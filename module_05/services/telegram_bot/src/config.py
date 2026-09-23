import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
AGENT_BACKEND_INTERNAL_URL = _require("AGENT_BACKEND_INTERNAL_URL")
OFFSET_FILE_PATH = _require("OFFSET_FILE_PATH")
GETUPDATES_TIMEOUT_SECONDS = int(_require("GETUPDATES_TIMEOUT_SECONDS"))
