import json
import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel

from . import (
    chroma_store,
    config,
    conversation_store,
    followup,
    injection_guard,
    price_drop,
    rate_limit,
    redact,
    speech,
    stats,
    summary,
    tracing,
)
from .graph import build_graph
from .qualification import Qualification

# Without this, src.* module loggers have no handler in their chain and are silently
# dropped - uvicorn only configures its own uvicorn.* loggers, not the root logger.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class _HealthCheckLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_HealthCheckLogFilter())

_followup_state: dict = {"status": "starting", "last_run_at": None, "last_error": None}
_price_drop_state: dict = {"status": "starting", "last_run_at": None, "last_error": None}
_summary_state: dict = {"status": "starting", "last_run_at": None, "last_error": None}


def _followup_loop() -> None:
    while True:
        try:
            cycle_stats = followup.run_once()
            _followup_state.update(cycle_stats)
            _followup_state["status"] = "ok"
            _followup_state["last_error"] = None
            logger.info("Follow-up cycle complete: %s", cycle_stats)
        except Exception as exc:
            _followup_state["status"] = "error"
            _followup_state["last_error"] = str(exc)
            logger.exception("Follow-up cycle failed")

        try:
            price_drop_stats = price_drop.run_once()
            _price_drop_state.update(price_drop_stats)
            _price_drop_state["status"] = "ok"
            _price_drop_state["last_error"] = None
            logger.info("Price drop cycle complete: %s", price_drop_stats)
        except Exception as exc:
            _price_drop_state["status"] = "error"
            _price_drop_state["last_error"] = str(exc)
            logger.exception("Price drop cycle failed")

        time.sleep(config.FOLLOWUP_POLL_INTERVAL_SECONDS)


