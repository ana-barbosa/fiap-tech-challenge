from unittest.mock import patch

from src.bot import NON_TEXT_REPLY, START_REPLY, process_update


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
