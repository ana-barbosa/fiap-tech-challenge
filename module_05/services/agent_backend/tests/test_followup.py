from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from src import followup
from src.conversation_store import ConversationState


def _iso(seconds_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()


def test_find_eligible_conversations_filters_by_inactivity_threshold(monkeypatch):
    monkeypatch.setattr(followup.config, "FOLLOWUP_INACTIVITY_SECONDS", 120)
    stale = ConversationState(conversation_id="stale", last_active_at=_iso(200))
    fresh = ConversationState(conversation_id="fresh", last_active_at=_iso(10))
    monkeypatch.setattr(followup.conversation_store, "list_by_channel", MagicMock(return_value=[stale, fresh]))

    result = followup.find_eligible_conversations()

    assert result == [stale]


def test_find_eligible_conversations_only_queries_telegram_channel(monkeypatch):
    fake_list_by_channel = MagicMock(return_value=[])
    monkeypatch.setattr(followup.conversation_store, "list_by_channel", fake_list_by_channel)

    followup.find_eligible_conversations()

    fake_list_by_channel.assert_called_once_with("telegram")


def test_find_followup_candidate_returns_none_when_no_shown_listings(monkeypatch):
    monkeypatch.setattr(followup.crm_client, "get_confirmed_visit_property_ids", MagicMock(return_value=set()))
    state = ConversationState(conversation_id="conv-1", shown_listings={})

    assert followup.find_followup_candidate(state) is None


def test_find_followup_candidate_excludes_booked_property(monkeypatch):
    monkeypatch.setattr(followup.crm_client, "get_confirmed_visit_property_ids", MagicMock(return_value={"34"}))
    state = ConversationState(conversation_id="conv-1", shown_listings={"34": {"city": "Taubaté"}})

    assert followup.find_followup_candidate(state) is None


def test_find_followup_candidate_excludes_already_followed_up_property(monkeypatch):
    monkeypatch.setattr(followup.crm_client, "get_confirmed_visit_property_ids", MagicMock(return_value=set()))
    state = ConversationState(
        conversation_id="conv-1",
        shown_listings={"34": {"city": "Taubaté", "followed_up_at": "2026-09-01T00:00:00+00:00"}},
    )

    assert followup.find_followup_candidate(state) is None


def test_find_followup_candidate_returns_most_recently_shown_eligible_property(monkeypatch):
    monkeypatch.setattr(followup.crm_client, "get_confirmed_visit_property_ids", MagicMock(return_value=set()))
    state = ConversationState(
        conversation_id="conv-1",
        shown_listings={"1": {"city": "Taubaté"}, "2": {"city": "Ubatuba"}},
    )

    assert followup.find_followup_candidate(state) == "2"


def test_build_message_includes_property_type_city_and_price():
    snapshot = {"property_type": "apartment", "city": "Taubaté", "neighborhood": "Centro", "price": 2000.0}

    message = followup.build_message(snapshot)

    assert "apartment" in message
    assert "Centro" in message
    assert "Taubaté" in message
    assert "2.000" in message or "2000" in message


def test_build_message_handles_missing_optional_fields():
    message = followup.build_message({})

    assert "imóvel" in message


def test_run_once_nudges_eligible_conversation_and_stamps_followed_up_at(monkeypatch):
    state = ConversationState(
        conversation_id="123",
        shown_listings={"34": {"city": "Taubaté", "property_type": "apartment"}},
    )
    monkeypatch.setattr(followup, "find_eligible_conversations", MagicMock(return_value=[state]))
    monkeypatch.setattr(followup.crm_client, "get_confirmed_visit_property_ids", MagicMock(return_value=set()))
    fake_push = MagicMock()
    monkeypatch.setattr(followup.telegram_bot_client, "push_message", fake_push)
    fake_save = MagicMock()
    monkeypatch.setattr(followup.conversation_store, "save", fake_save)

    stats = followup.run_once()

    fake_push.assert_called_once()
    assert fake_push.call_args.args[0] == "123"
    assert "followed_up_at" in state.shown_listings["34"]
    fake_save.assert_called_once_with(state)
    assert stats["conversations_checked"] == 1
    assert stats["nudged"] == 1


def test_run_once_skips_conversation_with_no_candidate(monkeypatch):
    state = ConversationState(conversation_id="123", shown_listings={})
    monkeypatch.setattr(followup, "find_eligible_conversations", MagicMock(return_value=[state]))
    monkeypatch.setattr(followup.crm_client, "get_confirmed_visit_property_ids", MagicMock(return_value=set()))
    fake_push = MagicMock()
    monkeypatch.setattr(followup.telegram_bot_client, "push_message", fake_push)
    fake_save = MagicMock()
    monkeypatch.setattr(followup.conversation_store, "save", fake_save)

    stats = followup.run_once()

    fake_push.assert_not_called()
    fake_save.assert_not_called()
    assert stats["nudged"] == 0
