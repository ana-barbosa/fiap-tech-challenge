"""Pose extraction for gait videos: YOLOv8 person detection -> MediaPipe Pose.

MediaPipe Pose alone misses most frames of the Toronto archive's "top" (ceiling-mounted,
205cm) camera: the walker occupies only a small fraction of the 1080x1920 frame, and the
pose model is tuned for subjects filling more of the frame. Running YOLOv8 first to
localize and crop the walker fixes this.

Outputs three per-video CSVs under db/blob_store/{patient_id}/:
  <video_id>_frames.csv     one row per frame with a detected person (bbox + whether
                             pose landmarks were also found) - used for direction
                             segmentation.
  <video_id>_landmarks.csv  long-format pose landmarks (one row per frame x landmark)
                             for frames where MediaPipe Pose succeeded.
  <video_id>_segments.csv   front/back walking-bout boundaries derived from the bbox
                             size trend in _frames.csv.
"""

import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from ultralytics import YOLO

MP_POSE = mp.solutions.pose
LANDMARK_NAMES = [lm.name.lower() for lm in MP_POSE.PoseLandmark]

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLOB_STORE_DIR = REPO_ROOT / "db" / "blob_store"
YOLO_WEIGHTS_PATH = SERVICE_ROOT / "models" / "yolov8n.pt"

CROP_PADDING = 0.25  # fraction of bbox size added on each side before pose inference
YOLO_PERSON_CLASS = 0
YOLO_MIN_CONFIDENCE = 0.3
MIN_SEGMENT_DURATION_S = 3.0  # shorter bouts are turn-around noise, not a walking pass
SEGMENT_SMOOTHING_S = 0.5
MAX_DETECTION_GAP_S = 1.0  # dropouts longer than this force a fresh segmentation run


def load_models():
    """Load YOLOv8 (person detector) and MediaPipe Pose once, for reuse across videos."""
    detector = YOLO(str(YOLO_WEIGHTS_PATH))
    pose = MP_POSE.Pose(static_image_mode=False, model_complexity=1, min_detection_confidence=0.3)
    return detector, pose


def _pad_box(x1, y1, x2, y2, frame_w, frame_h, padding=CROP_PADDING):
    bw, bh = x2 - x1, y2 - y1
    x1 = max(0, int(x1 - padding * bw))
    y1 = max(0, int(y1 - padding * bh))
    x2 = min(frame_w, int(x2 + padding * bw))
    y2 = min(frame_h, int(y2 + padding * bh))
    return x1, y1, x2, y2


def extract_landmarks(video_path, detector, pose, min_confidence=YOLO_MIN_CONFIDENCE):
    """Run person detection + pose estimation over every frame of one video.

    Returns (frames_df, landmarks_df, fps, total_frames). frames_df has one row per
    frame with a detected person (bbox + pose_detected flag); landmarks_df has one row
    per (frame, landmark) for frames where pose succeeded, in original-frame pixel
    coords; total_frames is every frame read from the video, detected or not.
    """
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    frame_rows = []
    landmark_rows = []
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h, w = frame.shape[:2]

        detections = detector(frame, classes=[YOLO_PERSON_CLASS], verbose=False)[0].boxes
        if len(detections) > 0:
            best = int(detections.conf.argmax())
            conf = float(detections.conf[best])
            if conf >= min_confidence:
                x1, y1, x2, y2 = detections.xyxy[best].tolist()
                cx1, cy1, cx2, cy2 = _pad_box(x1, y1, x2, y2, w, h)

                crop = frame[cy1:cy2, cx1:cx2]
                crop_h, crop_w = crop.shape[:2]
                rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)
                pose_detected = result.pose_landmarks is not None

                frame_rows.append({
                    "frame_idx": frame_idx,
                    "timestamp_s": frame_idx / fps,
                    "bbox_x1": cx1, "bbox_y1": cy1, "bbox_x2": cx2, "bbox_y2": cy2,
                    "bbox_height_px": cy2 - cy1,
                    "yolo_conf": conf,
                    "pose_detected": pose_detected,
                })

                if pose_detected:
                    timestamp = frame_idx / fps
                    for name, lm in zip(LANDMARK_NAMES, result.pose_landmarks.landmark):
                        landmark_rows.append({
                            "frame_idx": frame_idx,
                            "timestamp_s": timestamp,
                            "landmark": name,
                            "x_px": cx1 + lm.x * crop_w,
                            "y_px": cy1 + lm.y * crop_h,
                            "z": lm.z,
                            "visibility": lm.visibility,
                        })

        frame_idx += 1

    cap.release()
    return pd.DataFrame(frame_rows), pd.DataFrame(landmark_rows), fps, frame_idx


def _split_into_contiguous_runs(df, fps, max_gap_s=MAX_DETECTION_GAP_S):
    """Split frames (sorted by frame_idx) wherever a detection dropout exceeds max_gap_s.

    frames_df only contains rows where YOLO found a person - if detection drops out for
    many consecutive real frames (e.g. person briefly out of frame), those rows are
    simply absent, not NaN. Without this split, the row-position-based windowing below
    would treat two frames on either side of a 100-frame dropout as "1 frame apart,"
    silently corrupting the bbox-height trend right at the gap.
    """
    if len(df) < 2:
        return [df]
    max_gap_frames = max(1, int(max_gap_s * fps))
    gaps = df["frame_idx"].diff().to_numpy()
    split_positions = np.where(gaps > max_gap_frames)[0]
    boundaries = [0, *split_positions.tolist(), len(df)]
    return [df.iloc[start:end] for start, end in zip(boundaries[:-1], boundaries[1:])]


