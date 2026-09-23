import logging

import requests

from . import config

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS_MARGIN = 5


class TelegramUnavailableError(Exception):
    pass


def get_updates(offset: int | None, timeout: int) -> list[dict]:
    params: dict = {"timeout": timeout, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset

    try:
        response = requests.get(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates",
            params=params,
            timeout=timeout + TIMEOUT_SECONDS_MARGIN,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise TelegramUnavailableError(str(exc)) from exc

    return response.json()["result"]


def send_message(chat_id: int, text: str) -> None:
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=TIMEOUT_SECONDS_MARGIN,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise TelegramUnavailableError(str(exc)) from exc

    logger.info("Sent message to chat_id=%s", chat_id)
