# Dataset

`dataset/` holds only sourced/generated *input* material, plus the scripts to fetch,
generate, and organize it. No service reads from `dataset/` directly — see
`docs/architecture.md`'s Bridging Narrative and Implementation section for why.
`ingest_blob_store.py` moves everything fetched/generated here into
`db/blob_store/{patient_id}/` before any service touches it. Nothing under
`dataset/raw/` or `dataset/synthetic/` is committed to the repo (see `.gitignore`).

## Quick start

```bash
make setup-dataset     # dataset's own venv + creates db/hospital.sqlite
make generate-dataset  # fetch/generate everything, move it into db/blob_store/, seed patients
```

`generate-dataset` runs, in order: `download_video_dataset.py` →
`download_audio_dataset.py` → `generate_clinical_records.py` → `ingest_blob_store.py`
(moves everything into `db/blob_store/`) → `seed_patients.py` (fills the `patients`
table). To run one step manually, invoke it directly:
`./dataset/.venv/bin/python dataset/<script>.py [args]`.

## Video: Toronto Older Adults Gait Archive

- Paper: https://www.nature.com/articles/s41597-022-01495-z
- Data (figshare): https://doi.org/10.6084/m9.figshare.c.5515953.v1

`download_video_dataset.py` pulls `Videos.zip` (~2.3 GB), extracts only
`OAWxx-top.mp4` / `OAWxx-bottom.mp4` into `dataset/raw/toronto/`, and saves the
archive's clinical scores (`Table 1.xlsx`) as `dataset/raw/patients.xlsx`. It skips
`PoseTracking.zip` (this pipeline runs its own pose inference), `Xsens.zip`, and the
archive's MATLAB scripts. Use `--dry-run` to preview.

Result:

```
dataset/raw/toronto/OAW01-top.mp4
dataset/raw/toronto/OAW01-bottom.mp4
...
dataset/raw/patients.xlsx
```

Only 11 of 14 participants have Xsens-validated data, but all 14 have usable video +
clinical scores — process all 14.

`ingest_blob_store.py` moves every `.mp4` under `dataset/raw/toronto/` into
`db/blob_store/{patient_id}/{filename}`. Then run the video service to process it all
into `db/hospital.sqlite`:

```bash
make run-video
```

`db/blob_store/{patient_id}/` also holds the per-video pose-extraction output
(frames/landmarks/segments CSVs, the skeleton-overlay `.mp4`) — `gait_scores` rows
store a `landmarks_path` pointer back into it.

## Audio: synthetic consultation recordings

Scripted, AI-generated (not real patient recordings) — see `docs/consultation_scripts.md`
for the 14 doctor/patient dialogues, tiered by each participant's gait risk score.
Generated via `edge-tts`; requires `ffmpeg` on PATH (`make setup-dataset` checks for it).

Hosted on HuggingFace, not committed to this repo:
https://huggingface.co/datasets/ana-barbosa/fiap-module-04-fake-consultation

`download_audio_dataset.py` pulls all 14 participants' `.wav` + `_transcript.json`
files into `dataset/synthetic/audio/`, always overwriting. Use `--dry-run` to preview.

Result:

```
dataset/synthetic/audio/OAW01_consultation.wav    # concatenated doctor+patient dialogue
dataset/synthetic/audio/OAW01_transcript.json     # ground-truth {speaker, text, severity} per line
...
```

To regenerate from scratch instead (not part of `make generate-dataset`):

```bash
./dataset/.venv/bin/python dataset/generate_tts.py
```

`ingest_blob_store.py` then splits the two files: `consultation.wav` goes to
`db/blob_store/{patient_id}/` (the audio service's real input); `{id}_transcript.json`
goes to `notebooks/ground_truth/` instead. That transcript is ground truth generated at
TTS time, not a real unknown recording — `services/audio/src/transcription.py` never
reads it. It exists only for the one-off diarization check in
`notebooks/diarization_validation.ipynb`. Keeping it out of `db/blob_store/` entirely
guarantees no service can ever read it.

## Tabular: synthetic longitudinal bone-density/prescription history

Synthetic (not real patient labs) — 4 visits per participant, 6 months apart, trending
consistent with each participant's risk tier so all three modalities tell the same risk
story. Baseline demographics (Gender/Age/Height/Weight/BMI) are real, pulled from
`dataset/raw/patients.xlsx`; only bone density, labs, and medication columns are
synthesized. See `generate_clinical_records.py`'s module docstring for the full
derivation (population stats sourced from `module_01/analysis/UA.csv`).

`generate_clinical_records.py` is deterministic (seeded per `participant_id`) —
re-running always regenerates identical output.

Result:

```
dataset/synthetic/tabular/OAW01_bone_density_history.csv    # 4 synthetic visits
...
```

`ingest_blob_store.py` moves each one into
`db/blob_store/{patient_id}/bone_density_history.csv`. `services/tabular/run.py` reads
it back from there.

## Patients: demographics pre-fill

`seed_patients.py` is the single writer of the `patients` table (demographics + fall
history) — no modality service writes to it. It runs last in `generate-dataset`, after
`ingest_blob_store.py`, reading `dataset/raw/patients.xlsx` directly. Every `patient_id`
exists before any modality service runs, which is what lets video/audio/tabular run in
parallel instead of racing each other to satisfy `patients`'s foreign-key constraints.

Idempotent (`ON CONFLICT DO UPDATE`) — safe to re-run. Calls `dataset/init_db.py`
itself first, so it doesn't depend on `make setup-dataset` having already run.
