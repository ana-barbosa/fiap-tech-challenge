import json
import sys
from datetime import datetime, timedelta, timezone
from itertools import cycle
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import crm_client, database  # noqa: E402

PROPERTY_TYPE_LABEL = {"apartment": "apartamento", "house": "casa"}
CHANNEL_CYCLE = ["website", "website", "telegram"]

COLD_LEAD_SCENARIOS = [
    ("comprar", "sale", "Taubaté"),
    ("alugar", "rent", "Guaratinguetá"),
    ("investir", "sale", "Pindamonhangaba"),
    ("desconhecido", None, "Ubatuba"),
]
COLD_LEAD_DAYS_AGO = [2, 3, 5, 6]


def _price_label(listing: dict) -> str:
    price = f"R$ {listing['price']:,.0f}".replace(",", ".")
    return price if listing["listing_type"] == "sale" else f"{price}/mês"


def _read_seed_visits() -> list[dict]:
    seeded = []
    for visit in crm_client.list_visits():
        if not visit["conversation_id"].startswith("seed-"):
            continue
        listing = crm_client.get_property(visit["property_id"])
        if listing is None:
            continue
        seeded.append({"visit": visit, "listing": listing})
    return seeded


def _booking_history(listing: dict, lead_name: str) -> list[dict]:
    property_label = PROPERTY_TYPE_LABEL[listing["property_type"]]
    goal = "comprar" if listing["listing_type"] == "sale" else "alugar"
    return [
        {
            "role": "user",
            "content": (
                f"Oi, meu nome é {lead_name}. Estou procurando um(a) {property_label} em "
                f"{listing['city']} para {goal}."
            ),
        },
        {
            "role": "assistant",
            "content": (
                f"Olá, {lead_name}! Encontrei um(a) {property_label} em {listing['neighborhood']}, "
                f"{listing['city']}, com {listing['rooms']} quartos, por {_price_label(listing)}. "
                "Quer agendar uma visita?"
            ),
        },
        {"role": "user", "content": "Quero sim, pode agendar!"},
        {"role": "assistant", "content": "Visita agendada - nosso corretor te espera no horário combinado."},
    ]


def _booking_summary(listing: dict, lead_name: str) -> str:
    property_label = PROPERTY_TYPE_LABEL[listing["property_type"]]
    goal = "comprar" if listing["listing_type"] == "sale" else "alugar"
    return (
        f"{lead_name} está em busca de um(a) {property_label} para {goal} em {listing['city']}, "
        f"com {listing['rooms']} quartos. Foi apresentado um imóvel em {listing['neighborhood']}, "
        f"disponível por {_price_label(listing)}, e a visita já foi agendada."
    )


def _booking_qualification(listing: dict) -> dict:
    return {
        "intencao": "comprar" if listing["listing_type"] == "sale" else "alugar",
        "preco_min": round(listing["price"] * 0.85, -2),
        "preco_max": round(listing["price"] * 1.15, -2),
        "quartos": listing["rooms"],
        "regiao": [listing["city"]],
    }


def _last_active_at(visit: dict, listing: dict, now: datetime) -> str:
    if listing["status"] != "available":
        confirmed = datetime.fromisoformat(visit["confirmed_datetime"]).replace(tzinfo=timezone.utc)
        return confirmed.isoformat()
    return now.isoformat()


def _cold_lead_history(intent: str, listing: dict) -> list[dict]:
    property_label = PROPERTY_TYPE_LABEL[listing["property_type"]]
    price = _price_label(listing)

    if intent == "comprar":
        return [
            {"role": "user", "content": f"Oi, estou pensando em comprar um(a) {property_label} em {listing['city']}."},
            {
                "role": "assistant",
                "content": (
                    f"Olá! Encontrei um(a) {property_label} em {listing['neighborhood']}, {listing['city']}, "
                    f"com {listing['rooms']} quartos, por {price}. Quer mais detalhes ou agendar uma visita?"
                ),
            },
            {"role": "user", "content": "Deixa eu pensar com calma e te aviso."},
        ]
    if intent == "alugar":
        return [
            {"role": "user", "content": f"Oi, estou procurando um(a) {property_label} para alugar em {listing['city']}."},
            {
                "role": "assistant",
                "content": (
                    f"Olá! Temos um(a) {property_label} disponível em {listing['neighborhood']}, "
                    f"{listing['city']}, por {price}. Quer agendar uma visita?"
                ),
            },
            {"role": "user", "content": "Vou avaliar e retorno depois."},
        ]
    if intent == "investir":
        return [
            {
                "role": "user",
                "content": "Estou avaliando investir em imóveis na região - vocês têm algo com bom potencial de retorno?",
            },
            {
                "role": "assistant",
                "content": (
                    f"Temos um(a) {property_label} em {listing['neighborhood']}, {listing['city']}, por {price} - "
                    "pode ser interessante para revenda ou aluguel. Quer que eu detalhe o potencial de retorno?"
                ),
            },
            {"role": "user", "content": "Manda mais informações que eu analiso com calma."},
        ]
    return [
        {"role": "user", "content": "Quais cidades litorâneas seriam boas pra viver na região?"},
        {
            "role": "assistant",
            "content": (
                "Algumas boas opções no litoral são Ubatuba, Caraguatatuba, São Sebastião e Ilhabela - "
                f"{listing['city']} em particular é conhecida pelas praias preservadas e o clima costeiro tranquilo."
            ),
        },
        {"role": "user", "content": f"{listing['city']} parece legal! Tem algo disponível por lá?"},
        {
            "role": "assistant",
            "content": (
                f"Sim! Temos um(a) {property_label} em {listing['neighborhood']}, {listing['city']}, por {price}. "
                "Quer que eu te passe mais detalhes?"
            ),
        },
        {"role": "user", "content": "Deixa eu pensar, depois te falo."},
    ]


