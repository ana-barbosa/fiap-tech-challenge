#!/usr/bin/env python3
"""
Download and verify medical datasets for fine-tuning.

Datasets:
1. PubMedQA - https://github.com/pubmedqa/pubmedqa
2. MedQuAD - https://github.com/abachaa/MedQuAD
3. Synthea - https://synthea.mitre.org/downloads (manual or automated)

EPFL Guidelines are downloaded automatically by the notebook.
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError
import zipfile
import tempfile

# Get the data/raw directory
SCRIPT_DIR = Path(__file__).parent
RAW_DIR = SCRIPT_DIR / "data" / "raw"


def create_directories():
    """Create necessary directory structure."""
    if RAW_DIR.exists():
        print(f"🗑️  Removing existing: {RAW_DIR}")
        shutil.rmtree(RAW_DIR)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✅ Directory structure ready: {RAW_DIR}")


def run_command(cmd, cwd=None, desc=""):
    """Run a shell command and return success status."""
    try:
        if desc:
            print(f"📥 {desc}...")
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout: {desc} took too long")
        return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False


def download_pubmedqa():
    """Download PubMedQA dataset - ori_pqal.json only."""
    pubmedqa_dir = RAW_DIR / "pubmedqa" / "data"

    if (pubmedqa_dir / "ori_pqal.json").exists():
        print("✅ PubMedQA already downloaded")
        return True

    pubmedqa_dir.mkdir(parents=True, exist_ok=True)

    url = "https://raw.githubusercontent.com/pubmedqa/pubmedqa/master/data/ori_pqal.json"

    try:
        print("📥 Downloading PubMedQA...")
        with urlopen(url, timeout=300) as response:
            with open(pubmedqa_dir / "ori_pqal.json", "wb") as f:
                f.write(response.read())
        print("✅ PubMedQA downloaded successfully")
        return True
    except Exception as e:
        print(f"❌ PubMedQA download failed: {e}")
        return False


def download_medquad():
    """Download MedQuAD dataset."""
    medquad_dir = RAW_DIR / "medquad"

    if (medquad_dir / "1_CancerGov_QA").exists():
        print("✅ MedQuAD already downloaded")
        return True

    # Remove if partial download exists
    if medquad_dir.exists():
        shutil.rmtree(medquad_dir)

    success = run_command(
        ["git", "clone", "https://github.com/abachaa/MedQuAD.git", str(medquad_dir)],
        desc="Downloading MedQuAD"
    )

    if success and (medquad_dir / "1_CancerGov_QA").exists():
        print("✅ MedQuAD downloaded successfully")
        return True
    else:
        print("❌ MedQuAD download failed")
        return False


def download_synthea():
    """Download and extract Synthea dataset."""
    synthea_dir = RAW_DIR / "synthea"
    required_files = ["csv/patients.csv", "csv/encounters.csv", "csv/conditions.csv", "csv/medications.csv"]

    # Check if already exists
    if all((synthea_dir / f).exists() for f in required_files):
        print("✅ Synthea already downloaded")
        return True

    # Remove if partial download exists
    if synthea_dir.exists():
        shutil.rmtree(synthea_dir)

    synthea_url = "https://synthetichealth.github.io/synthea-sample-data/downloads/synthea_sample_data_csv_apr2020.zip"

    try:
        synthea_dir.mkdir(parents=True, exist_ok=True)
        temp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        temp_zip_path = temp_zip.name
        temp_zip.close()

        print(f"📥 Downloading Synthea ...")
        print(f"   From: {synthea_url}")
        with urlopen(synthea_url, timeout=300) as response:
            with open(temp_zip_path, 'wb') as out_file:
                total = 0
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    total += len(chunk)
                    print(f"\r   Downloaded: {total / (1024*1024):.1f}MB", end="", flush=True)
        print()

        # Extract
        print("   Extracting...")
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(synthea_dir)

        os.unlink(temp_zip_path)

        # Verify
        if all((synthea_dir / f).exists() for f in required_files):
            print("✅ Synthea downloaded and extracted successfully")
            return True
        else:
            print("⚠️  Synthea extracted but some files missing")
            print(f"   Files found: {list(synthea_dir.glob('**/*.csv'))}")
            return False

    except URLError as e:
        print(f"❌ Download failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def verify_downloads():
    """Verify all datasets are present."""
    print("\n📋 Verifying downloads...\n")

    checks = {
        "PubMedQA": (RAW_DIR / "pubmedqa" / "data" / "ori_pqal.json"),
        "MedQuAD": (RAW_DIR / "medquad" / "1_CancerGov_QA"),
        "Synthea": (RAW_DIR / "synthea" / "csv" / "patients.csv"),
    }

    all_ok = True
    for name, path in checks.items():
        if path.exists():
            print(f"✅ {name:20} {path}")
        else:
            print(f"❌ {name:20} MISSING")
            all_ok = False

    print(f"\n{'✅ All datasets ready!' if all_ok else '⚠️  Some datasets are missing.'}\n")
    return all_ok


def main():
    """Main download sequence."""
    print("=" * 60)
    print("Medical Dataset Downloader")
    print("=" * 60)
    print()

    create_directories()
    print()

    results = {
        "PubMedQA": download_pubmedqa(),
        "MedQuAD": download_medquad(),
        "Synthea": download_synthea(),
    }
    print()

    # Verify
    verify_downloads()

    # Summary
    failed = [name for name, success in results.items() if not success]
    if failed:
        print(f"⚠️  Failed to download: {', '.join(failed)}")
        print("\nTroubleshooting:")
        print("1. Check internet connection")
        print("2. Ensure you have at least 2.5GB free space")
        print("3. For Synthea, download manually from https://synthea.mitre.org/downloads")
        return 1
    else:
        print("🎉 All datasets downloaded successfully!")
        print("\nNext step: Run 01_data_preparation.ipynb")
        return 0


if __name__ == "__main__":
    sys.exit(main())