def _segment_run(df, fps, min_duration_s, smoothing_s, id_offset):
    """Find front/back turning points within one contiguous (gap-free) run of frames.

    Returns (segments, next_id_offset). next_id_offset accounts for turning points
    filtered out by the duration check too, not just accepted segments, to avoid
    a later run's ids colliding with ones already consumed by this run.
    """
    df = df.reset_index(drop=True)
    window = max(1, int(smoothing_s * fps))
    smoothed = df["bbox_height_px"].rolling(window, center=True, min_periods=1).mean().to_numpy()

    min_distance = max(1, int(min_duration_s * fps))
    peaks, _ = find_peaks(smoothed, distance=min_distance)
    troughs, _ = find_peaks(-smoothed, distance=min_distance)
    turning_points = sorted(set([0, *peaks.tolist(), *troughs.tolist(), len(df) - 1]))

    segments = []
    seg_id = id_offset
    for start_i, end_i in zip(turning_points[:-1], turning_points[1:]):
        start_row, end_row = df.iloc[start_i], df.iloc[end_i]
        duration = end_row["timestamp_s"] - start_row["timestamp_s"]
        if duration < min_duration_s:
            seg_id += 1
            continue
        direction = "front" if end_row["bbox_height_px"] >= start_row["bbox_height_px"] else "back"
        segments.append({
            "segment_id": seg_id,
            "direction": direction,
            "start_frame": int(start_row["frame_idx"]),
            "end_frame": int(end_row["frame_idx"]),
            "start_time_s": start_row["timestamp_s"],
            "end_time_s": end_row["timestamp_s"],
            "duration_s": duration,
        })
        seg_id += 1
    return segments, seg_id


def segment_walking_bouts(frames_df, fps, min_duration_s=MIN_SEGMENT_DURATION_S,
                           smoothing_s=SEGMENT_SMOOTHING_S):
    """Split a video's detected frames into front/back walking bouts.

    Each raw Toronto video is a continuous back-and-forth walk. The bbox height trend
    (person getting closer to / farther from the camera) alternates: rising while
    walking toward the camera ("front"), falling while walking away ("back"). Turning
    points are the local extrema of that trend; segments are the spans between them.

    Detection dropouts are handled by splitting into contiguous runs first (see
    _split_into_contiguous_runs) - the windowing/peak-finding below assumes row position
    tracks elapsed time, which only holds within a gap-free run.
    """
    if frames_df.empty:
        return pd.DataFrame(columns=["segment_id", "direction", "start_frame", "end_frame",
                                      "start_time_s", "end_time_s", "duration_s"])

    df = frames_df.sort_values("frame_idx").reset_index(drop=True)
    runs = _split_into_contiguous_runs(df, fps)

    segments = []
    next_id = 0
    for run in runs:
        run_segments, next_id = _segment_run(run, fps, min_duration_s, smoothing_s, id_offset=next_id)
        segments.extend(run_segments)

    return pd.DataFrame(segments)


def process_video(video_path, detector, pose, output_dir=DEFAULT_BLOB_STORE_DIR):
    video_id = Path(video_path).stem
    start_time = time.perf_counter()
    frames_df, landmarks_df, fps, total_frames = extract_landmarks(video_path, detector, pose)
    segments_df = segment_walking_bouts(frames_df, fps)
    elapsed_s = time.perf_counter() - start_time

    output_dir.mkdir(parents=True, exist_ok=True)
    frames_df.to_csv(output_dir / f"{video_id}_frames.csv", index=False)
    landmarks_df.to_csv(output_dir / f"{video_id}_landmarks.csv", index=False)
    segments_df.to_csv(output_dir / f"{video_id}_segments.csv", index=False)

    frames_with_pose = int(frames_df["pose_detected"].sum()) if not frames_df.empty else 0
    return {
        "video_id": video_id,
        "fps": fps,
        "total_frames": total_frames,
        "video_duration_s": round(total_frames / fps, 1) if fps else None,
        "frames_with_detection": len(frames_df),
        "detection_rate": round(len(frames_df) / total_frames, 3) if total_frames else None,
        "frames_with_pose": frames_with_pose,
        "pose_success_rate": round(frames_with_pose / len(frames_df), 3) if len(frames_df) else None,
        "mean_yolo_confidence": round(float(frames_df["yolo_conf"].mean()), 3) if not frames_df.empty else None,
        "num_segments": len(segments_df),
        "segment_directions": segments_df["direction"].value_counts().to_dict() if not segments_df.empty else {},
        "walking_coverage_s": round(float(segments_df["duration_s"].sum()), 1) if not segments_df.empty else 0.0,
        "elapsed_s": round(elapsed_s, 1),
        "processing_fps": round(total_frames / elapsed_s, 1) if elapsed_s > 0 else None,
    }
