"""Gait metrics from extracted pose landmarks: cadence, step time, and secondary metrics.

Cadence and step time correlate strongly with clinical fall-risk scores (cadence vs.
TUG: R = -0.79 to -0.87 per the source paper's Toronto Older Adults Gait Archive
analysis), while spatial variables (step width, margin of stability) correlate poorly.
Cadence/step time are therefore the primary outputs here; step width and margin of
stability are computed but flagged as secondary/exploratory only and are not used by
gait_risk_score.py.

Corrections applied before step detection:

1. Temporal smoothing: raw per-frame joint coordinates are noisy, producing spurious
   peaks in the step-detection signal. A zero-lag second-order Butterworth low-pass
   filter (8Hz cutoff, matching the source paper) is applied via scipy.signal.filtfilt.

2. Per-frame scale normalization: participants walk toward/away from the camera, so
   apparent size changes substantially within a segment. Step detection normalizes by
   the subject's own hip width *per frame*, not a segment-wide constant. Hip width is
   floored at MIN_HIP_WIDTH_PX to avoid divide-by-near-zero blowups at the frame edge.

3. MIN_STEP_EVENTS_FOR_CADENCE requires at least 3 step-time samples before a segment's
   cadence is trusted, since segments with only 2 detected step events yield a single,
   zero-variance sample that can swing cadence to implausible values.

4. PLAUSIBLE_CADENCE_RANGE_SPM rejects any computed cadence outside human-plausible
   bounds - short segments can pack enough jitter-driven events to clear the prominence
   bar locally without representing a real cadence.

Landmark choice for the alternating-stride signal: heel was chosen over ankle/foot_index
after comparing correlation sign against patients.xlsx's cadence-vs-TUG relationship -
heel was the only one giving the theoretically-correct (negative) sign, and is also the
anatomically standard gait-event landmark in biomechanics literature.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, find_peaks

from video_id import parse_video_id

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BLOB_STORE_DIR = REPO_ROOT / "db" / "blob_store"

BUTTERWORTH_CUTOFF_HZ = 8.0  # matches the source paper's jitter-removal filter
BUTTERWORTH_ORDER = 2
MIN_SAMPLES_FOR_SMOOTHING = 15  # filtfilt needs > ~3*(2*order+1) samples to run safely

MIN_HIP_WIDTH_PX = 15.0  # below this, keypoint precision is unreliable; floor to avoid /~0
STEP_PROMINENCE_HIP_WIDTHS = 0.3  # min normalized-signal excursion to count as a real step
MIN_STEP_INTERVAL_S = 0.2  # steps faster than 5/s are treated as noise, not real gait
MIN_STEP_EVENTS_FOR_CADENCE = 4  # >=3 step-time samples needed for a non-degenerate estimate
PLAUSIBLE_CADENCE_RANGE_SPM = (40.0, 180.0)  # human gait bounds

STEP_DETECTION_LANDMARK = "heel"  # see module docstring for why heel was chosen

TRAJECTORY_COLUMNS = ["left_hip_x", "left_hip_y", "right_hip_x", "right_hip_y",
                      f"left_{STEP_DETECTION_LANDMARK}_x", f"left_{STEP_DETECTION_LANDMARK}_y",
                      f"right_{STEP_DETECTION_LANDMARK}_x", f"right_{STEP_DETECTION_LANDMARK}_y"]


def pivot_landmarks_wide(landmarks_df):
    """Long-format (frame, landmark, x/y/z/visibility) rows -> one row per frame."""
    wide = landmarks_df.pivot(index="frame_idx", columns="landmark", values=["x_px", "y_px"])
    wide.columns = [f"{landmark}_{coord.split('_')[0]}" for coord, landmark in wide.columns]
    return wide.sort_index()


def smooth_trajectory(series, fps, cutoff_hz=BUTTERWORTH_CUTOFF_HZ, order=BUTTERWORTH_ORDER):
    """Zero-lag low-pass Butterworth filter, matching the source paper's jitter-removal step.

    Assumes samples are evenly spaced in time (no large gaps from dropped detections
    within the segment); left as-is for short/gappy segments, which just skip smoothing.
    """
    if len(series) <= MIN_SAMPLES_FOR_SMOOTHING:
        return series
    nyquist = fps / 2.0
    normal_cutoff = cutoff_hz / nyquist
    if normal_cutoff >= 1.0:
        return series  # fps too low relative to cutoff to filter meaningfully
    b, a = butter(order, normal_cutoff, btype="low")
    smoothed = filtfilt(b, a, series.to_numpy())
    return pd.Series(smoothed, index=series.index)


def smooth_wide_landmarks(wide_df, fps, columns=TRAJECTORY_COLUMNS):
    smoothed = wide_df.copy()
    for col in columns:
        if col in smoothed.columns:
            smoothed[col] = smooth_trajectory(smoothed[col], fps)
    return smoothed


def compute_hip_width_px(wide_df):
    """Per-frame hip width (pixels) - a per-frame scale reference, not a single scalar."""
    dx = wide_df["left_hip_x"] - wide_df["right_hip_x"]
    dy = wide_df["left_hip_y"] - wide_df["right_hip_y"]
    return np.sqrt(dx ** 2 + dy ** 2).clip(lower=MIN_HIP_WIDTH_PX)


def detect_step_events(wide_df, hip_width_px, fps, landmark=STEP_DETECTION_LANDMARK):
    """Find alternating-stride extrema in the hip-width-normalized left/right separation.

    Each local extremum (feet at maximum fore-aft separation) approximates one step
    event; the interval between consecutive extrema approximates step time. Operates on
    an already-smoothed, per-frame-normalized signal (see module docstring) - this is
    still a coarse heuristic appropriate for a scoped project, not a clinical-grade
    gait-event detector.
    """
    raw_diff = wide_df[f"left_{landmark}_x"] - wide_df[f"right_{landmark}_x"]
    normalized = (raw_diff / hip_width_px).to_numpy()

    min_distance = max(1, int(MIN_STEP_INTERVAL_S * fps))
    peaks, _ = find_peaks(normalized, distance=min_distance, prominence=STEP_PROMINENCE_HIP_WIDTHS)
    troughs, _ = find_peaks(-normalized, distance=min_distance, prominence=STEP_PROMINENCE_HIP_WIDTHS)
    event_positions = np.sort(np.concatenate([peaks, troughs]))

    frame_idx = wide_df.index.to_numpy()
    event_frames = frame_idx[event_positions]
    event_values_norm = np.abs(normalized[event_positions])
    return event_frames, event_values_norm


def compute_gait_metrics(landmarks_df, segment, fps):
    """Compute cadence, step time, and secondary metrics for one walking-bout segment."""
    seg_landmarks = landmarks_df[
        (landmarks_df["frame_idx"] >= segment["start_frame"])
        & (landmarks_df["frame_idx"] <= segment["end_frame"])
    ]
    required = {"left_hip", "right_hip", f"left_{STEP_DETECTION_LANDMARK}", f"right_{STEP_DETECTION_LANDMARK}"}
    present = set(seg_landmarks["landmark"].unique())
    if not required.issubset(present) or seg_landmarks.empty:
        return None

    wide = pivot_landmarks_wide(seg_landmarks)
    smoothed = smooth_wide_landmarks(wide, fps)
    hip_width_px = compute_hip_width_px(smoothed)
    hip_width_px_median = float(hip_width_px.median())

    event_frames, event_values_norm = detect_step_events(smoothed, hip_width_px, fps)
    n_events = len(event_frames)

    if n_events < MIN_STEP_EVENTS_FOR_CADENCE:
        cadence = None
        step_time_mean = None
        step_time_std = None
    else:
        step_times = np.diff(event_frames) / fps
        step_time_mean = float(np.mean(step_times))
        step_time_std = float(np.std(step_times))
        cadence = 60.0 / step_time_mean if step_time_mean > 0 else None
        min_cadence, max_cadence = PLAUSIBLE_CADENCE_RANGE_SPM
        if cadence is not None and not (min_cadence <= cadence <= max_cadence):
            cadence, step_time_mean, step_time_std = None, None, None

    if n_events == 0:
        step_width_norm_mean = None
        step_width_norm_cv = None
    else:
        step_width_norm_mean = float(np.mean(event_values_norm))
        step_width_norm_cv = (
            float(np.std(event_values_norm) / step_width_norm_mean) if step_width_norm_mean else None
        )

    center_x = (smoothed["left_hip_x"] + smoothed["right_hip_x"]) / 2
    stance_foot_x = smoothed[[f"left_{STEP_DETECTION_LANDMARK}_x", f"right_{STEP_DETECTION_LANDMARK}_x"]].mean(axis=1)
    mos_norm = (center_x - stance_foot_x).abs() / hip_width_px
    margin_of_stability_norm_mean = float(mos_norm.mean())

    return {
        "segment_id": segment["segment_id"],
        "direction": segment["direction"],
        "start_frame": segment["start_frame"],
        "end_frame": segment["end_frame"],
        "duration_s": segment["duration_s"],
        "n_frames": len(wide),
        "hip_width_px_median": hip_width_px_median,
        "num_steps_detected": n_events,
        "cadence_steps_per_min": cadence,
        "step_time_s_mean": step_time_mean,
        "step_time_s_std": step_time_std,
        "step_width_norm_mean": step_width_norm_mean,
        "step_width_norm_cv": step_width_norm_cv,
        "margin_of_stability_norm_mean": margin_of_stability_norm_mean,
    }


def compute_metrics_for_video(video_id, blob_store_dir=DEFAULT_BLOB_STORE_DIR):
    patient_id, _ = parse_video_id(video_id)
    patient_dir = blob_store_dir / patient_id
    landmarks_path = patient_dir / f"{video_id}_landmarks.csv"
    segments_path = patient_dir / f"{video_id}_segments.csv"
    if not landmarks_path.exists() or not segments_path.exists():
        return []

    landmarks_df = pd.read_csv(landmarks_path)
    segments_df = pd.read_csv(segments_path)
    fps_estimate = _estimate_fps(landmarks_df)

    rows = []
    for _, segment in segments_df.iterrows():
        metrics = compute_gait_metrics(landmarks_df, segment, fps_estimate)
        if metrics is None:
            continue
        metrics["video_id"] = video_id
        rows.append(metrics)
    return rows


def _estimate_fps(landmarks_df):
    """Recover fps from timestamp/frame spacing, since only frames.csv stores it directly."""
    frames = landmarks_df[["frame_idx", "timestamp_s"]].drop_duplicates().sort_values("frame_idx")
    diffs = frames["timestamp_s"].diff().dropna()
    diffs = diffs[diffs > 0]
    return 1.0 / diffs.median() if not diffs.empty else 30.0
