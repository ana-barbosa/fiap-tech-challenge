import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


CRM_INTERNAL_URL = _require("CRM_INTERNAL_URL")
CRM_PUBLIC_URL = _require("CRM_PUBLIC_URL")
AGENT_BACKEND_INTERNAL_URL = _require("AGENT_BACKEND_INTERNAL_URL")

CATALOG_FETCH_LIMIT = 100
