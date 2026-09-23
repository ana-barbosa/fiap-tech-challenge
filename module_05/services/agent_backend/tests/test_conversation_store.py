import uuid
from datetime import datetime, timedelta, timezone

from src import conversation_store
from src.conversation_store import ConversationState


def _new_id() -> str:
    return str(uuid.uuid4())


def test_get_or_create_returns_fresh_state_for_unseen_conversation_id():
    state = conversation_store.get_or_create(_new_id())

    assert state.history == []
    assert state.qualification == {}
    assert state.current_specialist == "real_estate"
    assert state.shown_listings == {}
    assert state.channel == "website"
    assert state.summary is None


def test_save_then_get_or_create_round_trips_all_fields():
    conversation_id = _new_id()
    state = ConversationState(
        conversation_id=conversation_id,
        history=[{"role": "user", "content": "quero alugar um apê em Taubaté"}],
        qualification={"intencao": "alugar", "quartos": 2},
        current_specialist="mortgage_advisor",
        shown_listings={"34": {"city": "Taubaté", "price": 2000}},
        channel="telegram",
    )

    conversation_store.save(state)
    reloaded = conversation_store.get_or_create(conversation_id)

    assert reloaded.history == state.history
    assert reloaded.qualification == state.qualification
    assert reloaded.current_specialist == "mortgage_advisor"
    assert reloaded.shown_listings == {"34": {"city": "Taubaté", "price": 2000}}
    assert reloaded.channel == "telegram"


def test_save_upserts_existing_conversation_id():
    conversation_id = _new_id()
    conversation_store.save(ConversationState(conversation_id=conversation_id, current_specialist="real_estate"))
    conversation_store.save(ConversationState(conversation_id=conversation_id, current_specialist="mortgage_advisor"))

    reloaded = conversation_store.get_or_create(conversation_id)

    assert reloaded.current_specialist == "mortgage_advisor"


def test_save_trims_history_beyond_configured_limit(monkeypatch):
    monkeypatch.setattr(conversation_store.config, "CONVERSATION_HISTORY_LIMIT", 2)
    conversation_id = _new_id()
    history = [{"role": "user", "content": f"mensagem {i}"} for i in range(5)]

    conversation_store.save(ConversationState(conversation_id=conversation_id, history=history))
    reloaded = conversation_store.get_or_create(conversation_id)

    assert reloaded.history == history[-2:]


def test_get_or_create_treats_expired_conversation_as_new(monkeypatch):
    monkeypatch.setattr(conversation_store.config, "CONVERSATION_RETENTION_DAYS", 60)
    conversation_id = _new_id()
    stale_timestamp = (datetime.now(timezone.utc) - timedelta(days=61)).isoformat()
    conversation_store.save(
        ConversationState(
            conversation_id=conversation_id,
            history=[{"role": "user", "content": "mensagem antiga"}],
            qualification={"intencao": "comprar"},
        )
    )
    with conversation_store.database.connection_scope() as conn:
        conn.execute(
            "UPDATE conversations SET last_active_at = ? WHERE conversation_id = ?",
            (stale_timestamp, conversation_id),
        )

    reloaded = conversation_store.get_or_create(conversation_id)

    assert reloaded.history == []
    assert reloaded.qualification == {}


def test_get_or_create_resumes_conversation_within_retention_window(monkeypatch):
    monkeypatch.setattr(conversation_store.config, "CONVERSATION_RETENTION_DAYS", 60)
    conversation_id = _new_id()
    recent_timestamp = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    conversation_store.save(
        ConversationState(conversation_id=conversation_id, qualification={"intencao": "comprar"})
    )
    with conversation_store.database.connection_scope() as conn:
        conn.execute(
            "UPDATE conversations SET last_active_at = ? WHERE conversation_id = ?",
            (recent_timestamp, conversation_id),
        )

    reloaded = conversation_store.get_or_create(conversation_id)

    assert reloaded.qualification == {"intencao": "comprar"}


def test_list_by_channel_returns_only_matching_channel():
    telegram_id = _new_id()
    website_id = _new_id()
    conversation_store.save(ConversationState(conversation_id=telegram_id, channel="telegram"))
    conversation_store.save(ConversationState(conversation_id=website_id, channel="website"))

    result = conversation_store.list_by_channel("telegram")

    assert telegram_id in {state.conversation_id for state in result}
    assert website_id not in {state.conversation_id for state in result}


def test_list_all_returns_conversations_across_channels():
    telegram_id = _new_id()
    website_id = _new_id()
    conversation_store.save(ConversationState(conversation_id=telegram_id, channel="telegram"))
    conversation_store.save(ConversationState(conversation_id=website_id, channel="website"))

    result = {state.conversation_id for state in conversation_store.list_all()}

    assert telegram_id in result
    assert website_id in result


