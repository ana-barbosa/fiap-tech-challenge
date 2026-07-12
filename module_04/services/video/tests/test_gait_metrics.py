import numpy as np
import pandas as pd
import pytest

from gait_metrics import (
    STEP_DETECTION_LANDMARK,
    compute_gait_metrics,
    compute_hip_width_px,
    pivot_landmarks_wide,
)

FOOT = STEP_DETECTION_LANDMARK


def make_landmark_rows(fps, duration_s, step_freq_hz, hip_width, stride_amplitude, y=800.0):
    n = int(duration_s * fps)
    t = np.arange(n) / fps
    left_hip_x = np.full(n, 500.0)
    right_hip_x = left_hip_x - hip_width
    left_foot_x = left_hip_x + stride_amplitude * np.sin(2 * np.pi * step_freq_hz * t)
    right_foot_x = right_hip_x - stride_amplitude * np.sin(2 * np.pi * step_freq_hz * t)

    rows = []
    for name, arr in [
        ("left_hip", left_hip_x), ("right_hip", right_hip_x),
        (f"left_{FOOT}", left_foot_x), (f"right_{FOOT}", right_foot_x),
    ]:
        for i in range(n):
            rows.append({"frame_idx": i, "landmark": name, "x_px": arr[i], "y_px": y})
    return pd.DataFrame(rows)


def test_pivot_landmarks_wide_shapes_one_row_per_frame():
    landmarks_df = make_landmark_rows(fps=30, duration_s=1, step_freq_hz=2, hip_width=40, stride_amplitude=30)
    wide = pivot_landmarks_wide(landmarks_df)
    assert len(wide) == 30
    assert {"left_hip_x", "right_hip_x", f"left_{FOOT}_x", f"right_{FOOT}_x"}.issubset(wide.columns)


def test_compute_hip_width_px_constant_width():
    landmarks_df = make_landmark_rows(fps=30, duration_s=1, step_freq_hz=2, hip_width=40, stride_amplitude=30)
    wide = pivot_landmarks_wide(landmarks_df)
    hip_width = compute_hip_width_px(wide)
    assert np.allclose(hip_width, 40.0)


def test_compute_gait_metrics_recovers_known_cadence():
    fps = 30
    step_freq_hz = 1.2  # each half-cycle of the sinusoid is one step -> cadence = 60 * 2 * step_freq_hz
                        # (144 spm - kept inside PLAUSIBLE_CADENCE_RANGE_SPM so the bound doesn't null it)
    landmarks_df = make_landmark_rows(fps=fps, duration_s=10, step_freq_hz=step_freq_hz,
                                       hip_width=40, stride_amplitude=30)
    segment = {"segment_id": 0, "direction": "front", "start_frame": 0, "end_frame": 299, "duration_s": 10}

    metrics = compute_gait_metrics(landmarks_df, segment, fps)

    expected_cadence = 60 * 2 * step_freq_hz
    assert metrics["cadence_steps_per_min"] == pytest.approx(expected_cadence, rel=0.05)
    assert metrics["hip_width_px_median"] == pytest.approx(40.0)
    assert metrics["num_steps_detected"] > 0


def test_compute_gait_metrics_rejects_implausible_cadence():
    fps = 30
    step_freq_hz = 4.0  # -> 480 spm, well outside PLAUSIBLE_CADENCE_RANGE_SPM
    landmarks_df = make_landmark_rows(fps=fps, duration_s=10, step_freq_hz=step_freq_hz,
                                       hip_width=40, stride_amplitude=30)
    segment = {"segment_id": 0, "direction": "front", "start_frame": 0, "end_frame": 299, "duration_s": 10}

    metrics = compute_gait_metrics(landmarks_df, segment, fps)

    assert metrics["num_steps_detected"] > 0  # steps were detected...
    assert metrics["cadence_steps_per_min"] is None  # ...but rejected as implausible
    assert metrics["step_time_s_mean"] is None


def test_compute_gait_metrics_returns_none_when_landmarks_missing():
    landmarks_df = pd.DataFrame([
        {"frame_idx": 0, "landmark": "left_hip", "x_px": 500.0, "y_px": 800.0},
        {"frame_idx": 0, "landmark": "right_hip", "x_px": 460.0, "y_px": 800.0},
    ])
    segment = {"segment_id": 0, "direction": "front", "start_frame": 0, "end_frame": 0, "duration_s": 0.0}

    assert compute_gait_metrics(landmarks_df, segment, fps=30) is None
