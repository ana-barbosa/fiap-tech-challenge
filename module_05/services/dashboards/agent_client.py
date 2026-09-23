import requests

import config

TIMEOUT_SECONDS = 5


class AgentBackendUnavailableError(Exception):
    pass


def get_summary(conversation_id: str) -> str:
    try:
        response = requests.get(
            f"{config.AGENT_BACKEND_INTERNAL_URL}/conversations/{conversation_id}/summary",
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["summary"]
    except requests.RequestException as exc:
        raise AgentBackendUnavailableError(str(exc)) from exc


def get_lead_stats() -> dict:
    try:
        response = requests.get(f"{config.AGENT_BACKEND_INTERNAL_URL}/stats/leads", timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise AgentBackendUnavailableError(str(exc)) from exc


def get_observability_stats() -> dict:
    try:
        response = requests.get(f"{config.AGENT_BACKEND_INTERNAL_URL}/stats/observability", timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise AgentBackendUnavailableError(str(exc)) from exc
