from unittest.mock import MagicMock

from src import summary
from src.conversation_store import ConversationState


def test_generate_summary_returns_placeholder_without_llm_call_when_no_history(monkeypatch):
    fake_get_chat_model = MagicMock()
    monkeypatch.setattr(summary, "get_chat_model", fake_get_chat_model)
    state = ConversationState(conversation_id="conv-1", history=[])

    result = summary.generate_summary(state)

    assert result == summary.NO_HISTORY_SUMMARY
    fake_get_chat_model.assert_not_called()


def test_generate_summary_calls_llm_with_transcript_and_returns_its_content(monkeypatch):
    fake_response = MagicMock(content="Cliente busca apartamento de 2 quartos em Taubaté.")
    fake_model = MagicMock()
    fake_model.invoke.return_value = fake_response
    monkeypatch.setattr(summary, "get_chat_model", lambda: fake_model)

    state = ConversationState(
        conversation_id="conv-1",
        history=[
            {"role": "user", "content": "quero alugar um apê em Taubaté"},
            {"role": "assistant", "content": "Legal! Quantos quartos você procura?"},
        ],
        qualification={"intencao": "alugar"},
        shown_listings={"34": {"city": "Taubaté", "price": 2000}},
    )

    result = summary.generate_summary(state)

    assert result == "Cliente busca apartamento de 2 quartos em Taubaté."
    messages = fake_model.invoke.call_args.args[0]
    assert messages[0]["role"] == "system"
    user_content = messages[1]["content"]
    assert "Cliente: quero alugar um apê em Taubaté" in user_content
    assert "Assistente: Legal! Quantos quartos você procura?" in user_content
    assert "Taubaté" in user_content


def test_run_once_generates_and_persists_a_summary_for_every_stale_conversation(monkeypatch):
    stale = ConversationState(
        conversation_id="conv-1",
        history=[{"role": "user", "content": "quero alugar um apê em Taubaté"}],
        last_active_at="2026-09-20T10:00:00+00:00",
    )
    monkeypatch.setattr(summary.conversation_store, "list_stale_summaries", MagicMock(return_value=[stale]))
    monkeypatch.setattr(summary, "generate_summary", MagicMock(return_value="Resumo gerado."))
    fake_set_summary = MagicMock()
    monkeypatch.setattr(summary.conversation_store, "set_summary", fake_set_summary)

    stats = summary.run_once()

    fake_set_summary.assert_called_once_with("conv-1", "Resumo gerado.", "2026-09-20T10:00:00+00:00")
    assert stats["conversations_checked"] == 1
    assert stats["summarized"] == 1


def test_run_once_does_nothing_when_no_stale_conversations(monkeypatch):
    monkeypatch.setattr(summary.conversation_store, "list_stale_summaries", MagicMock(return_value=[]))
    fake_set_summary = MagicMock()
    monkeypatch.setattr(summary.conversation_store, "set_summary", fake_set_summary)

    stats = summary.run_once()

    fake_set_summary.assert_not_called()
    assert stats["conversations_checked"] == 0
    assert stats["summarized"] == 0
