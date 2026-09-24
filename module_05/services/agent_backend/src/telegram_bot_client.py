import logging

import requests

from . import config

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 5


def push_message(chat_id: str, text: str) -> bool:
    try:
        numeric_chat_id = int(chat_id)
    except ValueError:
        logger.debug("Push skipped: chat_id=%s is not a valid Telegram chat id", chat_id)
        return False

    try:
        response = requests.post(
            f"{config.TELEGRAM_BOT_INTERNAL_URL}/push",
            json={"chat_id": numeric_chat_id, "text": text},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Push to chat_id=%s failed: %s", chat_id, exc)
        return False

    return True