def _summary_loop() -> None:
    while True:
        try:
            cycle_stats = summary.run_once()
            _summary_state.update(cycle_stats)
            _summary_state["status"] = "ok"
            _summary_state["last_error"] = None
            logger.info("Summary cycle complete: %s", cycle_stats)
        except Exception as exc:
            _summary_state["status"] = "error"
            _summary_state["last_error"] = str(exc)
            logger.exception("Summary cycle failed")
        time.sleep(config.SUMMARY_POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    chroma_store.warm_up()
    threading.Thread(target=_followup_loop, daemon=True).start()
    threading.Thread(target=_summary_loop, daemon=True).start()
    yield


app = FastAPI(title="Agente Imobiliário - Vale do Paraíba", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


_graph = build_graph()

STILL_INDEXING_REPLY = "Ainda estou carregando os dados dos imóveis - tente novamente em instantes."
STUCK_REPLY = "Não consegui encontrar uma resposta agora - pode tentar reformular sua pergunta?"
SUMMARY_PENDING = "Resumo ainda sendo gerado - tente novamente em instantes."

GRAPH_RECURSION_LIMIT = 15

RAG_TOOL_ID_FIELDS = {
    "buscar_imoveis": "id",
    "buscar_dados_geograficos": "city",
    "buscar_rentabilidade": "segment",
    "buscar_financiamento": "topic",
}


def _extract_rag_sources(new_messages: list) -> dict:
    call_names = {
        call["id"]: call["name"]
        for message in new_messages
        if isinstance(message, AIMessage)
        for call in message.tool_calls
        if call["name"] in RAG_TOOL_ID_FIELDS
    }
    sources: dict[str, list] = {}
    for message in new_messages:
        if isinstance(message, ToolMessage) and message.tool_call_id in call_names:
            tool_name = call_names[message.tool_call_id]
            id_field = RAG_TOOL_ID_FIELDS[tool_name]
            try:
                items = json.loads(message.content)
            except (json.JSONDecodeError, TypeError):
                continue
            ids = [item.get(id_field) for item in items if isinstance(item, dict)]
            sources.setdefault(tool_name, []).extend(ids)
    return sources


def _extract_token_usage(new_messages: list) -> tuple[int, int]:
    input_tokens = output_tokens = 0
    for message in new_messages:
        usage = isinstance(message, AIMessage) and message.usage_metadata
        if usage:
            input_tokens += usage.get("input_tokens") or 0
            output_tokens += usage.get("output_tokens") or 0
    return input_tokens, output_tokens


def _known_pii_this_turn(new_messages: list) -> list[str]:
    # Feeds tracing's redact.redact(known_pii=...) so exact lead-provided values get scrubbed,
    # on top of redact.py's generic email/phone patterns.
    values = []
    for message in new_messages:
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                if call["name"] == "agendar_visita":
                    values.extend(v for v in (call["args"].get("nome_lead"), call["args"].get("contato_lead")) if v)
    return values


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    channel: str = "website"


class ChatResponse(BaseModel):
    reply: str
    qualification: dict
    specialist: str


class SummaryResponse(BaseModel):
    summary: str


class TranscribeResponse(BaseModel):
    text: str


class LeadStatsResponse(BaseModel):
    total_clients: int
    intent_breakdown: dict[str, int]
    cold_leads: int


class ObservabilityStatsResponse(BaseModel):
    call_count: int
    avg_latency_ms: float
    p95_latency_ms: float
    total_input_tokens: int
    total_output_tokens: int
    error_rate: float
    injection_suspected_count: int
    recent_calls: list[dict]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/conversations/{conversation_id}/summary", response_model=SummaryResponse)
def conversation_summary(conversation_id: str) -> SummaryResponse:
    state = conversation_store.get_or_create(conversation_id)
    return SummaryResponse(summary=state.summary or SUMMARY_PENDING)


@app.get("/stats/leads", response_model=LeadStatsResponse)
def stats_leads() -> LeadStatsResponse:
    return LeadStatsResponse(**stats.lead_stats())


@app.get("/stats/observability", response_model=ObservabilityStatsResponse)
def stats_observability() -> ObservabilityStatsResponse:
    return ObservabilityStatsResponse(**tracing.call_stats())


@app.post("/chat", response_model=ChatResponse)
def chat(data: ChatRequest) -> ChatResponse:
    # Conversation state is looked up server-side by conversation_id and persisted again
    # after the turn - the caller only ever sends the new message text. Only human/assistant
    # dialogue turns and shown_listings cross this persistence boundary; the tool-calling
    # scaffolding within a turn lives and dies inside one _graph.invoke() call.
    logger.info("Chat request received for conversation_id=%s", data.conversation_id)

    if not rate_limit.check(data.conversation_id):
        raise HTTPException(status_code=429, detail="Muitas mensagens em pouco tempo - aguarde um momento.")

    state = conversation_store.get_or_create(data.conversation_id)

    if not chroma_store.is_ready():
        logger.warning("Chat request received before Chroma is populated - nothing to ground answers in yet")
        return ChatResponse(reply=STILL_INDEXING_REPLY, qualification=state.qualification, specialist=state.current_specialist)

    lc_messages = [
        HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"])
        for m in state.history
    ]
    lc_messages.append(HumanMessage(content=data.message))
    qualification = Qualification(**state.qualification)

    injection_pattern = injection_guard.looks_suspicious(data.message)
    if injection_pattern:
        logger.warning(
            "Possible prompt injection detected: conversation_id=%s pattern=%s", data.conversation_id, injection_pattern
        )

    turn_started_at = time.monotonic()
    try:
        result = _graph.invoke(
            {
                "messages": lc_messages,
                "qualification": qualification,
                "current_specialist": state.current_specialist,
                "shown_listings": state.shown_listings,
                "conversation_id": data.conversation_id,
                "channel": data.channel,
            },
            config={"recursion_limit": GRAPH_RECURSION_LIMIT},
        )
    except GraphRecursionError:
        logger.warning("Graph exceeded recursion limit without finalizing - returning fallback reply")
        tracing.log_call(
            tracing.LlmCall(
                conversation_id=data.conversation_id,
                specialist=state.current_specialist,
                latency_ms=int((time.monotonic() - turn_started_at) * 1000),
                prompt_redacted=redact.redact(data.message),
                error="graph_recursion_limit_exceeded",
                injection_suspected=bool(injection_pattern),
            )
        )
        return ChatResponse(reply=STUCK_REPLY, qualification=state.qualification, specialist=state.current_specialist)
    except Exception as exc:
        tracing.log_call(
            tracing.LlmCall(
                conversation_id=data.conversation_id,
                specialist=state.current_specialist,
                latency_ms=int((time.monotonic() - turn_started_at) * 1000),
                prompt_redacted=redact.redact(data.message),
                error=str(exc),
                injection_suspected=bool(injection_pattern),
            )
        )
        raise

    latency_ms = int((time.monotonic() - turn_started_at) * 1000)
    new_messages = result["messages"][len(lc_messages) :]

    reply = result["messages"][-1].content
    qualification_dict = result["qualification"].model_dump(by_alias=True, exclude_none=True)
    specialist = result["current_specialist"]

    known_pii = _known_pii_this_turn(new_messages)
    input_tokens, output_tokens = _extract_token_usage(new_messages)
    tracing.log_call(
        tracing.LlmCall(
            conversation_id=data.conversation_id,
            specialist=specialist,
            latency_ms=latency_ms,
            rag_sources=_extract_rag_sources(new_messages),
            prompt_redacted=redact.redact(data.message, known_pii),
            response_redacted=redact.redact(reply, known_pii),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            injection_suspected=bool(injection_pattern),
        )
    )

    state.history.append({"role": "user", "content": data.message})
    state.history.append({"role": "assistant", "content": reply})
    state.qualification = qualification_dict
    state.current_specialist = specialist
    state.shown_listings = result["shown_listings"]
    state.channel = data.channel
    conversation_store.save(state)

    logger.info("Chat reply produced")

    return ChatResponse(reply=reply, qualification=qualification_dict, specialist=specialist)


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)) -> TranscribeResponse:
    # A standalone, conversation-agnostic utility - callers decide whether/when to use it and
    # what to do with the result (e.g. whether an empty transcription is worth forwarding to
    # /chat at all). agent_backend has no concept of "voice" as a channel-level feature.
    try:
        text = speech.transcribe(audio.filename, await audio.read())
    except speech.SpeechError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return TranscribeResponse(text=text)
