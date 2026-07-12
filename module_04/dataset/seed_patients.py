"""Pre-fill the patients table - the single authoritative writer of patients.source and
demographics, decoupled from every modality service.

Reads dataset/raw/patients.xlsx for the real participants' demographics +
source='toronto'. Also scans db/blob_store/*/*.mp4 for any other patient_id with a raw
video but no matching xlsx row - those get source='self-recorded', no demographics.

Runs as the last step of `make generate-dataset`, after ingest_blob_store.py, so every
patient_id that a service might score already exists in patients (source is NOT NULL,
FK-referenced by gait_scores/audio_scores/anomaly_scores) before any service runs -
this is what lets them run in parallel instead of racing to satisfy the FK constraint.

Calls init_db() itself so it stays self-sufficient regardless of Makefile ordering.

Usage:
    python dataset/seed_patients.py
"""

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from init_db import DEFAULT_DB_PATH, get_connection, init_db

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATIENTS_XLSX = REPO_ROOT / "dataset" / "raw" / "patients.xlsx"
DEFAULT_BLOB_STORE_DIR = REPO_ROOT / "db" / "blob_store"

LBS_TO_KG = 0.453592
PATIENT_DEMOGRAPHIC_COLUMNS = ["age", "sex", "height_cm", "weight_kg", "bmi", "falls_last_6mo"]


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


def load_demographics(patients_xlsx=DEFAULT_PATIENTS_XLSX):
    """Real per-patient demographics (age/sex/height/weight/bmi/falls_last_6mo) from
    the Toronto archive's clinical spreadsheet. POMA/BBS/TUG test scores are
    deliberately excluded - see db/schema.sql's patients table comment.

    Filters out the summary rows (mean/SD/Min/Max) the spreadsheet appends after the 14
    real participants. Returns {} if the file isn't present yet."""
    if not patients_xlsx.exists():
        return {}

    df = pd.read_excel(patients_xlsx)
    df = df[pd.to_numeric(df["Participant No."], errors="coerce").notna()].copy()
    df["participant_no"] = df["Participant No."].astype(int)

    demographics = {}
    for _, row in df.iterrows():
        participant_id = f"OAW{row['participant_no']:02d}"
        height_cm = row["Height (cm)"]
        weight_kg = row["Weight (lbs)"] * LBS_TO_KG
        demographics[participant_id] = {
            "age": row["Age (years)"],
            "sex": row["Sex"],
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "bmi": weight_kg / ((height_cm / 100.0) ** 2),
            "falls_last_6mo": row["Number of falls in the last 6 months "],
        }
    return demographics


def find_self_recorded_patient_ids(known_patient_ids, blob_store_dir=DEFAULT_BLOB_STORE_DIR):
    """Any blob_store patient_id with a raw video (a *.mp4 that isn't an
    _annotated.mp4, i.e. one ingest_blob_store.py moved there) but no matching
    patients.xlsx row."""
    video_patient_ids = {
        p.parent.name for p in blob_store_dir.glob("*/*.mp4") if not p.stem.endswith("_annotated")
    }
    return sorted(video_patient_ids - set(known_patient_ids))


def upsert_patient(conn, patient_id, source, demographics=None):
    demographics = demographics or {}
    values = [_sanitize(demographics.get(c)) for c in PATIENT_DEMOGRAPHIC_COLUMNS]
    columns = ["source", *PATIENT_DEMOGRAPHIC_COLUMNS]
    placeholders = ", ".join("?" for _ in columns)
    update_clause = ", ".join(f"{c} = excluded.{c}" for c in columns)
    conn.execute(
        f"INSERT INTO patients (patient_id, {', '.join(columns)}) VALUES (?, {placeholders}) "
        f"ON CONFLICT(patient_id) DO UPDATE SET {update_clause}",
        [patient_id, source, *values],
    )


def run(db_path=DEFAULT_DB_PATH):
    init_db(db_path)
    demographics_by_patient = load_demographics()
    self_recorded_ids = find_self_recorded_patient_ids(demographics_by_patient)

    conn = get_connection(db_path)
    try:
        for patient_id, demographics in demographics_by_patient.items():
            upsert_patient(conn, patient_id, "toronto", demographics)
        for patient_id in self_recorded_ids:
            upsert_patient(conn, patient_id, "self-recorded")
        conn.commit()
    finally:
        conn.close()
    print(f"seeded {len(demographics_by_patient)} toronto + {len(self_recorded_ids)} "
          f"self-recorded patients -> {db_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    run(db_path=args.db_path)


if __name__ == "__main__":
    main()