def test_list_all_excludes_expired_conversations(monkeypatch):
    monkeypatch.setattr(conversation_store.config, "CONVERSATION_RETENTION_DAYS", 60)
    conversation_id = _new_id()
    conversation_store.save(ConversationState(conversation_id=conversation_id))
    stale_timestamp = (datetime.now(timezone.utc) - timedelta(days=61)).isoformat()
    with conversation_store.database.connection_scope() as conn:
        conn.execute(
            "UPDATE conversations SET last_active_at = ? WHERE conversation_id = ?",
            (stale_timestamp, conversation_id),
        )

    result = conversation_store.list_all()

    assert conversation_id not in {state.conversation_id for state in result}


def test_list_by_channel_excludes_expired_conversations(monkeypatch):
    monkeypatch.setattr(conversation_store.config, "CONVERSATION_RETENTION_DAYS", 60)
    conversation_id = _new_id()
    conversation_store.save(ConversationState(conversation_id=conversation_id, channel="telegram"))
    stale_timestamp = (datetime.now(timezone.utc) - timedelta(days=61)).isoformat()
    with conversation_store.database.connection_scope() as conn:
        conn.execute(
            "UPDATE conversations SET last_active_at = ? WHERE conversation_id = ?",
            (stale_timestamp, conversation_id),
        )

    result = conversation_store.list_by_channel("telegram")

    assert conversation_id not in {state.conversation_id for state in result}


def test_save_always_resets_summary_to_null():
    conversation_id = _new_id()
    conversation_store.save(ConversationState(conversation_id=conversation_id))
    with conversation_store.database.connection_scope() as conn:
        conn.execute(
            "UPDATE conversations SET summary = ? WHERE conversation_id = ?",
            ("Resumo antigo.", conversation_id),
        )
    assert conversation_store.get_or_create(conversation_id).summary == "Resumo antigo."

    conversation_store.save(ConversationState(conversation_id=conversation_id))

    assert conversation_store.get_or_create(conversation_id).summary is None


def test_list_stale_summaries_requires_null_summary_and_enough_idle_time(monkeypatch):
    monkeypatch.setattr(conversation_store.config, "SUMMARY_IDLE_SECONDS", 60)
    idle_id = _new_id()
    active_id = _new_id()
    already_summarized_id = _new_id()
    for conversation_id in (idle_id, active_id, already_summarized_id):
        conversation_store.save(ConversationState(conversation_id=conversation_id))

    idle_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    recent_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    with conversation_store.database.connection_scope() as conn:
        conn.execute(
            "UPDATE conversations SET last_active_at = ? WHERE conversation_id = ?",
            (idle_timestamp, idle_id),
        )
        conn.execute(
            "UPDATE conversations SET last_active_at = ? WHERE conversation_id = ?",
            (recent_timestamp, active_id),
        )
        conn.execute(
            "UPDATE conversations SET last_active_at = ?, summary = ? WHERE conversation_id = ?",
            (idle_timestamp, "Já resumido.", already_summarized_id),
        )

    result = {state.conversation_id for state in conversation_store.list_stale_summaries()}

    assert idle_id in result
    assert active_id not in result
    assert already_summarized_id not in result


def test_list_stale_summaries_excludes_expired_conversations(monkeypatch):
    monkeypatch.setattr(conversation_store.config, "SUMMARY_IDLE_SECONDS", 60)
    monkeypatch.setattr(conversation_store.config, "CONVERSATION_RETENTION_DAYS", 60)
    conversation_id = _new_id()
    conversation_store.save(ConversationState(conversation_id=conversation_id))
    stale_timestamp = (datetime.now(timezone.utc) - timedelta(days=61)).isoformat()
    with conversation_store.database.connection_scope() as conn:
        conn.execute(
            "UPDATE conversations SET last_active_at = ? WHERE conversation_id = ?",
            (stale_timestamp, conversation_id),
        )

    result = conversation_store.list_stale_summaries()

    assert conversation_id not in {state.conversation_id for state in result}


def test_set_summary_writes_when_last_active_at_still_matches():
    conversation_id = _new_id()
    conversation_store.save(ConversationState(conversation_id=conversation_id))
    state = conversation_store.get_or_create(conversation_id)

    conversation_store.set_summary(conversation_id, "Cliente busca apê em Taubaté.", state.last_active_at)

    assert conversation_store.get_or_create(conversation_id).summary == "Cliente busca apê em Taubaté."


def test_set_summary_is_a_noop_when_last_active_at_changed_in_the_meantime():
    conversation_id = _new_id()
    conversation_store.save(ConversationState(conversation_id=conversation_id))
    stale_last_active_at = conversation_store.get_or_create(conversation_id).last_active_at

    conversation_store.save(ConversationState(conversation_id=conversation_id))

    conversation_store.set_summary(conversation_id, "Resumo desatualizado.", stale_last_active_at)

    assert conversation_store.get_or_create(conversation_id).summary is None
