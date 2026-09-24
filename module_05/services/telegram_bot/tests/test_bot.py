from unittest.mock import patch

from src.agent_client import AgentUnavailableError
from src.bot import CANNOT_TRANSCRIBE_REPLY, NON_TEXT_REPLY, START_REPLY, process_update
from src.telegram_client import TelegramUnavailableError


def test_text_message_relays_agent_reply():
    update = {"message": {"chat": {"id": 123}, "text": "quero alugar um apê"}}
    with patch("src.bot.agent_client.send_message", return_value={"reply": "Claro!"}) as mocked_agent, \
            patch("src.bot.telegram_client.send_message") as mocked_telegram:
        process_update(update)

    mocked_agent.assert_called_once_with("123", "quero alugar um apê")
    mocked_telegram.assert_called_once_with(123, "Claro!")


def test_start_command_sends_canned_reply_without_calling_agent():
    update = {"message": {"chat": {"id": 123}, "text": "/start"}}
    with patch("src.bot.agent_client.send_message") as mocked_agent, \
            patch("src.bot.telegram_client.send_message") as mocked_telegram:
        process_update(update)

    mocked_agent.assert_not_called()
    mocked_telegram.assert_called_once_with(123, START_REPLY)


def test_non_text_message_sends_canned_reply_without_calling_agent():
    update = {"message": {"chat": {"id": 123}, "sticker": {}}}
    with patch("src.bot.agent_client.send_message") as mocked_agent, \
            patch("src.bot.telegram_client.send_message") as mocked_telegram:
        process_update(update)

    mocked_agent.assert_not_called()
    mocked_telegram.assert_called_once_with(123, NON_TEXT_REPLY)


def test_update_without_message_key_is_a_no_op():
    update = {"edited_message": {"chat": {"id": 123}, "text": "oi"}}
    with patch("src.bot.agent_client.send_message") as mocked_agent, \
            patch("src.bot.telegram_client.send_message") as mocked_telegram:
        process_update(update)

    mocked_agent.assert_not_called()
    mocked_telegram.assert_not_called()


def test_voice_message_transcribes_and_relays_agent_reply():
    update = {"message": {"chat": {"id": 123}, "voice": {"file_id": "file-abc"}}}
    with patch("src.bot.telegram_client.get_file_bytes", return_value=b"fake-ogg-bytes") as mocked_get_file, \
            patch("src.bot.agent_client.transcribe", return_value="quero alugar um apê") as mocked_transcribe, \
            patch("src.bot.agent_client.send_message", return_value={"reply": "Claro!"}) as mocked_agent, \
            patch("src.bot.telegram_client.send_message") as mocked_telegram:
        process_update(update)

    mocked_get_file.assert_called_once_with("file-abc")
    mocked_transcribe.assert_called_once_with(b"fake-ogg-bytes")
    mocked_agent.assert_called_once_with("123", "quero alugar um apê")
    mocked_telegram.assert_called_once_with(123, "Claro!")


def test_voice_message_with_empty_transcription_sends_canned_reply_without_calling_agent():
    update = {"message": {"chat": {"id": 123}, "voice": {"file_id": "file-abc"}}}
    with patch("src.bot.telegram_client.get_file_bytes", return_value=b"fake-ogg-bytes"), \
            patch("src.bot.agent_client.transcribe", return_value="   "), \
            patch("src.bot.agent_client.send_message") as mocked_agent, \
            patch("src.bot.telegram_client.send_message") as mocked_telegram:
        process_update(update)

    mocked_agent.assert_not_called()
    mocked_telegram.assert_called_once_with(123, CANNOT_TRANSCRIBE_REPLY)


def test_voice_message_download_failure_sends_canned_reply_without_calling_agent():
    update = {"message": {"chat": {"id": 123}, "voice": {"file_id": "file-abc"}}}
    with patch("src.bot.telegram_client.get_file_bytes", side_effect=TelegramUnavailableError("boom")), \
            patch("src.bot.agent_client.transcribe") as mocked_transcribe, \
            patch("src.bot.agent_client.send_message") as mocked_agent, \
            patch("src.bot.telegram_client.send_message") as mocked_telegram:
        process_update(update)

    mocked_transcribe.assert_not_called()
    mocked_agent.assert_not_called()
    mocked_telegram.assert_called_once_with(123, CANNOT_TRANSCRIBE_REPLY)


def test_voice_message_transcription_failure_sends_canned_reply_without_calling_agent():
    update = {"message": {"chat": {"id": 123}, "voice": {"file_id": "file-abc"}}}
    with patch("src.bot.telegram_client.get_file_bytes", return_value=b"fake-ogg-bytes"), \
            patch("src.bot.agent_client.transcribe", side_effect=AgentUnavailableError("boom")), \
            patch("src.bot.agent_client.send_message") as mocked_agent, \
            patch("src.bot.telegram_client.send_message") as mocked_telegram:
        process_update(update)

    mocked_agent.assert_not_called()
    mocked_telegram.assert_called_once_with(123, CANNOT_TRANSCRIBE_REPLY)
