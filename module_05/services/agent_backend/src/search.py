import logging

from . import chroma_store

logger = logging.getLogger(__name__)

# Listings are indexed with English property_type values ("apartment"/"house"), but the
# agent's tool-calling LLM sometimes passes the Portuguese word the customer used instead.
_PROPERTY_TYPE_ALIASES = {
    "apartamento": "apartment",
    "apartment": "apartment",
    "casa": "house",
    "house": "house",
}


def _normalize_property_type(property_type: str | None) -> str | None:
    if property_type is None:
        return None
    return _PROPERTY_TYPE_ALIASES.get(property_type.strip().lower(), property_type)


def _combine_where(clauses: list[dict]) -> dict | None:
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def search_listings(
    query: str,
    cities: list[str] | None = None,
    property_type: str | None = None,
    listing_type: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    rooms: int | None = None,
    n_results: int = 5,
) -> list[dict]:
    clauses = []
    if cities:
        clauses.append({"city": {"$in": cities}})
    if property_type:
        clauses.append({"property_type": _normalize_property_type(property_type)})
    if listing_type:
        clauses.append({"listing_type": listing_type})
    if price_min is not None:
        clauses.append({"price": {"$gte": price_min}})
    if price_max is not None:
        clauses.append({"price": {"$lte": price_max}})
    if rooms is not None:
        clauses.append({"rooms": {"$gte": rooms}})

    collection = chroma_store.get_listings_collection()
    result = collection.query(
        query_texts=[query], n_results=n_results, where=_combine_where(clauses)
    )

    listings = [
        {"id": doc_id, "description": document, **metadata}
        for doc_id, document, metadata in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0]
        )
    ]
    # ids are internal listing keys, not PII - safe to log in full.
    logger.info("search_listings(%r, filters=%s) -> ids=%s", query, _combine_where(clauses), [item["id"] for item in listings])
    return listings


def search_geo(query: str, n_results: int = 3) -> list[dict]:
    collection = chroma_store.get_geo_collection()
    result = collection.query(query_texts=[query], n_results=n_results)

    cities = [
        {"city": doc_id, "content": document, **metadata}
        for doc_id, document, metadata in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0]
        )
    ]
    logger.info("search_geo(%r) -> cities=%s", query, [item["city"] for item in cities])
    return cities


def search_roi(
    query: str,
    cities: list[str] | None = None,
    property_type: str | None = None,
    n_results: int = 5,
) -> list[dict]:
    clauses = []
    if cities:
        clauses.append({"city": {"$in": cities}})
    if property_type:
        clauses.append({"property_type": _normalize_property_type(property_type)})

    collection = chroma_store.get_roi_collection()
    result = collection.query(
        query_texts=[query], n_results=n_results, where=_combine_where(clauses)
    )

    segments = [
        {"segment": doc_id, "summary": document, **metadata}
        for doc_id, document, metadata in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0]
        )
    ]
    logger.info("search_roi(%r, filters=%s) -> segments=%s", query, _combine_where(clauses), [item["segment"] for item in segments])
    return segments


def search_financing(query: str, n_results: int = 3) -> list[dict]:
    collection = chroma_store.get_financing_collection()
    result = collection.query(query_texts=[query], n_results=n_results)

    docs = [
        {"topic": doc_id, "content": document, **metadata}
        for doc_id, document, metadata in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0]
        )
    ]
    logger.info("search_financing(%r) -> topics=%s", query, [item["topic"] for item in docs])
    return docs
