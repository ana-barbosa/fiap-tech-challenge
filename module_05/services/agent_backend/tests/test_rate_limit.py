from src import config, rate_limit


def test_allows_requests_within_the_limit(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_MAX_REQUESTS", 3)
    monkeypatch.setattr(config, "RATE_LIMIT_WINDOW_SECONDS", 60)
    conversation_id = "conv-within-limit"

    assert rate_limit.check(conversation_id)
    assert rate_limit.check(conversation_id)
    assert rate_limit.check(conversation_id)


def test_blocks_requests_once_limit_is_exceeded(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_MAX_REQUESTS", 2)
    monkeypatch.setattr(config, "RATE_LIMIT_WINDOW_SECONDS", 60)
    conversation_id = "conv-over-limit"

    assert rate_limit.check(conversation_id)
    assert rate_limit.check(conversation_id)
    assert not rate_limit.check(conversation_id)


def test_different_conversations_have_independent_limits(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr(config, "RATE_LIMIT_WINDOW_SECONDS", 60)

    assert rate_limit.check("conv-a")
    assert rate_limit.check("conv-b")
    assert not rate_limit.check("conv-a")


def test_old_requests_fall_out_of_the_window(monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr(config, "RATE_LIMIT_WINDOW_SECONDS", 60)
    conversation_id = "conv-sliding-window"

    assert rate_limit.check(conversation_id)
    assert not rate_limit.check(conversation_id)

    rate_limit._calls[conversation_id][0] -= 61
    assert rate_limit.check(conversation_id)
