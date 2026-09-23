from unittest.mock import Mock, patch

import pytest
import requests

from src.telegram_client import TelegramUnavailableError, get_updates, send_message


def test_get_updates_without_offset_omits_it_from_params():
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = {"result": [{"update_id": 1}]}
    fake_response.raise_for_status = Mock()
    with patch("src.telegram_client.requests.get", return_value=fake_response) as mocked_get:
        result = get_updates(None, 30)

    assert result == [{"update_id": 1}]
    called_url = mocked_get.call_args.args[0]
    assert called_url == "https://api.telegram.org/bottest-token/getUpdates"
    assert mocked_get.call_args.kwargs["params"] == {"timeout": 30, "allowed_updates": ["message"]}


def test_get_updates_with_offset_includes_it_in_params():
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = {"result": []}
    fake_response.raise_for_status = Mock()
    with patch("src.telegram_client.requests.get", return_value=fake_response) as mocked_get:
        get_updates(42, 30)

    assert mocked_get.call_args.kwargs["params"] == {"timeout": 30, "allowed_updates": ["message"], "offset": 42}


def test_get_updates_raises_telegram_unavailable_on_request_exception():
    with patch("src.telegram_client.requests.get", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(TelegramUnavailableError):
            get_updates(None, 30)


def test_send_message_posts_expected_payload():
    fake_response = Mock(status_code=200)
    fake_response.raise_for_status = Mock()
    with patch("src.telegram_client.requests.post", return_value=fake_response) as mocked_post:
        send_message(123, "olá")

    called_url = mocked_post.call_args.args[0]
    assert called_url == "https://api.telegram.org/bottest-token/sendMessage"
    assert mocked_post.call_args.kwargs["json"] == {"chat_id": 123, "text": "olá", "parse_mode": "Markdown"}


def test_send_message_raises_telegram_unavailable_on_request_exception():
    with patch("src.telegram_client.requests.post", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(TelegramUnavailableError):
            send_message(123, "olá")
