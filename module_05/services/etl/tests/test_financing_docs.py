from pathlib import Path

from src import financing_docs

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_scan_docs_reads_text_and_hash_from_each_pdf(monkeypatch):
    monkeypatch.setattr(financing_docs, "DOCS_DIR", FIXTURES_DIR)

    docs = financing_docs.scan_docs()

    assert set(docs) == {"doc_a", "doc_b"}
    assert "Documento A" in docs["doc_a"]["document"]
    assert "acentuacao" in docs["doc_b"]["document"]
    for doc_id, doc in docs.items():
        assert doc["metadata"]["source_file"] == f"{doc_id}.pdf"
        assert len(doc["metadata"]["content_hash"]) == 64


def test_scan_docs_hash_is_stable_across_calls(monkeypatch):
    monkeypatch.setattr(financing_docs, "DOCS_DIR", FIXTURES_DIR)

    first = financing_docs.scan_docs()
    second = financing_docs.scan_docs()

    assert first["doc_a"]["metadata"]["content_hash"] == second["doc_a"]["metadata"]["content_hash"]


def test_scan_docs_empty_dir_returns_empty_dict(tmp_path, monkeypatch):
    monkeypatch.setattr(financing_docs, "DOCS_DIR", tmp_path)

    assert financing_docs.scan_docs() == {}
