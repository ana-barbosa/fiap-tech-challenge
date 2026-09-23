import logging
from datetime import datetime, timezone

from . import conversation_store, crm_client, telegram_bot_client
from .conversation_store import ConversationState

logger = logging.getLogger(__name__)


def find_price_drops(state: ConversationState) -> list[tuple[str, dict, float]]:
    drops = []
    for property_id, snapshot in state.shown_listings.items():
        listing = crm_client.get_property(property_id)
        if listing is None:
            continue

        baseline = snapshot.get("last_notified_price", snapshot.get("price"))
        current_price = listing["price"]
        if baseline is not None and current_price < baseline:
            drops.append((property_id, snapshot, current_price))

    return drops


def build_message(snapshot: dict, new_price: float) -> str:
    property_type = snapshot.get("property_type") or "imóvel"
    city = snapshot.get("city") or ""
    neighborhood = snapshot.get("neighborhood") or ""

    location = f"{neighborhood}, {city}" if neighborhood and city else (city or neighborhood)
    price_part = f"R${new_price:,.0f}".replace(",", ".")

    return (
        f"Boa notícia! O(a) {property_type} em {location} que você viu baixou de preço - "
        f"agora está por {price_part}. Ainda tem interesse? É só me chamar para agendar uma visita."
    )


def run_once() -> dict:
    conversations = conversation_store.list_by_channel("telegram")
    notified = 0

    for state in conversations:
        drops = find_price_drops(state)
        if not drops:
            continue

        for property_id, snapshot, new_price in drops:
            telegram_bot_client.push_message(state.conversation_id, build_message(snapshot, new_price))
            snapshot["last_notified_price"] = new_price
            notified += 1
            logger.info(
                "Price drop notification sent: conversation_id=%s property_id=%s new_price=%s",
                state.conversation_id,
                property_id,
                new_price,
            )

        conversation_store.save(state)

    return {
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "conversations_checked": len(conversations),
        "notified": notified,
    }
