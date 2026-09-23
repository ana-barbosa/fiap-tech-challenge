import pytest

from src import config


def test_require_env_raises_when_missing(monkeypatch):
    monkeypatch.delenv("SOME_MISSING_VAR", raising=False)
    with pytest.raises(RuntimeError, match="SOME_MISSING_VAR"):
        config.require_env("SOME_MISSING_VAR")


def test_require_env_raises_when_empty(monkeypatch):
    monkeypatch.setenv("EMPTY_VAR", "")
    with pytest.raises(RuntimeError, match="EMPTY_VAR"):
        config.require_env("EMPTY_VAR")


def test_require_env_returns_value(monkeypatch):
    monkeypatch.setenv("SOME_VAR", "value")
    assert config.require_env("SOME_VAR") == "value"


def test_followup_env_vars_loaded_as_ints_and_url():
    assert isinstance(config.FOLLOWUP_INACTIVITY_SECONDS, int)
    assert isinstance(config.FOLLOWUP_POLL_INTERVAL_SECONDS, int)
    assert config.TELEGRAM_BOT_INTERNAL_URL


def test_summary_env_vars_loaded_as_ints():
    assert isinstance(config.SUMMARY_IDLE_SECONDS, int)
    assert isinstance(config.SUMMARY_POLL_INTERVAL_SECONDS, int)
