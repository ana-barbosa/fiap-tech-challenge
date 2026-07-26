# Osteoporosis Multimodal Monitoring — Tech Challenge Fase 4

Multimodal fall/fracture-risk monitoring for osteoporosis patients, fusing gait video
analysis, consultation audio analysis, and bone-density/prescription anomaly detection
into a single fall/fracture-risk alert for the medical team.

See `docs/architecture.md` for the full platform narrative, multimodal flow diagram,
models applied per data type, results/validation, scope decisions, and next steps.

## Demo

Short screen recording of the dashboard, covering three patients: a clean LOW-risk
patient for contrast (`OAW02`), a HIGH-risk alert with all three modalities agreeing
(`OAW04`), and a second HIGH-risk case with a different score composition (`OAW12`).

[`docs/demo.mov`](docs/demo.mov)

## Architecture: service per modality + SQLite

Each modality is a separate service with its own isolated venv and dependencies. Services never
import each other's code; the only shared contract is a SQLite database - each service
writes its own structured output rows, the aggregation service reads all three and writes
the combined result, the UI only ever reads the database.

```
[video service  ] ─┐
[audio service  ] ─┼──▶ [SQLite db/hospital.sqlite] ──▶ [aggregation service] ──▶ [Streamlit app]
[anomaly service] ─┘
```

See `docs/architecture.md` for the full diagram and rationale.

## Quick Start

Fastest path from an empty checkout to the dashboard:

```bash
make setup-dataset       # creates dataset/.venv + db/hospital.sqlite
make generate-dataset    # fetches/generates video+audio+tabular input -> db/blob_store/

make setup-services      # one venv per modality service (video/audio/tabular/aggregation)
make setup-app           # Streamlit app's venv, also copies .env.example -> .env
```

Before continuing:

- Visit [`pyannote/speaker-diarization-community-1`](https://huggingface.co/pyannote/speaker-diarization-community-1)
  while logged in to huggingface.co and click "Agree and access repository" — the
  diarization model is gated, so this step is required before a token can download it.
- Create a token at huggingface.co/settings/tokens and fill it in as `HF_TOKEN` in `.env`.


⚠️ This next step might take a considerable amount of time due to the video processing step.
```bash
make run-services        # runs video, audio, tabular, then aggregation
make run-app              # opens the dashboard at http://localhost:8501
```

## Repository layout

```
docs/       architecture doc (narrative, flow diagram, models, results, next steps)
            + consultation scripts used to generate the synthetic audio dataset
dataset/    own venv - fetch/generate/organize scripts (incl. init_db.py, seed_patients.py)
            + gitignored raw/sourced input and generated synthetic data
services/   one dir per modality - own requirements.txt, src/, tests/, run.py
db/         schema.sql + blob_store/ (gitignored per-patient generated artifacts) +
            hospital.sqlite (gitignored) - the shared contract between services
app/        Streamlit dashboard (reads db/hospital.sqlite only)
notebooks/  diarization_validation.ipynb - one-off dev-time check of the audio
            service's diarization output against ground truth, plus
            ground_truth/ (gitignored, populated by dataset generation - see
            dataset/README.md's Audio section)
```

## Data

Not committed to the repo. See `dataset/README.md` for download links and expected file
placement.

## Extra commands

Beyond the Quick Start sequence, each modality service has its own `setup-<name>` /
`run-<name>` target, useful for iterating on one service at a time instead of the whole
pipeline:

```bash
make setup-video && make run-video
make setup-audio && make run-audio
make setup-tabular && make run-tabular
make setup-aggregation && make run-aggregation   # needs the other three to have run at least once
```

`run-video`, `run-audio`, `run-tabular`, `run-aggregation`, and `run-services` all accept
`ARGS`, e.g. to point at a scratch database instead of the real one:

```bash
make run-video ARGS="--db-path path/to/scratch.sqlite"
```

See `dataset/README.md` for running individual dataset-generation steps (e.g.
regenerating audio from scratch instead of pulling from HuggingFace).

## QA

Every service except the Streamlit app (which has no logic beyond reading the database)
has a real automated test suite exercising its scoring/processing logic, not just
top-level scripts assumed to work:

```bash
make qa
```

This runs each folder's test suite (`dataset`, `services/video`, `services/audio`,
`services/tabular`, `services/aggregation`) through its own venv's pytest, continuing
through all of them even if one fails, and exits non-zero if any suite failed.

To run one service's tests in isolation:

```bash
./services/video/.venv/bin/python -m pytest services/video/tests
```
