from langchain_openai import ChatOpenAI

from src import config
from src.llm import get_chat_model


def test_get_chat_model_returns_chatopenai(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-test-fake")

    model = get_chat_model()

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "gpt-4o-mini"
    assert model.temperature == 0
