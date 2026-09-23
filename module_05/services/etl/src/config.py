import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


CRM_INTERNAL_URL = _require("CRM_INTERNAL_URL")
POLL_INTERVAL_SECONDS = int(_require("ETL_POLL_INTERVAL_SECONDS"))
CHROMA_PATH = _require("CHROMA_PATH")
WIKIPEDIA_REGION_URL = _require("WIKIPEDIA_REGION_URL")
