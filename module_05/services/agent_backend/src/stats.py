from datetime import datetime, timedelta, timezone

from . import config, conversation_store, followup
from .conversation_store import ConversationState
from .qualification import Intent, Qualification

UNKNOWN_INTENT_KEY = "desconhecido"


def _is_cold(state: ConversationState) -> bool:
    if not state.shown_listings:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=config.FOLLOWUP_INACTIVITY_SECONDS)
    if datetime.fromisoformat(state.last_active_at) > cutoff:
        return False
    return followup.find_followup_candidate(state) is not None


def lead_stats() -> dict:
    conversations = conversation_store.list_all()

    intent_breakdown = {intent.value: 0 for intent in Intent}
    intent_breakdown[UNKNOWN_INTENT_KEY] = 0
    cold_leads = 0

    for state in conversations:
        qualification = Qualification(**state.qualification)
        key = qualification.intent.value if qualification.intent else UNKNOWN_INTENT_KEY
        intent_breakdown[key] += 1

        if _is_cold(state):
            cold_leads += 1

    return {
        "total_clients": len(conversations),
        "intent_breakdown": intent_breakdown,
        "cold_leads": cold_leads,
    }
