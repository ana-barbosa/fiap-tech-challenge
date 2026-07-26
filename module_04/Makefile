.PHONY: setup-dataset generate-dataset setup-services run-services setup-video \
	run-video setup-audio run-audio setup-tabular run-tabular setup-aggregation \
	run-aggregation setup-app run-app qa

# needed for PIPESTATUS (run-services, qa) - /bin/sh doesn't have it
SHELL := /bin/bash

setup-dataset:
	command -v ffmpeg >/dev/null 2>&1 || ( \
		echo "ffmpeg not found on PATH - installing..." && \
		if [ "$$(uname)" = "Darwin" ]; then brew install ffmpeg; \
		elif command -v apt-get >/dev/null 2>&1; then sudo apt-get update && sudo apt-get install -y ffmpeg; \
		else echo "Could not auto-install ffmpeg on this OS - install it manually (needed by pydub)." && exit 1; \
		fi \
	)
	python3.11 -m venv dataset/.venv
	./dataset/.venv/bin/pip install --upgrade pip
	./dataset/.venv/bin/pip install -r dataset/requirements.txt
	./dataset/.venv/bin/python dataset/init_db.py

# Fetches/generates everything, moves it into db/blob_store/, then seeds the patients
# table. For individual steps, run the dataset/*.py scripts directly (see dataset/README.md).
generate-dataset:
	./dataset/.venv/bin/python dataset/download_video_dataset.py
	./dataset/.venv/bin/python dataset/download_audio_dataset.py
	./dataset/.venv/bin/python dataset/generate_clinical_records.py
	./dataset/.venv/bin/python dataset/ingest_blob_store.py
	./dataset/.venv/bin/python dataset/seed_patients.py

setup-services: setup-video setup-audio setup-tabular setup-aggregation

# Runs video/audio/tabular, then aggregation once all three finish. Extra flags go
# through ARGS, applied to all four, e.g.:
#   make run-services ARGS="--db-path path/to/hospital.sqlite"
run-services: run-video run-audio run-tabular run-aggregation

setup-video:
	python3.11 -m venv services/video/.venv
	./services/video/.venv/bin/pip install --upgrade pip
	./services/video/.venv/bin/pip install -r services/video/requirements.txt

# Reads db/blob_store/ (make generate-dataset first). Extra flags go through ARGS, e.g.:
#   make run-video ARGS="--db-path path/to/hospital.sqlite"
run-video:
	./services/video/.venv/bin/python services/video/run.py $(ARGS)

setup-audio:
	command -v ffmpeg >/dev/null 2>&1 || ( \
		echo "ffmpeg not found on PATH - installing..." && \
		if [ "$$(uname)" = "Darwin" ]; then brew install ffmpeg; \
		elif command -v apt-get >/dev/null 2>&1; then sudo apt-get update && sudo apt-get install -y ffmpeg; \
		else echo "Could not auto-install ffmpeg on this OS - install it manually (needed by whisperx)." && exit 1; \
		fi \
	)
	python3.11 -m venv services/audio/.venv
	./services/audio/.venv/bin/pip install --upgrade pip
	./services/audio/.venv/bin/pip install -r services/audio/requirements.txt
	test -f .env || cp .env.example .env

# Needs HF_TOKEN in .env (see transcription.py's docstring).
# Extra flags go through ARGS, e.g.: make run-audio ARGS="--db-path path/to/hospital.sqlite"
run-audio:
	./services/audio/.venv/bin/python services/audio/run.py $(ARGS)

setup-tabular:
	python3.11 -m venv services/tabular/.venv
	./services/tabular/.venv/bin/pip install --upgrade pip
	./services/tabular/.venv/bin/pip install -r services/tabular/requirements.txt

# Reads db/blob_store/ (make generate-dataset first). Extra flags go through ARGS, e.g.:
#   make run-tabular ARGS="--db-path path/to/hospital.sqlite"
run-tabular:
	./services/tabular/.venv/bin/python services/tabular/run.py $(ARGS)

# Depends on gait_scores/audio_scores/anomaly_scores already being populated
# (run-video/run-audio/run-tabular first).
setup-aggregation:
	python3.11 -m venv services/aggregation/.venv
	./services/aggregation/.venv/bin/pip install --upgrade pip
	./services/aggregation/.venv/bin/pip install -r services/aggregation/requirements.txt

run-aggregation:
	./services/aggregation/.venv/bin/python services/aggregation/run.py $(ARGS)

setup-app:
	python3.11 -m venv app/.venv
	./app/.venv/bin/pip install --upgrade pip
	./app/.venv/bin/pip install -r app/requirements.txt

run-app:
	./app/.venv/bin/streamlit run app/Patient_Profile.py

# Runs every folder's test suite through its own venv's pytest (app/ has none). All
# suites run even if one fails; qa exits non-zero at the end if any of them did.
qa:
	@status=0; \
	for dir in dataset services/video services/audio services/tabular services/aggregation; do \
		name=$$(basename $$dir); \
		./$$dir/.venv/bin/python -m pytest $$dir/tests | sed "s/^/[$$name] /"; \
		if [ $${PIPESTATUS[0]} -ne 0 ]; then status=1; fi; \
	done; \
	exit $$status
