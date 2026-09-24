import logging
from datetime import datetime, timedelta, timezone

from . import config, conversation_store, crm_client, telegram_bot_client
from .conversation_store import ConversationState

logger = logging.getLogger(__name__)


def find_eligible_conversations() -> list[ConversationState]:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=config.FOLLOWUP_INACTIVITY_SECONDS)
    return [
        state
        for state in conversation_store.list_by_channel("telegram")
        if datetime.fromisoformat(state.last_active_at) <= cutoff
    ]


def find_followup_candidate(state: ConversationState) -> str | None:
    booked = crm_client.get_confirmed_visit_property_ids(state.conversation_id)

    candidate = None
    for property_id, snapshot in state.shown_listings.items():
        if property_id in booked or snapshot.get("followed_up_at"):
            continue
        candidate = property_id
    return candidate


def build_message(snapshot: dict) -> str:
    property_type = snapshot.get("property_type") or "imóvel"
    city = snapshot.get("city") or ""
    neighborhood = snapshot.get("neighborhood") or ""
    price = snapshot.get("price")

    location = f"{neighborhood}, {city}" if neighborhood and city else (city or neighborhood)
    price_part = f", por R${price:,.0f}".replace(",", ".") if price is not None else ""

    return (
        f"Oi! Vi que você deu uma olhada em um(a) {property_type} em {location}{price_part} "
        "e ainda não agendou uma visita - ainda tem interesse? É só me chamar para marcar um "
        "horário quando quiser."
    )


def run_once() -> dict:
    conversations = find_eligible_conversations()
    nudged = 0

    for state in conversations:
        property_id = find_followup_candidate(state)
        if property_id is None:
            continue

        snapshot = state.shown_listings[property_id]
        if not telegram_bot_client.push_message(state.conversation_id, build_message(snapshot)):
            continue

        snapshot["followed_up_at"] = datetime.now(timezone.utc).isoformat()
        conversation_store.save(state)
        nudged += 1
        logger.info("Follow-up nudge sent: conversation_id=%s property_id=%s", state.conversation_id, property_id)

    return {
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "conversations_checked": len(conversations),
        "nudged": nudged,
    }
