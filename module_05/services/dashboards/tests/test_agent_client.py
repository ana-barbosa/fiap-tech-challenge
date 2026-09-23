import sys
from pathlib import Path
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_client import (  # noqa: E402
    AgentBackendUnavailableError,
    get_lead_stats,
    get_observability_stats,
    get_summary,
)


def test_get_summary_returns_the_summary_field():
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = {"summary": "Cliente busca apê em Taubaté."}
    fake_response.raise_for_status = Mock()
    with patch("agent_client.requests.get", return_value=fake_response) as mocked_get:
        result = get_summary("conv-1")

    assert result == "Cliente busca apê em Taubaté."
    assert mocked_get.call_args.args[0].endswith("/conversations/conv-1/summary")


def test_get_summary_raises_on_connection_error():
    with patch("agent_client.requests.get", side_effect=requests.ConnectionError("boom")):
        try:
            get_summary("conv-1")
            assert False, "expected AgentBackendUnavailableError"
        except AgentBackendUnavailableError:
            pass


def test_get_lead_stats_returns_json_on_success():
    fake_stats = {"total_clients": 5, "intent_breakdown": {"comprar": 2}, "cold_leads": 1}
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = fake_stats
    fake_response.raise_for_status = Mock()
    with patch("agent_client.requests.get", return_value=fake_response):
        assert get_lead_stats() == fake_stats


def test_get_lead_stats_raises_on_connection_error():
    with patch("agent_client.requests.get", side_effect=requests.ConnectionError("boom")):
        try:
            get_lead_stats()
            assert False, "expected AgentBackendUnavailableError"
        except AgentBackendUnavailableError:
            pass


def test_get_observability_stats_returns_json_on_success():
    fake_stats = {"call_count": 3, "avg_latency_ms": 120.0, "recent_calls": []}
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = fake_stats
    fake_response.raise_for_status = Mock()
    with patch("agent_client.requests.get", return_value=fake_response) as mocked_get:
        assert get_observability_stats() == fake_stats
    assert mocked_get.call_args.args[0].endswith("/stats/observability")


def test_get_observability_stats_raises_on_connection_error():
    with patch("agent_client.requests.get", side_effect=requests.ConnectionError("boom")):
        try:
            get_observability_stats()
            assert False, "expected AgentBackendUnavailableError"
        except AgentBackendUnavailableError:
            pass
