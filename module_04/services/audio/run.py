"""Audio service entry point: consultation audio -> transcript -> risk score -> DB.

Scans db/blob_store/*/consultation.wav, runs WhisperX transcription + diarization on
any not yet processed (writing each participant's diarized transcript to
db/blob_store/{patient_id}/diarized_transcript.json), then scores patient-only text for
fatigue/pain/anxiety mentions (audio_risk_score.py) and writes one row per participant
to the audio_scores table.

Also rewrites each participant's diarized_transcript.json with per-line fatigue/pain/
anxiety flags added to every segment (audio_risk_score.py::annotate_transcript_with_flags)
so the UI can highlight individual transcript rows.

Usage:
    python run.py
    python run.py --db-path path/to/hospital.sqlite
"""

import argparse
import json
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SERVICE_ROOT.parents[1]
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "dataset"))

import audio_risk_score  # noqa: E402
import transcription  # noqa: E402
from init_db import DEFAULT_DB_PATH, get_connection, init_db  # noqa: E402

BLOB_STORE_DIR = REPO_ROOT / "db" / "blob_store"

AUDIO_SCORE_COLUMNS = ["audio_file", "distress_score", "fatigue_mentions", "pain_mentions", "flags"]


def upsert_audio_score(conn, patient_id, row):
    values = [row[c] for c in AUDIO_SCORE_COLUMNS]
    placeholders = ", ".join("?" for _ in AUDIO_SCORE_COLUMNS)
    update_clause = ", ".join(
        f"{c} = excluded.{c}" for c in AUDIO_SCORE_COLUMNS if c != "audio_file"
    )
    conn.execute(
        f"INSERT INTO audio_scores (patient_id, {', '.join(AUDIO_SCORE_COLUMNS)}) "
        f"VALUES (?, {placeholders}) "
        f"ON CONFLICT(audio_file) DO UPDATE SET {update_clause}",
        [patient_id, *values],
    )


def run_transcription(audio_paths):
    models = transcription.load_models()
    for audio_path in audio_paths:
        participant_id = audio_path.parent.name
        print(f"[{participant_id}] starting transcription")
        summary = transcription.process_participant(participant_id, BLOB_STORE_DIR, models)
        print(f"[{participant_id}] done: {summary}")


def run_scoring():
    participant_ids = sorted(
        p.name for p in BLOB_STORE_DIR.iterdir()
        if p.is_dir() and (p / "diarized_transcript.json").exists()
    )
    rows = []
    for participant_id in participant_ids:
        print(f"[{participant_id}] scoring")
        result = audio_risk_score.score_participant(participant_id, BLOB_STORE_DIR)
        audio_risk_score.annotate_transcript_with_flags(participant_id, BLOB_STORE_DIR)
        audio_path = BLOB_STORE_DIR / participant_id / "consultation.wav"
        result["audio_file"] = str(audio_path.relative_to(REPO_ROOT))
        result["flags"] = json.dumps(result["flags"])
        rows.append(result)
    return rows


def write_to_db(rows, db_path):
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        for row in rows:
            upsert_audio_score(conn, row["participant_id"], row)
        conn.commit()
    finally:
        conn.close()
    print(f"wrote {len(rows)} audio_scores rows -> {db_path}")


def run(db_path=DEFAULT_DB_PATH):
    audio_paths = sorted(BLOB_STORE_DIR.glob("*/consultation.wav"))
    if not audio_paths:
        print(f"No consultation.wav files found under {BLOB_STORE_DIR} - run "
              "'make generate-dataset' first (or dataset/generate_tts.py to regenerate "
              "from scratch, then dataset/ingest_blob_store.py)")
        return

    run_transcription(audio_paths)

    rows = run_scoring()
    write_to_db(rows, db_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    run(db_path=args.db_path)


if __name__ == "__main__":
    main()
