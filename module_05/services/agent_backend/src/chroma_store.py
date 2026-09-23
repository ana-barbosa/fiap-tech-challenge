import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from . import config

_client = None


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=config.CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def reset_client_cache() -> None:
    global _client
    _client = None


def get_listings_collection():
    return get_client().get_collection("listings")


def get_geo_collection():
    return get_client().get_collection("geo")


def get_roi_collection():
    return get_client().get_collection("roi_summary")


def get_financing_collection():
    return get_client().get_collection("financing_kb")


def is_ready() -> bool:
    try:
        return get_listings_collection().count() > 0
    except Exception:
        return False


def warm_up() -> None:
    DefaultEmbeddingFunction()(["warmup"])
