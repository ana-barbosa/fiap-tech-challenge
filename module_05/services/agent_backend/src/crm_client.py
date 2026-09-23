import logging

import requests

from . import config

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 5


class CrmUnavailableError(Exception):
    pass


def get_confirmed_visit_property_ids(conversation_id: str) -> set[str]:
    try:
        response = requests.get(
            f"{config.CRM_BASE_URL}/visits",
            params={"conversation_id": conversation_id, "status": "confirmed"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CrmUnavailableError(str(exc)) from exc

    return {str(visit["property_id"]) for visit in response.json()}


def list_visits(**filters) -> list[dict]:
    try:
        response = requests.get(
            f"{config.CRM_BASE_URL}/visits",
            params={k: v for k, v in filters.items() if v is not None},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CrmUnavailableError(str(exc)) from exc

    return response.json()


def list_properties(**filters) -> list[dict]:
    try:
        response = requests.get(
            f"{config.CRM_BASE_URL}/properties",
            params={k: v for k, v in filters.items() if v is not None},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CrmUnavailableError(str(exc)) from exc

    return response.json()


def get_property(listing_id: int) -> dict | None:
    try:
        response = requests.get(f"{config.CRM_BASE_URL}/properties/{listing_id}", timeout=TIMEOUT_SECONDS)
        if response.status_code == 404:
            return None
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CrmUnavailableError(str(exc)) from exc

    return response.json()


def book_visit(
    property_id: int,
    conversation_id: str,
    lead_name: str,
    lead_contact: str,
    requested_datetime: str,
    channel: str | None = None,
) -> dict:
    payload = {
        "property_id": property_id,
        "conversation_id": conversation_id,
        "lead_name": lead_name,
        "lead_contact": lead_contact,
        "requested_datetime": requested_datetime,
    }
    if channel is not None:
        payload["channel"] = channel

    try:
        response = requests.post(f"{config.CRM_BASE_URL}/visits", json=payload, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        logger.warning("CRM visit booking request failed for property_id=%s: %s", property_id, exc)
        return {"status": "error", "detail": "Não foi possível conectar ao sistema de agendamento no momento."}

    if response.status_code == 201:
        confirmation = response.json()
        # lead_name/lead_contact are deliberately not logged here (PII).
        logger.info(
            "Visit booked: property_id=%s broker=%s confirmed_datetime=%s",
            confirmation.get("property_id"),
            confirmation.get("broker_name"),
            confirmation.get("confirmed_datetime"),
        )
        return confirmation

    detail = response.json().get("detail", "Erro ao agendar a visita.")
    if not isinstance(detail, str):
        # FastAPI's own request-validation errors (as opposed to the endpoint's explicit
        # HTTPException calls) return `detail` as a list of per-field error dicts, not a
        # string - fall back to a message the LLM can safely relay as-is.
        detail = "Não foi possível agendar a visita com os dados informados - confira nome, contato e data."
    logger.info(
        "CRM rejected visit booking for property_id=%s, requested_datetime=%s (status %d): %s",
        property_id,
        requested_datetime,
        response.status_code,
        detail,
    )
    return {"status": "error", "detail": detail}
