from unittest.mock import MagicMock

from src import price_drop
from src.conversation_store import ConversationState


def test_find_price_drops_detects_real_drop(monkeypatch):
    monkeypatch.setattr(price_drop.crm_client, "get_property", MagicMock(return_value={"price": 900.0}))
    state = ConversationState(conversation_id="conv-1", shown_listings={"34": {"city": "Taubaté", "price": 1000.0}})

    drops = price_drop.find_price_drops(state)

    assert drops == [("34", state.shown_listings["34"], 900.0)]


def test_find_price_drops_ignores_price_increase(monkeypatch):
    monkeypatch.setattr(price_drop.crm_client, "get_property", MagicMock(return_value={"price": 1100.0}))
    state = ConversationState(conversation_id="conv-1", shown_listings={"34": {"city": "Taubaté", "price": 1000.0}})

    assert price_drop.find_price_drops(state) == []


def test_find_price_drops_ignores_unchanged_price(monkeypatch):
    monkeypatch.setattr(price_drop.crm_client, "get_property", MagicMock(return_value={"price": 1000.0}))
    state = ConversationState(conversation_id="conv-1", shown_listings={"34": {"city": "Taubaté", "price": 1000.0}})

    assert price_drop.find_price_drops(state) == []


def test_find_price_drops_uses_last_notified_price_as_baseline(monkeypatch):
    monkeypatch.setattr(price_drop.crm_client, "get_property", MagicMock(return_value={"price": 900.0}))
    state = ConversationState(
        conversation_id="conv-1",
        shown_listings={"34": {"city": "Taubaté", "price": 1000.0, "last_notified_price": 900.0}},
    )

    assert price_drop.find_price_drops(state) == []


def test_find_price_drops_detects_further_drop_below_last_notified_price(monkeypatch):
    monkeypatch.setattr(price_drop.crm_client, "get_property", MagicMock(return_value={"price": 800.0}))
    state = ConversationState(
        conversation_id="conv-1",
        shown_listings={"34": {"city": "Taubaté", "price": 1000.0, "last_notified_price": 900.0}},
    )

    drops = price_drop.find_price_drops(state)

    assert drops == [("34", state.shown_listings["34"], 800.0)]


def test_build_message_includes_property_type_city_and_new_price():
    snapshot = {"property_type": "apartment", "city": "Taubaté", "neighborhood": "Centro"}

    message = price_drop.build_message(snapshot, 900.0)

    assert "apartment" in message
    assert "Centro" in message
    assert "Taubaté" in message
    assert "900" in message


def test_run_once_only_queries_telegram_channel(monkeypatch):
    fake_list_by_channel = MagicMock(return_value=[])
    monkeypatch.setattr(price_drop.conversation_store, "list_by_channel", fake_list_by_channel)

    price_drop.run_once()

    fake_list_by_channel.assert_called_once_with("telegram")


def test_run_once_notifies_and_stamps_last_notified_price(monkeypatch):
    state = ConversationState(conversation_id="123", shown_listings={"34": {"city": "Taubaté", "price": 1000.0}})
    monkeypatch.setattr(price_drop.conversation_store, "list_by_channel", MagicMock(return_value=[state]))
    monkeypatch.setattr(price_drop.crm_client, "get_property", MagicMock(return_value={"price": 900.0}))
    fake_push = MagicMock()
    monkeypatch.setattr(price_drop.telegram_bot_client, "push_message", fake_push)
    fake_save = MagicMock()
    monkeypatch.setattr(price_drop.conversation_store, "save", fake_save)

    stats = price_drop.run_once()

    fake_push.assert_called_once()
    assert fake_push.call_args.args[0] == "123"
    assert state.shown_listings["34"]["last_notified_price"] == 900.0
    fake_save.assert_called_once_with(state)
    assert stats["conversations_checked"] == 1
    assert stats["notified"] == 1


def test_run_once_skips_conversation_with_no_drop(monkeypatch):
    state = ConversationState(conversation_id="123", shown_listings={"34": {"city": "Taubaté", "price": 1000.0}})
    monkeypatch.setattr(price_drop.conversation_store, "list_by_channel", MagicMock(return_value=[state]))
    monkeypatch.setattr(price_drop.crm_client, "get_property", MagicMock(return_value={"price": 1000.0}))
    fake_push = MagicMock()
    monkeypatch.setattr(price_drop.telegram_bot_client, "push_message", fake_push)
    fake_save = MagicMock()
    monkeypatch.setattr(price_drop.conversation_store, "save", fake_save)

    stats = price_drop.run_once()

    fake_push.assert_not_called()
    fake_save.assert_not_called()
    assert stats["notified"] == 0
