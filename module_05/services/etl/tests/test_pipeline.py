from unittest.mock import patch

from src import chroma_store, pipeline, roi


def _listing(
    id_,
    city,
    neighborhood,
    property_type,
    listing_type,
    price,
    status="available",
    updated_at="t1",
    description="Ótimo imóvel.",
):
    return {
        "id": id_,
        "listing_type": listing_type,
        "city": city,
        "neighborhood": neighborhood,
        "property_type": property_type,
        "price": price,
        "rooms": 2,
        "area_sqm": 60,
        "status": status,
        "updated_at": updated_at,
        "description": description,
    }


def setup_function():
    for name in ["listings", "geo", "roi_summary", "financing_kb"]:
        collection = chroma_store.get_client().get_or_create_collection(name)
        existing_ids = collection.get(include=[])["ids"]
        if existing_ids:
            collection.delete(ids=existing_ids)


def test_sync_listings_indexes_new_and_skips_unchanged_on_next_cycle():
    listings = [_listing(1, "Ubatuba", "Centro", "house", "sale", 500_000)]

    first = pipeline.sync_listings(listings)
    assert first["indexed"] == 1
    assert first["removed"] == 0

    second = pipeline.sync_listings(listings)
    assert second["indexed"] == 0
    assert second["removed"] == 0


def test_sync_listings_reindexes_on_updated_at_change():
    pipeline.sync_listings([_listing(2, "Ubatuba", "Centro", "house", "sale", 500_000, updated_at="t1")])

    changed = [_listing(2, "Ubatuba", "Centro", "house", "sale", 480_000, updated_at="t2")]
    stats = pipeline.sync_listings(changed)
    assert stats["indexed"] == 1
    assert roi.segment_key("Ubatuba", "Centro", "house") in stats["changed_segments"]


def test_sync_listings_removes_ids_missing_from_current_batch():
    pipeline.sync_listings([_listing(3, "Ubatuba", "Centro", "house", "sale", 500_000)])

    stats = pipeline.sync_listings([])
    assert stats["removed"] == 1
    assert roi.segment_key("Ubatuba", "Centro", "house") in stats["changed_segments"]

    collection = chroma_store.get_listings_collection()
    assert collection.get(ids=["3"], include=[])["ids"] == []


def test_sync_geo_scrapes_each_missing_city_only_once_per_cycle():
    listings = [
        _listing(10, "Cidade Nova", "Centro", "house", "sale", 500_000),
        _listing(11, "Cidade Nova", "Centro", "house", "rent", 2_000),
    ]
    fake_geo = {"document": "Cidade Nova é ótima.", "metadata": {"city": "Cidade Nova"}}

    with patch("src.pipeline.wikipedia_geo.scrape_city_geo", return_value=fake_geo) as mock_scrape:
        stats = pipeline.sync_geo(listings)
    assert stats["scraped"] == 1
    mock_scrape.assert_called_once_with("Cidade Nova")

    with patch("src.pipeline.wikipedia_geo.scrape_city_geo") as mock_scrape_again:
        stats_again = pipeline.sync_geo(listings)
    assert stats_again["scraped"] == 0
    mock_scrape_again.assert_not_called()


def test_sync_geo_leaves_city_uncached_on_scrape_failure():
    listings = [_listing(12, "Cidade Falha", "Centro", "house", "sale", 500_000)]
    with patch("src.pipeline.wikipedia_geo.scrape_city_geo", side_effect=Exception("boom")):
        stats = pipeline.sync_geo(listings)

    assert stats["scraped"] == 0
    collection = chroma_store.get_geo_collection()
    assert collection.get(ids=["Cidade Falha"], include=[])["ids"] == []


def test_sync_roi_creates_then_removes_segment_when_a_side_disappears():
    listings = [
        _listing(20, "Lorena", "Centro", "apartment", "sale", 300_000),
        _listing(21, "Lorena", "Centro", "apartment", "rent", 1_500),
    ]
    key = roi.segment_key("Lorena", "Centro", "apartment")

    stats = pipeline.sync_roi(listings, {key})
    assert stats["updated"] == 1
    collection = chroma_store.get_roi_collection()
    assert collection.get(ids=[key], include=[])["ids"] == [key]

    stats_after_rent_removed = pipeline.sync_roi([listings[0]], {key})
    assert stats_after_rent_removed["removed"] == 1
    assert collection.get(ids=[key], include=[])["ids"] == []


def test_sync_roi_noop_when_no_segments_changed():
    stats = pipeline.sync_roi([], set())
    assert stats == {"updated": 0, "removed": 0}


def test_run_once_orchestrates_full_cycle():
    listings = [
        _listing(30, "Cruzeiro", "Centro", "apartment", "sale", 300_000),
        _listing(31, "Cruzeiro", "Centro", "apartment", "rent", 1_500),
    ]
    fake_geo = {"document": "Cruzeiro é uma cidade.", "metadata": {"city": "Cruzeiro"}}
    fake_financing = {"itbi": {"document": "ITBI...", "metadata": {"content_hash": "abc", "source_file": "itbi.pdf"}}}

    with (
        patch("src.pipeline.crm_client.fetch_available_listings", return_value=listings),
        patch("src.pipeline.wikipedia_geo.scrape_city_geo", return_value=fake_geo),
        patch("src.pipeline.financing_docs.scan_docs", return_value=fake_financing),
    ):
        stats = pipeline.run_once()

    assert stats["listings_available"] == 2
    assert stats["listings_indexed"] == 2
    assert stats["listings_removed"] == 0
    assert stats["geo_cities_scraped"] == 1
    assert stats["roi_segments_updated"] == 1
    assert stats["roi_segments_removed"] == 0
    assert stats["financing_docs_indexed"] == 1
    assert stats["financing_docs_removed"] == 0
    assert stats["last_run_at"] is not None


def test_sync_financing_docs_indexes_new_and_skips_unchanged_on_next_cycle():
    fake_docs = {"itbi": {"document": "ITBI texto...", "metadata": {"content_hash": "hash1", "source_file": "itbi.pdf"}}}

    with patch("src.pipeline.financing_docs.scan_docs", return_value=fake_docs):
        first = pipeline.sync_financing_docs()
        assert first == {"indexed": 1, "removed": 0}

        second = pipeline.sync_financing_docs()
        assert second == {"indexed": 0, "removed": 0}


def test_sync_financing_docs_reindexes_on_hash_change():
    with patch(
        "src.pipeline.financing_docs.scan_docs",
        return_value={"itbi": {"document": "v1", "metadata": {"content_hash": "hash1", "source_file": "itbi.pdf"}}},
    ):
        pipeline.sync_financing_docs()

    with patch(
        "src.pipeline.financing_docs.scan_docs",
        return_value={"itbi": {"document": "v2", "metadata": {"content_hash": "hash2", "source_file": "itbi.pdf"}}},
    ):
        stats = pipeline.sync_financing_docs()

    assert stats == {"indexed": 1, "removed": 0}


def test_sync_financing_docs_removes_deleted_file():
    with patch(
        "src.pipeline.financing_docs.scan_docs",
        return_value={"itbi": {"document": "v1", "metadata": {"content_hash": "hash1", "source_file": "itbi.pdf"}}},
    ):
        pipeline.sync_financing_docs()

    with patch("src.pipeline.financing_docs.scan_docs", return_value={}):
        stats = pipeline.sync_financing_docs()

    assert stats == {"indexed": 0, "removed": 1}
    collection = chroma_store.get_financing_collection()
    assert collection.get(ids=["itbi"], include=[])["ids"] == []
