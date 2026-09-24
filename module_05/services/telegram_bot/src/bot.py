import logging

from . import agent_client, telegram_client

logger = logging.getLogger(__name__)

NON_TEXT_REPLY = "Só consigo responder a mensagens de texto por enquanto."
START_REPLY = (
    "Olá! Sou a assistente virtual imobiliária do Vale do Paraíba. "
    "Me conte o que você procura - por exemplo, um apartamento para alugar em Taubaté."
)
CANNOT_TRANSCRIBE_REPLY = "Não consegui entender o áudio - pode tentar de novo ou digitar sua mensagem?"


def _relay_to_agent(chat_id: int, text: str) -> None:
    result = agent_client.send_message(str(chat_id), text)
    telegram_client.send_message(chat_id, result["reply"])


def process_update(update: dict) -> None:
    message = update.get("message")
    if message is None:
        return

    chat_id = message["chat"]["id"]
    voice = message.get("voice")
    text = message.get("text")

    if voice is not None:
        logger.info("Voice message received from chat_id=%s", chat_id)
        try:
            audio_bytes = telegram_client.get_file_bytes(voice["file_id"])
            text = agent_client.transcribe(audio_bytes)
        except (telegram_client.TelegramUnavailableError, agent_client.AgentUnavailableError):
            logger.exception("Failed to transcribe voice message from chat_id=%s", chat_id)
            telegram_client.send_message(chat_id, CANNOT_TRANSCRIBE_REPLY)
            return

        if not text.strip():
            logger.info("Empty transcription for voice message from chat_id=%s", chat_id)
            telegram_client.send_message(chat_id, CANNOT_TRANSCRIBE_REPLY)
            return

        logger.info("Voice message transcribed for chat_id=%s, forwarding to agent_backend", chat_id)
        _relay_to_agent(chat_id, text)
        return

    if text is None:
        logger.info("Non-text message received from chat_id=%s", chat_id)
        telegram_client.send_message(chat_id, NON_TEXT_REPLY)
        return

    if text == "/start":
        logger.info("/start received from chat_id=%s", chat_id)
        telegram_client.send_message(chat_id, START_REPLY)
        return

    logger.info("Text message received from chat_id=%s, forwarding to agent_backend", chat_id)
    _relay_to_agent(chat_id, text)
