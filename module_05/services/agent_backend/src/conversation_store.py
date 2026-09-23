import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

from . import config, database


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ConversationState:
    conversation_id: str
    history: list[dict] = field(default_factory=list)
    qualification: dict = field(default_factory=dict)
    current_specialist: str = "real_estate"
    shown_listings: dict = field(default_factory=dict)
    last_active_at: str = field(default_factory=_now_iso)
    channel: Literal["website", "telegram"] = "website"
    summary: str | None = None


def _is_expired(last_active_at: str) -> bool:
    last_active = datetime.fromisoformat(last_active_at)
    age = datetime.now(timezone.utc) - last_active
    return age > timedelta(days=config.CONVERSATION_RETENTION_DAYS)


def _state_from_row(row) -> ConversationState:
    return ConversationState(
        conversation_id=row["conversation_id"],
        history=json.loads(row["history_json"]),
        qualification=json.loads(row["qualification_json"]),
        current_specialist=row["current_specialist"],
        shown_listings=json.loads(row["shown_listings_json"]),
        last_active_at=row["last_active_at"],
        channel=row["channel"],
        summary=row["summary"],
    )


def get_or_create(conversation_id: str) -> ConversationState:
    with database.connection_scope() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,)
        ).fetchone()

    if row is None or _is_expired(row["last_active_at"]):
        return ConversationState(conversation_id=conversation_id)

    return _state_from_row(row)


def list_by_channel(channel: str) -> list[ConversationState]:
    with database.connection_scope() as conn:
        rows = conn.execute("SELECT * FROM conversations WHERE channel = ?", (channel,)).fetchall()

    return [_state_from_row(row) for row in rows if not _is_expired(row["last_active_at"])]


def list_all() -> list[ConversationState]:
    with database.connection_scope() as conn:
        rows = conn.execute("SELECT * FROM conversations").fetchall()

    return [_state_from_row(row) for row in rows if not _is_expired(row["last_active_at"])]


def save(state: ConversationState) -> None:
    trimmed_history = state.history[-config.CONVERSATION_HISTORY_LIMIT :]

    with database.connection_scope() as conn:
        conn.execute(
            """
            INSERT INTO conversations
                (conversation_id, history_json, qualification_json, current_specialist,
                 shown_listings_json, last_active_at, channel)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                history_json = excluded.history_json,
                qualification_json = excluded.qualification_json,
                current_specialist = excluded.current_specialist,
                shown_listings_json = excluded.shown_listings_json,
                last_active_at = excluded.last_active_at,
                channel = excluded.channel,
                summary = NULL
            """,
            (
                state.conversation_id,
                json.dumps(trimmed_history),
                json.dumps(state.qualification),
                state.current_specialist,
                json.dumps(state.shown_listings),
                _now_iso(),
                state.channel,
            ),
        )


def list_stale_summaries() -> list[ConversationState]:
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=config.SUMMARY_IDLE_SECONDS)).isoformat()
    with database.connection_scope() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE summary IS NULL AND last_active_at <= ?", (cutoff,)
        ).fetchall()

    return [_state_from_row(row) for row in rows if not _is_expired(row["last_active_at"])]


def set_summary(conversation_id: str, summary: str, expected_last_active_at: str) -> None:
    # Optimistic-concurrency guard: expected_last_active_at is the timestamp captured before
    # the LLM call ran, so if a new message arrived (and reset last_active_at/summary again)
    # while that call was in flight, this UPDATE matches zero rows and the fresher NULL is
    # correctly left alone instead of being overwritten with a stale summary.
    with database.connection_scope() as conn:
        conn.execute(
            "UPDATE conversations SET summary = ? WHERE conversation_id = ? AND last_active_at = ?",
            (summary, conversation_id, expected_last_active_at),
        )
