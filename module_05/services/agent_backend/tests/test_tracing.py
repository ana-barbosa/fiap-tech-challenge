from src import tracing


def _call(**overrides) -> tracing.LlmCall:
    defaults = dict(
        conversation_id="conv-1",
        specialist="real_estate",
        latency_ms=100,
        rag_sources={"buscar_imoveis": ["1", "2"]},
        prompt_redacted="quero alugar um apartamento",
        response_redacted="Claro, me conta mais.",
        input_tokens=50,
        output_tokens=20,
    )
    defaults.update(overrides)
    return tracing.LlmCall(**defaults)


def test_log_call_persists_a_row():
    tracing.log_call(_call(conversation_id="conv-log-1"))

    stats = tracing.call_stats()
    assert stats["call_count"] >= 1
    assert any(row["conversation_id"] == "conv-log-1" for row in stats["recent_calls"])


def test_call_stats_computes_average_and_p95_latency():
    conversation_id = "conv-latency"
    for latency in (100, 200, 300, 400, 500):
        tracing.log_call(_call(conversation_id=conversation_id, latency_ms=latency))

    stats = tracing.call_stats()
    matching = [row for row in stats["recent_calls"] if row["conversation_id"] == conversation_id]
    assert len(matching) == 5
    assert stats["avg_latency_ms"] > 0
    assert stats["p95_latency_ms"] >= stats["avg_latency_ms"]


def test_call_stats_computes_error_rate_and_injection_count():
    conversation_id = "conv-errors"
    tracing.log_call(_call(conversation_id=conversation_id, error="boom"))
    tracing.log_call(_call(conversation_id=conversation_id, injection_suspected=True))
    tracing.log_call(_call(conversation_id=conversation_id))

    stats = tracing.call_stats()
    matching = [row for row in stats["recent_calls"] if row["conversation_id"] == conversation_id]
    errors = [row for row in matching if row["error"] is not None]
    flagged = [row for row in matching if row["injection_suspected"]]
    assert len(errors) == 1
    assert len(flagged) == 1


def test_call_stats_sums_token_usage():
    conversation_id = "conv-tokens"
    tracing.log_call(_call(conversation_id=conversation_id, input_tokens=10, output_tokens=5))
    tracing.log_call(_call(conversation_id=conversation_id, input_tokens=20, output_tokens=8))

    stats = tracing.call_stats()
    assert stats["total_input_tokens"] >= 30
    assert stats["total_output_tokens"] >= 13
