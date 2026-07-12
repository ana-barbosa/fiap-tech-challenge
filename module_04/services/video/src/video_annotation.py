"""Overlay the extracted pose skeleton onto the original video, frame by frame.

Deliberately separate from pose_extraction.py, which eagerly imports mediapipe/
ultralytics at module level. This module only needs cv2 + pandas to redraw
already-computed landmarks - run.py's run_video_annotation() reads back the
{video_id}_landmarks.csv that pose_extraction.py just wrote, rather than re-running
pose inference.

Output: db/blob_store/{patient_id}/{video_id}_annotated.mp4 - played back directly by
app/Patient_Profile.py's video section, next to the numeric gait_scores table.

Known limitation: frames are encoded with OpenCV's 'mp4v' fourcc, since
opencv-python-headless builds don't reliably ship an H.264 encoder. Most browsers play
mp4v-in-.mp4 fine, but if st.video() shows a blank player for a given browser,
re-encoding the output through system ffmpeg (H.264) is the fix.
"""

from pathlib import Path

import cv2
import pandas as pd

# Skeleton edges as landmark *name* pairs (not mediapipe's enum-index POSE_CONNECTIONS,
# since this module has no mediapipe import). Hardcoded from mediapipe's own 33-point
# Pose topology - limbs + torso only, skipping the fine-grained face landmarks.
SKELETON_CONNECTIONS = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
    ("left_ankle", "left_heel"), ("left_heel", "left_foot_index"),
    ("right_ankle", "right_heel"), ("right_heel", "right_foot_index"),
]

POINT_COLOR_BGR = (0, 0, 255)
LINE_COLOR_BGR = (0, 255, 0)
POINT_RADIUS_PX = 4
LINE_THICKNESS_PX = 2


def annotate_video(video_path, landmarks_csv_path, output_path):
    """Draw the pose skeleton (from an already-extracted landmarks CSV) over every
    frame of the original video.

    Frames with no detected pose (not present in landmarks_csv for that frame_idx)
    pass through unannotated rather than being dropped, so the output video keeps the
    same length/duration/frame rate as the source - a reviewer scrubbing the video
    shouldn't see it jump or freeze at detection gaps.
    """
    landmarks_df = pd.read_csv(landmarks_csv_path)
    points_by_frame = {
        frame_idx: dict(zip(group["landmark"], zip(group["x_px"], group["y_px"])))
        for frame_idx, group in landmarks_df.groupby("frame_idx")
    }

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(
            f"cv2.VideoWriter couldn't open {output_path} with the 'mp4v' codec - "
            "this OpenCV build may be missing that codec's backend."
        )

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        points = points_by_frame.get(frame_idx)
        if points:
            for name_a, name_b in SKELETON_CONNECTIONS:
                point_a, point_b = points.get(name_a), points.get(name_b)
                if point_a and point_b:
                    cv2.line(frame, (int(point_a[0]), int(point_a[1])),
                              (int(point_b[0]), int(point_b[1])), LINE_COLOR_BGR, LINE_THICKNESS_PX)
            for x, y in points.values():
                cv2.circle(frame, (int(x), int(y)), POINT_RADIUS_PX, POINT_COLOR_BGR, -1)
        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()
    return output_path
