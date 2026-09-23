import logging

from . import agent_client, telegram_client

logger = logging.getLogger(__name__)

NON_TEXT_REPLY = "Só consigo responder a mensagens de texto por enquanto."
START_REPLY = (
    "Olá! Sou a assistente virtual imobiliária do Vale do Paraíba. "
    "Me conte o que você procura - por exemplo, um apartamento para alugar em Taubaté."
)


def process_update(update: dict) -> None:
    message = update.get("message")
    if message is None:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text")

    if text is None:
        logger.info("Non-text message received from chat_id=%s", chat_id)
        telegram_client.send_message(chat_id, NON_TEXT_REPLY)
        return

    if text == "/start":
        logger.info("/start received from chat_id=%s", chat_id)
        telegram_client.send_message(chat_id, START_REPLY)
        return

    logger.info("Text message received from chat_id=%s, forwarding to agent_backend", chat_id)
    result = agent_client.send_message(str(chat_id), text)
    telegram_client.send_message(chat_id, result["reply"])
