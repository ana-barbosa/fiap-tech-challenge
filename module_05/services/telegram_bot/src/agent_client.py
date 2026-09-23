import requests

from . import config

TIMEOUT_SECONDS = 30


class AgentUnavailableError(Exception):
    pass


def send_message(conversation_id: str, message: str) -> dict:
    try:
        response = requests.post(
            f"{config.AGENT_BACKEND_INTERNAL_URL}/chat",
            json={"conversation_id": conversation_id, "message": message, "channel": "telegram"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise AgentUnavailableError(str(exc)) from exc
