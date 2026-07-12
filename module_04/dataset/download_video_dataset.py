"""Download the Toronto Older Adults Gait Archive from figshare.

Fetches only what this project needs from the public figshare collection cited
in docs/osteoporosis_scenario_plan.md (DOI 10.6084/m9.figshare.c.5515953.v1):
  - Videos.zip (~2.3 GB) -> extracts OAWxx-top.mp4 / OAWxx-bottom.mp4 into
    dataset/raw/toronto/, then discards the zip.
  - Table 1.xlsx -> saved as dataset/raw/patients.xlsx.

Skips PoseTracking.zip, Xsens.zip, and the MATLAB analysis-code articles -
this project runs its own pose inference on raw video and doesn't need the
archive's precomputed pose/mocap data or original analysis scripts.

Usage:
    python dataset/download_video_dataset.py
    python dataset/download_video_dataset.py --dry-run
"""

import argparse
import re
import sys
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

FIGSHARE_API = "https://api.figshare.com/v2"
COLLECTION_DOI = "10.6084/m9.figshare.c.5515953.v1"
COLLECTION_ID = 5515953  # encoded in the DOI's "c.<id>" segment

VIDEO_MEMBER_RE = re.compile(r"^Videos/(OAW\d+-(top|bottom)\.mp4)$", re.IGNORECASE)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "dataset" / "raw"


def get_collection_articles(collection_id):
    articles, page = [], 1
    while True:
        resp = requests.get(
            f"{FIGSHARE_API}/collections/{collection_id}/articles",
            params={"page": page, "page_size": 100},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        articles.extend(batch)
        page += 1
    return articles


def get_article_files(article_id):
    resp = requests.get(f"{FIGSHARE_API}/articles/{article_id}")
    resp.raise_for_status()
    return resp.json().get("files", [])


def iter_dataset_files(collection_id):
    for article in get_collection_articles(collection_id):
        for file_info in get_article_files(article["id"]):
            yield file_info


def download_with_progress(url, dest, dry_run=False):
    if dry_run:
        print(f"would download: {url} -> {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc=dest.name) as bar:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                bar.update(len(chunk))


def extract_videos(zip_path, output_dir, dry_run=False):
    toronto_dir = output_dir / "toronto"
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if VIDEO_MEMBER_RE.match(m)]
        for member in members:
            filename = VIDEO_MEMBER_RE.match(member).group(1)
            dest = toronto_dir / filename
            if dry_run:
                print(f"would extract: {member} -> {dest}")
                continue
            toronto_dir.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dest, "wb") as out:
                out.write(src.read())
            print(f"extracted: {dest}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="List what would happen without downloading")
    args = parser.parse_args()

    found_any = False
    for file_info in iter_dataset_files(COLLECTION_ID):
        name = file_info["name"]

        if name.lower() == "videos.zip":
            found_any = True
            zip_dest = OUTPUT_DIR / "_downloads" / "Videos.zip"
            download_with_progress(file_info["download_url"], zip_dest, dry_run=args.dry_run)
            if not args.dry_run:
                extract_videos(zip_dest, OUTPUT_DIR, dry_run=args.dry_run)
                zip_dest.unlink(missing_ok=True)
            else:
                extract_videos(zip_dest, OUTPUT_DIR, dry_run=True) if zip_dest.exists() else None

        elif name.lower() in ("table 1.xlsx", "table_1.xlsx"):
            found_any = True
            download_with_progress(file_info["download_url"], OUTPUT_DIR / "patients.xlsx", dry_run=args.dry_run)

    if not found_any:
        print(
            "No matching files found via the figshare API - the collection layout may "
            f"have changed. Check https://doi.org/{COLLECTION_DOI} manually.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
