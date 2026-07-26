"""Video service entry point: pose extraction -> gait metrics -> risk scoring -> DB.

Scans db/blob_store/*/ for raw video files, runs the pipeline on any not yet processed,
and writes one row per (video, segment) to the gait_scores table. Each video's
per-video CSVs (frames/landmarks/segments) are also written to
db/blob_store/{patient_id}/. Pose extraction (YOLOv8 + MediaPipe, the heavy part)
always (re)runs for every video, overwriting any cached CSVs. gait_scores.landmarks_path
stores a repo-relative pointer back into blob_store to each video's landmarks CSV, so
app/Patient_Profile.py's video section can read it back.

Skeleton-overlay video annotation (video_annotation.py) also always runs - it redraws
the freshly-extracted landmarks CSV onto the original video, writing
db/blob_store/{patient_id}/{video_id}_annotated.mp4 for app/Patient_Profile.py to play
back next to the numeric gait_scores table.

Processes videos sequentially, one at a time. extract_landmarks/annotate_video print
progress every ~150 frames so a long-running video doesn't look stuck.

Usage:
    python run.py
    python run.py --db-path path/to/hospital.sqlite
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SERVICE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "dataset"))

import gait_metrics  # noqa: E402
import gait_risk_score  # noqa: E402
import pose_extraction  # noqa: E402
import video_annotation  # noqa: E402
from video_id import parse_video_id  # noqa: E402
from init_db import DEFAULT_DB_PATH, get_connection, init_db  # noqa: E402

BLOB_STORE_DIR = REPO_ROOT / "db" / "blob_store"

GAIT_SCORE_COLUMNS = [
    "video_id", "segment_id", "direction", "camera", "ground_truth", "landmarks_path",
    "start_frame", "end_frame", "duration_s", "n_frames", "hip_width_px_median",
    "num_steps_detected", "cadence_steps_per_min", "step_time_s_mean", "step_time_s_std",
    "step_width_norm_mean", "step_width_norm_cv", "margin_of_stability_norm_mean",
    "risk_score", "flag_low_cadence", "flag_prolonged_step_time", "flag_abnormal_gait",
]


def _sanitize(value):
    """Coerce pandas/numpy scalars to native Python types sqlite3 can bind directly,
    and NaN to None so it round-trips as SQL NULL rather than a stored float NaN."""
    if isinstance(value, (np.floating, float)) and math.isnan(value):
        return None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def upsert_gait_score(conn, patient_id, row):
    values = [_sanitize(row.get(c)) for c in GAIT_SCORE_COLUMNS]
    placeholders = ", ".join("?" for _ in GAIT_SCORE_COLUMNS)
    update_clause = ", ".join(
        f"{c} = excluded.{c}" for c in GAIT_SCORE_COLUMNS if c not in ("video_id", "segment_id")
    )
    conn.execute(
        f"INSERT INTO gait_scores (patient_id, {', '.join(GAIT_SCORE_COLUMNS)}) "
        f"VALUES (?, {placeholders}) "
        f"ON CONFLICT(video_id, segment_id) DO UPDATE SET {update_clause}",
        [patient_id, *values],
    )


def run_pose_extraction(video_paths):
    detector, pose = pose_extraction.load_models()
    for video_path in video_paths:
        patient_id, _ = parse_video_id(video_path)
        patient_dir = BLOB_STORE_DIR / patient_id
        print(f"[{video_path.stem}] starting pose extraction")
        summary = pose_extraction.process_video(video_path, detector, pose, patient_dir)
        print(f"[{video_path.stem}] done: {summary}")


def run_video_annotation(video_paths):
    for video_path in video_paths:
        video_id = video_path.stem
        patient_id, _ = parse_video_id(video_path)
        patient_dir = BLOB_STORE_DIR / patient_id
        landmarks_csv = patient_dir / f"{video_id}_landmarks.csv"
        annotated_path = patient_dir / f"{video_id}_annotated.mp4"

        print(f"[{video_id}] starting annotation")
        video_annotation.annotate_video(video_path, landmarks_csv, annotated_path)
        print(f"[{video_id}] wrote annotated video -> {annotated_path}")


def run_metrics_and_scoring():
    video_ids = sorted({p.stem.replace("_segments", "") for p in BLOB_STORE_DIR.glob("*/*_segments.csv")})
    all_rows = []
    for video_id in video_ids:
        all_rows.extend(gait_metrics.compute_metrics_for_video(video_id, BLOB_STORE_DIR))
    metrics_df = pd.DataFrame(all_rows)
    scored_df, reference = gait_risk_score.score_metrics(metrics_df)
    scored_df["landmarks_path"] = scored_df.apply(
        lambda row: str(
            (BLOB_STORE_DIR / row["participant_id"] / f"{row['video_id']}_landmarks.csv").relative_to(REPO_ROOT)
        ),
        axis=1,
    )
    print(f"reference stats (fit from this cohort): {reference}")
    return scored_df


def write_to_db(scored_df, db_path):
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        for _, row in scored_df.iterrows():
            row_dict = row.to_dict()
            patient_id = row_dict["participant_id"]
            upsert_gait_score(conn, patient_id, row_dict)
        conn.commit()
    finally:
        conn.close()
    print(f"wrote {len(scored_df)} gait_scores rows for {scored_df['participant_id'].nunique()} "
          f"patients -> {db_path}")


def run(db_path=DEFAULT_DB_PATH):
    video_paths = sorted(
        p for p in BLOB_STORE_DIR.glob("*/*.mp4") if not p.stem.endswith("_annotated")
    )
    if not video_paths:
        print(f"No videos found under {BLOB_STORE_DIR} - run dataset/ingest_blob_store.py "
              "(after dataset/download_video_dataset.py) first")
        return

    run_pose_extraction(video_paths)
    run_video_annotation(video_paths)

    scored_df = run_metrics_and_scoring()
    write_to_db(scored_df, db_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    run(db_path=args.db_path)


if __name__ == "__main__":
    main()
