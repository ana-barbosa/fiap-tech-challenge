import hashlib
from pathlib import Path

from pypdf import PdfReader

DOCS_DIR = Path(__file__).resolve().parent.parent / "seed_data" / "financing_docs"


def scan_docs() -> dict[str, dict]:
    docs: dict[str, dict] = {}
    for pdf_path in sorted(DOCS_DIR.glob("*.pdf")):
        raw = pdf_path.read_bytes()
        content_hash = hashlib.sha256(raw).hexdigest()
        reader = PdfReader(pdf_path)
        text = "\n".join(page.extract_text() for page in reader.pages).strip()
        docs[pdf_path.stem] = {
            "document": text,
            "metadata": {"content_hash": content_hash, "source_file": pdf_path.name},
        }
    return docs
