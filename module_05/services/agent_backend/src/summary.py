import logging
from datetime import datetime, timezone

from . import conversation_store, prompts
from .conversation_store import ConversationState
from .llm import get_chat_model

logger = logging.getLogger(__name__)

NO_HISTORY_SUMMARY = "Nenhuma conversa registrada para este cliente ainda."


def _transcript(history: list[dict]) -> str:
    lines = [f"{'Cliente' if m['role'] == 'user' else 'Assistente'}: {m['content']}" for m in history]
    return "\n".join(lines)


def generate_summary(state: ConversationState) -> str:
    if not state.history:
        return NO_HISTORY_SUMMARY

    context = (
        f"Qualificação já coletada: {state.qualification}\n"
        f"Imóveis apresentados nesta conversa: {list(state.shown_listings.values())}\n\n"
        f"Transcrição da conversa:\n{_transcript(state.history)}"
    )

    model = get_chat_model()
    response = model.invoke(
        [
            {"role": "system", "content": prompts.SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ]
    )
    return response.content


def run_once() -> dict:
    stale = conversation_store.list_stale_summaries()

    for state in stale:
        text = generate_summary(state)
        conversation_store.set_summary(state.conversation_id, text, state.last_active_at)
        logger.info("Summary generated: conversation_id=%s", state.conversation_id)

    return {
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "conversations_checked": len(stale),
        "summarized": len(stale),
    }
