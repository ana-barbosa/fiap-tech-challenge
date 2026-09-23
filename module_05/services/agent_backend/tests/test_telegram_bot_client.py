from unittest.mock import MagicMock, patch

import requests as requests_module

from src import telegram_bot_client


def test_push_message_posts_chat_id_and_text():
    mock_response = MagicMock(status_code=200)
    with patch("src.telegram_bot_client.requests.post", return_value=mock_response) as mock_post:
        telegram_bot_client.push_message("123", "Oi de novo!")

    assert mock_post.call_args.kwargs["json"] == {"chat_id": 123, "text": "Oi de novo!"}


def test_push_message_swallows_request_exception():
    with patch("src.telegram_bot_client.requests.post", side_effect=requests_module.RequestException("boom")):
        telegram_bot_client.push_message("123", "Oi de novo!")


def test_push_message_swallows_non_numeric_chat_id():
    with patch("src.telegram_bot_client.requests.post") as mock_post:
        telegram_bot_client.push_message("seed-66", "Oi de novo!")

    mock_post.assert_not_called()
