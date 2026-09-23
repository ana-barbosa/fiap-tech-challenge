import logging
from datetime import datetime, timezone

from . import chroma_store, crm_client, financing_docs, roi, wikipedia_geo

logger = logging.getLogger(__name__)

LISTING_METADATA_FIELDS = [
    "listing_type",
    "city",
    "neighborhood",
    "property_type",
    "price",
    "rooms",
    "area_sqm",
    "status",
    "updated_at",
]


def _listing_document(listing: dict) -> str:
    return (
        f"{listing['property_type']} para {listing['listing_type']} em "
        f"{listing['neighborhood']}, {listing['city']}. {listing['description']}"
    )


def _listing_metadata(listing: dict) -> dict:
    return {field: listing[field] for field in LISTING_METADATA_FIELDS}


def sync_listings(current_listings: list[dict]) -> dict:
    collection = chroma_store.get_listings_collection()
    by_id = {str(listing["id"]): listing for listing in current_listings}
    current_ids = list(by_id)

    existing = collection.get(ids=current_ids, include=["metadatas"]) if current_ids else {"ids": [], "metadatas": []}
    existing_updated_at = dict(zip(existing["ids"], (m.get("updated_at") for m in existing["metadatas"])))

    changed_segments: set[str] = set()
    upsert_ids, upsert_docs, upsert_meta = [], [], []
    for listing_id, listing in by_id.items():
        if existing_updated_at.get(listing_id) == listing["updated_at"]:
            continue
        upsert_ids.append(listing_id)
        upsert_docs.append(_listing_document(listing))
        upsert_meta.append(_listing_metadata(listing))
        changed_segments.add(roi.segment_key(listing["city"], listing["neighborhood"], listing["property_type"]))

    if upsert_ids:
        collection.upsert(ids=upsert_ids, documents=upsert_docs, metadatas=upsert_meta)

    all_existing_ids = set(collection.get(include=[])["ids"])
    stale_ids = all_existing_ids - set(current_ids)
    if stale_ids:
        stale = collection.get(ids=list(stale_ids), include=["metadatas"])
        for meta in stale["metadatas"]:
            changed_segments.add(roi.segment_key(meta["city"], meta["neighborhood"], meta["property_type"]))
        collection.delete(ids=list(stale_ids))

    return {"indexed": len(upsert_ids), "removed": len(stale_ids), "changed_segments": changed_segments}


def sync_geo(current_listings: list[dict]) -> dict:
    collection = chroma_store.get_geo_collection()
    cities = {listing["city"] for listing in current_listings}
    if not cities:
        return {"scraped": 0}

    existing_ids = set(collection.get(ids=list(cities), include=[])["ids"])
    missing = cities - existing_ids

    scraped = 0
    for city in missing:
        try:
            geo = wikipedia_geo.scrape_city_geo(city)
        except Exception:
            logger.warning("Failed to scrape geo data for %s; will retry next cycle", city, exc_info=True)
            continue
        collection.upsert(ids=[city], documents=[geo["document"]], metadatas=[geo["metadata"]])
        scraped += 1

    return {"scraped": scraped}


def _roi_document(data: dict) -> str:
    pct = data["gross_yield"] * 100
    return (
        f"Imóveis do tipo {data['property_type']} no bairro {data['neighborhood']}, "
        f"{data['city']}, têm yield bruto estimado de {pct:.2f}% ao ano "
        f"(baseado em {data['sale_sample_size']} anúncio(s) de venda e "
        f"{data['rent_sample_size']} de aluguel)."
    )


def sync_roi(current_listings: list[dict], changed_segments: set[str]) -> dict:
    if not changed_segments:
        return {"updated": 0, "removed": 0}

    logger.info("Recomputing ROI for %d changed segment(s)", len(changed_segments))
    collection = chroma_store.get_roi_collection()
    computed = roi.compute_roi_segments(current_listings, segment_keys=changed_segments)

    upsert_ids, upsert_docs, upsert_meta = [], [], []
    delete_candidates = []
    for key, data in computed.items():
        if data is None:
            delete_candidates.append(key)
            continue
        upsert_ids.append(key)
        upsert_docs.append(_roi_document(data))
        upsert_meta.append({**data, "computed_at": datetime.now(timezone.utc).isoformat()})

    if upsert_ids:
        collection.upsert(ids=upsert_ids, documents=upsert_docs, metadatas=upsert_meta)

    removed = 0
    if delete_candidates:
        existing = set(collection.get(ids=delete_candidates, include=[])["ids"])
        if existing:
            collection.delete(ids=list(existing))
            removed = len(existing)

    return {"updated": len(upsert_ids), "removed": removed}


def sync_financing_docs() -> dict:
    collection = chroma_store.get_financing_collection()
    current = financing_docs.scan_docs()
    current_ids = list(current)

    existing = collection.get(ids=current_ids, include=["metadatas"]) if current_ids else {"ids": [], "metadatas": []}
    existing_hash = dict(zip(existing["ids"], (m.get("content_hash") for m in existing["metadatas"])))

    upsert_ids, upsert_docs, upsert_meta = [], [], []
    for doc_id, doc in current.items():
        if existing_hash.get(doc_id) == doc["metadata"]["content_hash"]:
            continue
        upsert_ids.append(doc_id)
        upsert_docs.append(doc["document"])
        upsert_meta.append(doc["metadata"])

    if upsert_ids:
        collection.upsert(ids=upsert_ids, documents=upsert_docs, metadatas=upsert_meta)

    all_existing_ids = set(collection.get(include=[])["ids"])
    stale_ids = all_existing_ids - set(current_ids)
    if stale_ids:
        collection.delete(ids=list(stale_ids))

    if upsert_ids or stale_ids:
        logger.info("Financing docs sync: %d indexed, %d removed", len(upsert_ids), len(stale_ids))

    return {"indexed": len(upsert_ids), "removed": len(stale_ids)}


def run_once() -> dict:
    current_listings = crm_client.fetch_available_listings()

    listings_stats = sync_listings(current_listings)
    geo_stats = sync_geo(current_listings)
    roi_stats = sync_roi(current_listings, listings_stats["changed_segments"])
    financing_stats = sync_financing_docs()

    return {
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "listings_available": len(current_listings),
        "listings_indexed": listings_stats["indexed"],
        "listings_removed": listings_stats["removed"],
        "geo_cities_scraped": geo_stats["scraped"],
        "roi_segments_updated": roi_stats["updated"],
        "roi_segments_removed": roi_stats["removed"],
        "financing_docs_indexed": financing_stats["indexed"],
        "financing_docs_removed": financing_stats["removed"],
    }
