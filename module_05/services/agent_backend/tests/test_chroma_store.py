import tempfile
from pathlib import Path

import pytest

from src import chroma_store, config


def test_get_listings_collection_reads_seeded_data():
    collection = chroma_store.get_listings_collection()
    assert collection.count() == 3
    result = collection.get(ids=["1"])
    assert result["metadatas"][0]["city"] == "Taubaté"


def test_get_geo_collection_reads_seeded_data():
    collection = chroma_store.get_geo_collection()
    assert collection.count() == 2


def test_get_roi_collection_reads_seeded_data():
    collection = chroma_store.get_roi_collection()
    assert collection.count() == 1


def test_get_financing_collection_reads_seeded_data():
    collection = chroma_store.get_financing_collection()
    assert collection.count() == 2


def test_semantic_query_returns_seeded_listing():
    collection = chroma_store.get_listings_collection()
    result = collection.query(query_texts=["apartamento tranquilo em Taubaté"], n_results=1)
    assert result["ids"][0] == ["1"]


def test_is_ready_true_when_listings_populated():
    assert chroma_store.is_ready() is True


def test_missing_collection_raises_instead_of_silently_creating(monkeypatch):
    empty_dir = Path(tempfile.mkdtemp()) / "chroma"
    monkeypatch.setattr(config, "CHROMA_PATH", str(empty_dir))
    chroma_store.reset_client_cache()
    try:
        with pytest.raises(Exception, match="does not exist"):
            chroma_store.get_listings_collection()
        assert chroma_store.is_ready() is False
    finally:
        chroma_store.reset_client_cache()
