from unittest.mock import Mock, patch

import pytest
import requests

from src.agent_client import AgentUnavailableError, send_message


def test_send_message_returns_json_on_success():
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = {
        "reply": "Oi!",
        "qualification": {"intencao": "alugar"},
        "specialist": "real_estate",
    }
    fake_response.raise_for_status = Mock()
    with patch("src.agent_client.requests.post", return_value=fake_response) as mocked_post:
        result = send_message("123", "quero alugar")

    assert result == {"reply": "Oi!", "qualification": {"intencao": "alugar"}, "specialist": "real_estate"}
    assert mocked_post.call_args.kwargs["json"] == {
        "conversation_id": "123",
        "message": "quero alugar",
        "channel": "telegram",
    }


def test_send_message_raises_agent_unavailable_on_connection_error():
    with patch("src.agent_client.requests.post", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(AgentUnavailableError):
            send_message("123", "oi")
