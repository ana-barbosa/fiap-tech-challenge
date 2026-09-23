import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import database

RECENT_CALLS_LIMIT = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LlmCall:
    conversation_id: str
    specialist: str
    latency_ms: int
    rag_sources: dict = field(default_factory=dict)
    prompt_redacted: str = ""
    response_redacted: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None
    injection_suspected: bool = False


def log_call(call: LlmCall) -> None:
    with database.connection_scope() as conn:
        conn.execute(
            """
            INSERT INTO llm_calls
                (conversation_id, specialist, created_at, latency_ms, input_tokens,
                 output_tokens, rag_sources_json, prompt_redacted, response_redacted, error,
                 injection_suspected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                call.conversation_id,
                call.specialist,
                _now_iso(),
                call.latency_ms,
                call.input_tokens,
                call.output_tokens,
                json.dumps(call.rag_sources),
                call.prompt_redacted,
                call.response_redacted,
                call.error,
                int(call.injection_suspected),
            ),
        )


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, int(round(pct * (len(sorted_values) - 1))))
    return sorted_values[index]


def call_stats() -> dict:
    with database.connection_scope() as conn:
        rows = conn.execute("SELECT * FROM llm_calls ORDER BY id DESC").fetchall()

    call_count = len(rows)
    latencies = sorted(row["latency_ms"] for row in rows)
    errors = [row for row in rows if row["error"] is not None]
    injection_flagged = [row for row in rows if row["injection_suspected"]]
    total_input_tokens = sum(row["input_tokens"] or 0 for row in rows)
    total_output_tokens = sum(row["output_tokens"] or 0 for row in rows)

    return {
        "call_count": call_count,
        "avg_latency_ms": (sum(latencies) / call_count) if call_count else 0.0,
        "p95_latency_ms": _percentile(latencies, 0.95),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "error_rate": (len(errors) / call_count) if call_count else 0.0,
        "injection_suspected_count": len(injection_flagged),
        "recent_calls": [
            {
                "conversation_id": row["conversation_id"],
                "specialist": row["specialist"],
                "created_at": row["created_at"],
                "latency_ms": row["latency_ms"],
                "input_tokens": row["input_tokens"],
                "output_tokens": row["output_tokens"],
                "error": row["error"],
                "injection_suspected": bool(row["injection_suspected"]),
            }
            for row in rows[:RECENT_CALLS_LIMIT]
        ],
    }
