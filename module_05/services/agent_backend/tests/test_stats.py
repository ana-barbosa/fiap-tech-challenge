from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src import stats
from src.conversation_store import ConversationState


def _iso(seconds_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()


def test_is_cold_false_when_no_shown_listings():
    state = ConversationState(conversation_id="conv-1", shown_listings={}, last_active_at=_iso(999))
    assert stats._is_cold(state) is False


def test_is_cold_false_when_recently_active(monkeypatch):
    monkeypatch.setattr(stats.config, "FOLLOWUP_INACTIVITY_SECONDS", 120)
    state = ConversationState(
        conversation_id="conv-1", shown_listings={"1": {}}, last_active_at=_iso(10)
    )
    assert stats._is_cold(state) is False


def test_is_cold_true_when_inactive_with_a_followup_candidate(monkeypatch):
    monkeypatch.setattr(stats.config, "FOLLOWUP_INACTIVITY_SECONDS", 120)
    monkeypatch.setattr(stats.followup, "find_followup_candidate", MagicMock(return_value="1"))
    state = ConversationState(
        conversation_id="conv-1", shown_listings={"1": {}}, last_active_at=_iso(999)
    )
    assert stats._is_cold(state) is True


def test_is_cold_false_when_inactive_but_no_candidate_left(monkeypatch):
    monkeypatch.setattr(stats.config, "FOLLOWUP_INACTIVITY_SECONDS", 120)
    monkeypatch.setattr(stats.followup, "find_followup_candidate", MagicMock(return_value=None))
    state = ConversationState(
        conversation_id="conv-1", shown_listings={"1": {}}, last_active_at=_iso(999)
    )
    assert stats._is_cold(state) is False


def test_lead_stats_counts_total_clients_and_intent_breakdown(monkeypatch):
    conversations = [
        ConversationState(conversation_id="c1", qualification={"intencao": "alugar"}),
        ConversationState(conversation_id="c2", qualification={"intencao": "comprar"}),
        ConversationState(conversation_id="c3", qualification={}),
    ]
    monkeypatch.setattr(stats.conversation_store, "list_all", MagicMock(return_value=conversations))

    result = stats.lead_stats()

    assert result["total_clients"] == 3
    assert result["intent_breakdown"]["alugar"] == 1
    assert result["intent_breakdown"]["comprar"] == 1
    assert result["intent_breakdown"]["investir"] == 0
    assert result["intent_breakdown"][stats.UNKNOWN_INTENT_KEY] == 1


def test_lead_stats_counts_cold_leads(monkeypatch):
    cold = ConversationState(conversation_id="cold", shown_listings={"1": {}}, last_active_at=_iso(999))
    warm = ConversationState(conversation_id="warm", shown_listings={"1": {}}, last_active_at=_iso(1))
    monkeypatch.setattr(stats.conversation_store, "list_all", MagicMock(return_value=[cold, warm]))
    monkeypatch.setattr(stats.config, "FOLLOWUP_INACTIVITY_SECONDS", 120)
    monkeypatch.setattr(stats.followup, "find_followup_candidate", MagicMock(return_value="1"))

    result = stats.lead_stats()

    assert result["cold_leads"] == 1
