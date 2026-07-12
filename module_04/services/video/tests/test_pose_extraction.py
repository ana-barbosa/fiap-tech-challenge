import numpy as np
import pandas as pd

from pose_extraction import segment_walking_bouts
from video_id import parse_video_id


def test_parse_video_id_toronto_naming():
    assert parse_video_id("dataset/raw/toronto/OAW01-top.mp4") == ("OAW01", "top")
    assert parse_video_id("OAW14-bottom.mp4") == ("OAW14", "bottom")


def test_parse_video_id_self_recorded_has_no_camera():
    participant_id, camera = parse_video_id("cane_incorrect_use.mp4")
    assert camera is None
    assert participant_id == "cane_incorrect_use"


def make_triangle_wave_frames(fps=30, total_duration_s=20, period_s=10):
    t = np.arange(0, total_duration_s, 1 / fps)
    height = 200 + 100 * (1 - np.abs(((t % period_s) / (period_s / 2)) - 1))
    return pd.DataFrame({
        "frame_idx": np.arange(len(t)),
        "timestamp_s": t,
        "bbox_height_px": height,
        "pose_detected": True,
    })


def test_segment_walking_bouts_alternates_front_and_back():
    fps = 30
    frames_df = make_triangle_wave_frames(fps=fps)
    segments = segment_walking_bouts(frames_df, fps=fps)

    assert len(segments) >= 2
    directions = segments["direction"].tolist()
    assert all(a != b for a, b in zip(directions, directions[1:]))


def test_segment_walking_bouts_empty_input():
    empty = pd.DataFrame(columns=["frame_idx", "timestamp_s", "bbox_height_px", "pose_detected"])
    segments = segment_walking_bouts(empty, fps=30)
    assert len(segments) == 0


def test_segment_walking_bouts_assigns_globally_unique_segment_ids_across_runs():
    """Regression test: a filtered (too-short) turning point within one run must not
    cause a later run's segment_id to collide with an id this run already used.

    Real production data hit this: OAW01-bottom's segment_id=4 was assigned to two
    different frame ranges. Root cause was using len(segments) (count of *accepted*
    segments) as the next run's id_offset - if a run has any turning point filtered out
    by the duration check, len(segments) undercounts the ids actually consumed, and the
    next run starts from a lower id than it should, colliding with one already used.

    Constructed to reproduce that shape exactly: run 1 = accepted segment (0->15) +
    filtered short dip (15->18, 0.3s < the 1.0s min_duration_s used here) + accepted
    segment (18->40); large gap; run 2 = two more accepted segments.
    """
    fps = 10.0
    min_duration_s = 1.0
    smoothing_s = 0.1  # ~no-op at this fps (window size 1), keeps peak positions exact

    run1_a = np.linspace(100, 200, 16)        # positions 0-15 (rise, accepted 0->15)
    run1_b = np.linspace(200, 190, 4)[1:]     # positions 16-18 (short dip, filtered)
    run1_c = np.linspace(190, 300, 23)[1:]    # positions 19-40 (rise, accepted 18->40)
    run1_height = np.concatenate([run1_a, run1_b, run1_c])
    run1_frames = np.arange(0, 41)

    run2_a = np.linspace(150, 250, 16)        # positions 0-15 (rise, accepted)
    run2_b = np.linspace(250, 150, 16)[1:]    # positions 16-30 (fall, accepted)
    run2_height = np.concatenate([run2_a, run2_b])
    run2_frames = np.arange(200, 231)         # gap of 160 frames >> MAX_DETECTION_GAP_S*fps

    frame_idx = np.concatenate([run1_frames, run2_frames])
    bbox_height = np.concatenate([run1_height, run2_height])

    frames_df = pd.DataFrame({
        "frame_idx": frame_idx,
        "timestamp_s": frame_idx / fps,
        "bbox_height_px": bbox_height,
        "pose_detected": True,
    })

    segments = segment_walking_bouts(frames_df, fps=fps, min_duration_s=min_duration_s,
                                      smoothing_s=smoothing_s)

    assert segments["segment_id"].is_unique, segments[["segment_id", "start_frame", "end_frame"]]
    assert len(segments) >= 3  # >=2 accepted in run 1 (dip correctly filtered) + >=1 in run 2


def test_segment_walking_bouts_does_not_bridge_large_detection_gap():
    """Regression test for the OAW05-bottom/top bug: a ~95-frame detection dropout was
    silently treated as "1 frame apart" (row-position, not frame_idx, based windowing),
    producing a degenerate 2-frame segment spanning the entire gap."""
    fps = 29.0
    frame_idx = np.concatenate([np.arange(0, 21), [117], np.arange(118, 250)])
    bbox_height = 200 + np.linspace(0, 100, len(frame_idx))  # steady rise across the gap
    frames_df = pd.DataFrame({
        "frame_idx": frame_idx,
        "timestamp_s": frame_idx / fps,
        "bbox_height_px": bbox_height,
        "pose_detected": True,
    })

    segments = segment_walking_bouts(frames_df, fps=fps)

    bridges_gap = ((segments["start_frame"] == 21) & (segments["end_frame"] == 117)).any()
    assert not bridges_gap
