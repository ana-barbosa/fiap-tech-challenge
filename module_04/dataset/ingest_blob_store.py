"""Move sourced/generated dataset/ input into db/blob_store/ before any service reads it.

db/blob_store/{patient_id}/ is the "hospital's" own storage - services read only from
there, never from dataset/raw or dataset/synthetic directly. Runs before
dataset/seed_patients.py, the last step of `make generate-dataset`.

Everything below **moves**, not copies - dataset/raw/ and dataset/synthetic/ are
staging areas that empty out as they're ingested.

- Video: dataset/raw/toronto/*.mp4 -> db/blob_store/{patient_id}/{original_filename}.
- Audio: dataset/synthetic/audio/{id}_consultation.wav ->
  db/blob_store/{id}/consultation.wav. The TTS ground-truth log
  ({id}_transcript.json) does NOT go to blob_store - it's dev-only tooling, moved to
  notebooks/ground_truth/ instead so no production service can reach it.
- Tabular: dataset/synthetic/tabular/{id}_bone_density_history.csv ->
  db/blob_store/{id}/bone_density_history.csv.

dataset/raw/patients.xlsx is out of scope here - services/video/run.py reads it
directly for demographics.

Usage:
    python dataset/ingest_blob_store.py
"""

import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_VIDEO_DIR = REPO_ROOT / "dataset" / "raw"
SYNTHETIC_AUDIO_DIR = REPO_ROOT / "dataset" / "synthetic" / "audio"
SYNTHETIC_TABULAR_DIR = REPO_ROOT / "dataset" / "synthetic" / "tabular"
DEFAULT_BLOB_STORE_DIR = REPO_ROOT / "db" / "blob_store"
DEFAULT_GROUND_TRUTH_DIR = REPO_ROOT / "notebooks" / "ground_truth"

# Duplicated from services/video/src/video_id.py rather than imported - dataset/ and
# services/ deliberately don't import each other's code.
VIDEO_NAME_RE = re.compile(r"^(OAW\d+)-(top|bottom)$", re.IGNORECASE)


def _parse_video_patient_id(video_path):
    """OAW01-top.mp4 -> 'OAW01'. Self-recorded clips have no camera suffix - the
    filename stem itself is the patient_id."""
    stem = Path(video_path).stem
    match = VIDEO_NAME_RE.match(stem)
    return match.group(1).upper() if match else stem


def _move(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    print(f"{src} -> {dest}")
    return dest


def ingest_video(raw_dir=RAW_VIDEO_DIR, blob_store_dir=DEFAULT_BLOB_STORE_DIR):
    video_paths = sorted(raw_dir.glob("toronto/*.mp4")) + sorted(raw_dir.glob("self_recorded/*.mp4"))
    moved = []
    for video_path in video_paths:
        patient_id = _parse_video_patient_id(video_path)
        dest = blob_store_dir / patient_id / video_path.name
        moved.append(_move(video_path, dest))
    return moved


def ingest_audio(source_dir=SYNTHETIC_AUDIO_DIR, blob_store_dir=DEFAULT_BLOB_STORE_DIR,
                  ground_truth_dir=DEFAULT_GROUND_TRUTH_DIR):
    moved = []
    for wav_path in sorted(source_dir.glob("*_consultation.wav")):
        participant_id = wav_path.stem.replace("_consultation", "")
        moved.append(_move(wav_path, blob_store_dir / participant_id / "consultation.wav"))

        transcript_path = source_dir / f"{participant_id}_transcript.json"
        if transcript_path.exists():
            moved.append(_move(transcript_path, ground_truth_dir / transcript_path.name))
    return moved


def ingest_tabular(source_dir=SYNTHETIC_TABULAR_DIR, blob_store_dir=DEFAULT_BLOB_STORE_DIR):
    moved = []
    for csv_path in sorted(source_dir.glob("*_bone_density_history.csv")):
        participant_id = csv_path.stem.replace("_bone_density_history", "")
        moved.append(_move(csv_path, blob_store_dir / participant_id / "bone_density_history.csv"))
    return moved


def main():
    moved = ingest_video() + ingest_audio() + ingest_tabular()
    if not moved:
        print("Nothing found to ingest under dataset/raw/ or dataset/synthetic/ - run "
              "the earlier make generate-dataset steps first")
        return
    print(f"ingested {len(moved)} files -> {DEFAULT_BLOB_STORE_DIR} "
          f"(ground truth transcripts -> {DEFAULT_GROUND_TRUTH_DIR})")


if __name__ == "__main__":
    main()
