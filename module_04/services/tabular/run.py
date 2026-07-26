"""Tabular (bone density/prescriptions) service entry point: anomaly detection + OP
prediction -> DB.

Scans db/blob_store/*/bone_density_history.csv, then for each patient:

  - scores it for anomalies (anomaly_risk_score.py) - the longitudinal question, "is
    something changing over time."
  - runs module_01's OP classifier on the latest visit (bone_density_model.py) - the
    cross-sectional question, "does this snapshot look osteoporotic."

Both write into the same anomaly_scores table row per patient.

Usage:
    python run.py
    python run.py --db-path path/to/hospital.sqlite
"""

import argparse
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "dataset"))

import anomaly_risk_score  # noqa: E402
import bone_density_model  # noqa: E402
from init_db import DEFAULT_DB_PATH, get_connection, init_db  # noqa: E402

BLOB_STORE_DIR = REPO_ROOT / "db" / "blob_store"

ANOMALY_SCORE_COLUMNS = [
    "bone_density_risk_score", "t_score_trend", "prescription_flag",
    "op_prediction", "op_prediction_confidence",
]


def upsert_anomaly_score(conn, patient_id, row):
    values = [row[c] for c in ANOMALY_SCORE_COLUMNS]
    placeholders = ", ".join("?" for _ in ANOMALY_SCORE_COLUMNS)
    update_clause = ", ".join(f"{c} = excluded.{c}" for c in ANOMALY_SCORE_COLUMNS)
    conn.execute(
        f"INSERT INTO anomaly_scores (patient_id, {', '.join(ANOMALY_SCORE_COLUMNS)}) "
        f"VALUES (?, {placeholders}) "
        f"ON CONFLICT(patient_id) DO UPDATE SET {update_clause}",
        [patient_id, *values],
    )


def run_scoring(participant_ids):
    model, pipeline = bone_density_model.load_model()
    rows = []
    for participant_id in participant_ids:
        print(f"[{participant_id}] scoring")
        anomaly_result = anomaly_risk_score.score_participant(participant_id, BLOB_STORE_DIR)
        op_result = bone_density_model.predict_participant_op_risk(participant_id, BLOB_STORE_DIR, model, pipeline)
        rows.append({**anomaly_result, **op_result})
    return rows


def write_to_db(rows, db_path):
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        for row in rows:
            upsert_anomaly_score(conn, row["participant_id"], row)
        conn.commit()
    finally:
        conn.close()
    print(f"wrote {len(rows)} anomaly_scores rows -> {db_path}")


def run(db_path=DEFAULT_DB_PATH):
    participant_ids = sorted(p.parent.name for p in BLOB_STORE_DIR.glob("*/bone_density_history.csv"))
    if not participant_ids:
        print(f"No bone_density_history.csv files found under {BLOB_STORE_DIR} - run "
              "'make generate-dataset' first")
        return

    rows = run_scoring(participant_ids)
    write_to_db(rows, db_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    run(db_path=args.db_path)


if __name__ == "__main__":
    main()
