import sys
from pathlib import Path
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_client import AgentUnavailableError, send_message  # noqa: E402


def test_send_message_returns_json_on_success():
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = {
        "reply": "Oi!",
        "qualification": {"intencao": "alugar"},
        "specialist": "real_estate",
    }
    fake_response.raise_for_status = Mock()
    with patch("agent_client.requests.post", return_value=fake_response) as mocked_post:
        result = send_message("conv-1", "quero alugar")

    assert result == {"reply": "Oi!", "qualification": {"intencao": "alugar"}, "specialist": "real_estate"}
    assert mocked_post.call_args.kwargs["json"] == {"conversation_id": "conv-1", "message": "quero alugar"}


def test_send_message_raises_agent_unavailable_on_connection_error():
    with patch("agent_client.requests.post", side_effect=requests.ConnectionError("boom")):
        try:
            send_message("conv-1", "oi")
            assert False, "expected AgentUnavailableError"
        except AgentUnavailableError:
            pass
