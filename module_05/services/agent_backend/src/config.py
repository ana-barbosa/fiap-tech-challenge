import os
from pathlib import Path


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


OPENAI_MODEL = require_env("OPENAI_MODEL")
OPENAI_API_KEY = require_env("OPENAI_API_KEY")

CHROMA_PATH = require_env("CHROMA_PATH")

CRM_BASE_URL = require_env("CRM_BASE_URL")

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(require_env("DB_PATH"))
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"

CONVERSATION_RETENTION_DAYS = int(require_env("CONVERSATION_RETENTION_DAYS"))
CONVERSATION_HISTORY_LIMIT = int(require_env("CONVERSATION_HISTORY_LIMIT"))

TELEGRAM_BOT_INTERNAL_URL = require_env("TELEGRAM_BOT_INTERNAL_URL")
WEBSITE_PUBLIC_URL = require_env("WEBSITE_PUBLIC_URL")

FOLLOWUP_INACTIVITY_SECONDS = int(require_env("FOLLOWUP_INACTIVITY_SECONDS"))
FOLLOWUP_POLL_INTERVAL_SECONDS = int(require_env("FOLLOWUP_POLL_INTERVAL_SECONDS"))

SUMMARY_IDLE_SECONDS = int(require_env("SUMMARY_IDLE_SECONDS"))
SUMMARY_POLL_INTERVAL_SECONDS = int(require_env("SUMMARY_POLL_INTERVAL_SECONDS"))

RATE_LIMIT_MAX_REQUESTS = int(require_env("RATE_LIMIT_MAX_REQUESTS"))
RATE_LIMIT_WINDOW_SECONDS = int(require_env("RATE_LIMIT_WINDOW_SECONDS"))
