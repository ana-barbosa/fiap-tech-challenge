import os
from pathlib import Path


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = Path(_require("DB_PATH"))
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
STATIC_PHOTOS_DIR = Path(_require("STATIC_PHOTOS_DIR"))

BROKER_NAME = _require("BROKER_NAME")
BROKER_CONTACT = _require("BROKER_CONTACT")
