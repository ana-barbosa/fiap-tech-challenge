"""Aggregation service entry point: read each patient's latest gait/audio/anomaly scores,
combine them via aggregate_scores.py, and write one aggregated_assessments row (+ an
alerts row if HIGH) per patient.

Only patients with at least one row in each of gait_scores, audio_scores, and
anomaly_scores are eligible.

Every run INSERTs a new aggregated_assessments row (and alerts row, if triggered)
rather than upserting, so re-running after upstream scores change accumulates history.

Usage:
    python run.py
"""

import argparse
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "dataset"))

import aggregate_scores  # noqa: E402
import report_generator  # noqa: E402
from init_db import DEFAULT_DB_PATH, get_connection, init_db  # noqa: E402


def get_eligible_patient_ids(conn):
    """Patient IDs with at least one usable row in each of the three modality tables."""
    rows = conn.execute(
        """
        SELECT p.patient_id FROM patients p
        WHERE EXISTS (SELECT 1 FROM gait_scores g WHERE g.patient_id = p.patient_id AND g.risk_score IS NOT NULL)
          AND EXISTS (SELECT 1 FROM audio_scores a WHERE a.patient_id = p.patient_id)
          AND EXISTS (SELECT 1 FROM anomaly_scores an WHERE an.patient_id = p.patient_id)
        ORDER BY p.patient_id
        """
    ).fetchall()
    return [row["patient_id"] for row in rows]


def get_representative_gait_row(conn, patient_id):
    """Pick the patient's gait_scores row whose risk_score is closest to their
    per-patient median, and return it alongside that median.
    """
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM gait_scores WHERE patient_id = ? AND risk_score IS NOT NULL",
        (patient_id,),
    ).fetchall()]
    scores = sorted(r["risk_score"] for r in rows)
    n = len(scores)
    median = scores[n // 2] if n % 2 else (scores[n // 2 - 1] + scores[n // 2]) / 2
    representative = min(rows, key=lambda r: abs(r["risk_score"] - median))
    return representative, median


def get_latest_audio_row(conn, patient_id):
    row = conn.execute(
        "SELECT * FROM audio_scores WHERE patient_id = ? ORDER BY processed_at DESC, id DESC LIMIT 1",
        (patient_id,),
    ).fetchone()
    return dict(row)


def get_latest_anomaly_row(conn, patient_id):
    row = conn.execute(
        "SELECT * FROM anomaly_scores WHERE patient_id = ? ORDER BY processed_at DESC, id DESC LIMIT 1",
        (patient_id,),
    ).fetchone()
    return dict(row)


def insert_aggregated_assessment(conn, patient_id, gait_row, audio_row, anomaly_row, aggregation_result, rationale):
    cursor = conn.execute(
        "INSERT INTO aggregated_assessments "
        "(patient_id, gait_score_id, audio_score_id, anomaly_score_id, combined_risk_level, rationale) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            patient_id, gait_row["id"], audio_row["id"], anomaly_row["id"],
            aggregation_result["combined_risk_level"], rationale,
        ),
    )
    return cursor.lastrowid


def insert_alert(conn, patient_id, aggregated_assessment_id, alert_level, message):
    conn.execute(
        "INSERT INTO alerts (patient_id, aggregated_assessment_id, alert_level, message) VALUES (?, ?, ?, ?)",
        (patient_id, aggregated_assessment_id, alert_level, message),
    )


def run_for_patient(conn, patient_id):
    gait_row, gait_median_score = get_representative_gait_row(conn, patient_id)
    audio_row = get_latest_audio_row(conn, patient_id)
    anomaly_row = get_latest_anomaly_row(conn, patient_id)

    aggregation_result = aggregate_scores.aggregate(
        gait_score=gait_median_score,
        audio_score=audio_row["distress_score"],
        anomaly_score=anomaly_row["bone_density_risk_score"],
    )
    rationale = report_generator.build_report(patient_id, gait_row, audio_row, anomaly_row, aggregation_result)
    aggregated_id = insert_aggregated_assessment(
        conn, patient_id, gait_row, audio_row, anomaly_row, aggregation_result, rationale
    )

    if aggregation_result["combined_risk_level"] == "HIGH":
        message = report_generator.build_alert_message(patient_id, aggregation_result)
        insert_alert(conn, patient_id, aggregated_id, "HIGH", message)

    return aggregation_result


def run(db_path=DEFAULT_DB_PATH):
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        patient_ids = get_eligible_patient_ids(conn)
        if not patient_ids:
            print("No patients have all three modality scores yet - "
                  "run `make run-video`, `make run-audio`, `make run-tabular` first")
            return
        for patient_id in patient_ids:
            print(f"[{patient_id}] aggregating")
            result = run_for_patient(conn, patient_id)
            alert_note = " - ALERT" if result["combined_risk_level"] == "HIGH" else ""
            print(f"[{patient_id}] {result['combined_risk_level']} "
                  f"({result['combined_risk_score']:.1f}/100){alert_note}")
        conn.commit()
    finally:
        conn.close()
    print(f"wrote {len(patient_ids)} aggregated_assessments rows -> {db_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    run(db_path=args.db_path)


if __name__ == "__main__":
    main()