def _cold_lead_qualification(intent: str, listing: dict) -> dict:
    if intent in ("comprar", "alugar"):
        return {
            "intencao": intent,
            "preco_min": round(listing["price"] * 0.85, -2),
            "preco_max": round(listing["price"] * 1.15, -2),
            "quartos": listing["rooms"],
            "regiao": [listing["city"]],
        }
    if intent == "investir":
        return {
            "intencao": "investir",
            "perfil_investidor": "iniciante",
            "valor_investimento": round(listing["price"] * 1.1, -2),
            "retorno_esperado": 0.08,
            "regiao": [listing["city"]],
        }
    return {"regiao": [listing["city"]]}


def _cold_lead_summary(intent: str, listing: dict) -> str:
    property_label = PROPERTY_TYPE_LABEL[listing["property_type"]]
    price = _price_label(listing)

    if intent == "comprar":
        return (
            f"Cliente interessado em comprar um(a) {property_label} em {listing['city']}. Foi apresentado "
            f"um imóvel em {listing['neighborhood']}, por {price}, mas ainda não agendou visita nem retornou contato."
        )
    if intent == "alugar":
        return (
            f"Cliente em busca de um(a) {property_label} para alugar em {listing['city']}. Foi apresentado "
            f"um imóvel em {listing['neighborhood']}, por {price}, mas ainda não agendou visita nem retornou contato."
        )
    if intent == "investir":
        return (
            f"Cliente avaliando investir em um(a) {property_label} em {listing['city']} "
            f"({listing['neighborhood']}), por {price}. Pediu detalhes sobre potencial de retorno, mas "
            "ainda não retornou contato."
        )
    return (
        f"Cliente perguntou sobre cidades litorâneas para morar na região e demonstrou interesse em "
        f"{listing['city']}, chegando a ver um(a) {property_label} em {listing['neighborhood']} por {price}, "
        "mas ainda não definiu uma intenção (comprar, alugar ou investir) nem retornou contato."
    )


def _pick_cold_lead_property(listing_type: str | None, city: str) -> dict:
    results = crm_client.list_properties(status="available", listing_type=listing_type, city=city, limit=1)
    return results[0]


def _build_booking_rows(now: datetime) -> list[tuple]:
    channels = cycle(CHANNEL_CYCLE)
    rows = []
    for entry in _read_seed_visits():
        visit, listing = entry["visit"], entry["listing"]
        rows.append(
            (
                visit["conversation_id"],
                json.dumps(_booking_history(listing, visit["lead_name"])),
                json.dumps(_booking_qualification(listing)),
                json.dumps({str(listing["id"]): listing}),
                _last_active_at(visit, listing, now),
                next(channels),
                _booking_summary(listing, visit["lead_name"]),
            )
        )
    return rows


def _build_cold_lead_rows(now: datetime) -> list[tuple]:
    rows = []
    for index, (intent, listing_type, city) in enumerate(COLD_LEAD_SCENARIOS):
        listing = _pick_cold_lead_property(listing_type, city)
        last_active_at = (now - timedelta(days=COLD_LEAD_DAYS_AGO[index])).isoformat()
        rows.append(
            (
                f"seed-cold-{index + 1}",
                json.dumps(_cold_lead_history(intent, listing)),
                json.dumps(_cold_lead_qualification(intent, listing)),
                json.dumps({str(listing["id"]): listing}),
                last_active_at,
                "website",
                _cold_lead_summary(intent, listing),
            )
        )
    return rows


def seed() -> None:
    now = datetime.now(timezone.utc)
    rows = _build_booking_rows(now - timedelta(hours=2)) + _build_cold_lead_rows(now)

    with database.connection_scope() as conn:
        conn.executemany("DELETE FROM conversations WHERE conversation_id = ?", [(row[0],) for row in rows])
        conn.executemany(
            """
            INSERT INTO conversations
                (conversation_id, history_json, qualification_json, current_specialist,
                 shown_listings_json, last_active_at, channel, summary)
            VALUES (?, ?, ?, 'real_estate', ?, ?, ?, ?)
            """,
            rows,
        )

    print(f"Seeded {len(rows)} conversations.")


if __name__ == "__main__":
    seed()
