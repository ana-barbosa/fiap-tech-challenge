"""Download the synthetic consultation audio dataset from HuggingFace.

Fetches each participant's *_consultation.wav and *_transcript.json (ground-truth
speaker/text/severity log, dev-only) from the public HF dataset repo:
https://huggingface.co/datasets/ana-barbosa/fiap-module-04-fake-consultation

Every call passes token=False to force anonymous access - otherwise huggingface_hub
picks up an HF_TOKEN from the environment if one is set (e.g. services/audio/.env's
pyannote token), and an invalid/expired one gets a 401 instead of falling back to
anonymous, even though this repo needs no auth.

Usage:
    python dataset/download_audio_dataset.py
    python dataset/download_audio_dataset.py --dry-run
"""

import argparse
from pathlib import Path

from huggingface_hub import hf_hub_download, list_repo_files

REPO_ID = "ana-barbosa/fiap-module-04-fake-consultation"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "dataset" / "synthetic" / "audio"


def iter_dataset_filenames(repo_id):
    for filename in list_repo_files(repo_id, repo_type="dataset", token=False):
        if filename.endswith(".wav") or filename.endswith("_transcript.json"):
            yield filename


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="List what would happen without downloading")
    args = parser.parse_args()

    filenames = sorted(iter_dataset_filenames(REPO_ID))
    if not filenames:
        raise SystemExit(
            f"No .wav/_transcript.json files found in {REPO_ID} - check "
            f"https://huggingface.co/datasets/{REPO_ID} manually."
        )

    for filename in filenames:
        dest = OUTPUT_DIR / filename
        if args.dry_run:
            print(f"would download: {filename} -> {dest}")
            continue
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        downloaded_path = hf_hub_download(
            REPO_ID, filename, repo_type="dataset", local_dir=OUTPUT_DIR,
            force_download=True, token=False,
        )
        print(f"downloaded: {downloaded_path}")


if __name__ == "__main__":
    main()
