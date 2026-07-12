import pandas as pd

from gait_risk_score import fit_reference_stats, score_metrics, score_segment


def make_metrics_row(video_id, cadence, step_time):
    return {
        "video_id": video_id, "segment_id": 0, "direction": "front",
        "start_frame": 0, "end_frame": 100, "duration_s": 5.0, "n_frames": 100,
        "hip_width_px_median": 40.0, "num_steps_detected": 10,
        "cadence_steps_per_min": cadence, "step_time_s_mean": step_time,
        "step_time_s_std": 0.01, "step_width_norm_mean": 1.0, "step_width_norm_cv": 0.1,
        "margin_of_stability_norm_mean": 0.2,
    }


def test_fit_reference_stats_matches_known_mean():
    metrics_df = pd.DataFrame([
        make_metrics_row("OAW01-top", 100.0, 0.6),
        make_metrics_row("OAW02-top", 120.0, 0.5),
    ])
    reference = fit_reference_stats(metrics_df)
    assert reference["cadence_mean"] == 110.0
    assert reference["step_time_mean"] == 0.55


def test_score_segment_average_cadence_scores_near_fifty():
    reference = {"cadence_mean": 110.0, "cadence_sd": 10.0, "step_time_mean": 0.55, "step_time_sd": 0.05}
    risk_score, flags = score_segment(110.0, 0.55, reference)
    assert risk_score == 50.0
    assert flags["abnormal_gait"] is False


def test_score_segment_low_cadence_and_slow_step_time_flags_abnormal():
    reference = {"cadence_mean": 110.0, "cadence_sd": 10.0, "step_time_mean": 0.55, "step_time_sd": 0.05}
    risk_score, flags = score_segment(85.0, 0.70, reference)  # 2.5 SD below / above reference
    assert risk_score > 90
    assert flags["low_cadence"] is True
    assert flags["prolonged_step_time"] is True
    assert flags["abnormal_gait"] is True


def test_score_segment_missing_values_returns_none_flags():
    reference = {"cadence_mean": 110.0, "cadence_sd": 10.0, "step_time_mean": 0.55, "step_time_sd": 0.05}
    risk_score, flags = score_segment(None, 0.55, reference)
    assert risk_score is None
    assert all(v is None for v in flags.values())


def test_score_metrics_derives_participant_and_source():
    metrics_df = pd.DataFrame([
        make_metrics_row("OAW03-bottom", 100.0, 0.6),
        make_metrics_row("cane_incorrect_use", 90.0, 0.65),
    ])
    scored_df, _ = score_metrics(metrics_df)

    toronto_row = scored_df[scored_df["video_id"] == "OAW03-bottom"].iloc[0]
    assert toronto_row["source"] == "toronto"
    assert toronto_row["participant_no"] == 3

    self_recorded_row = scored_df[scored_df["video_id"] == "cane_incorrect_use"].iloc[0]
    assert self_recorded_row["source"] == "self-recorded"
    assert self_recorded_row["ground_truth"] == "none"
    assert pd.isna(self_recorded_row["participant_no"])
