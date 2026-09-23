import json
import logging
import re
from datetime import date
from typing import Annotated, Literal, TypedDict
from urllib.parse import quote

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, ConfigDict, Field

from . import config, prompts, tools
from .llm import get_chat_model
from .qualification import Qualification

logger = logging.getLogger(__name__)

FINAL_ANSWER_TOOL = "AgentTurn"

TOOL_RESULT_FINALIZE_THRESHOLD = 3

Specialist = Literal["real_estate", "mortgage_advisor"]

TRANSFER_TOOLS = {
    "TransferToMortgageAdvisor": "mortgage_advisor",
    "TransferToRealEstate": "real_estate",
}

# ToolMessage content acknowledging a transfer call, satisfying OpenAI's requirement that a
# tool_calls message be immediately followed by a matching tool response.
TRANSFER_NOTICES = {
    "mortgage_advisor": "Conversa transferida para o especialista de financiamento.",
    "real_estate": "Conversa transferida de volta para a assistente de imóveis.",
}

HANDOFF_NOTICES = {
    "mortgage_advisor": "🏦 Você agora está falando com nossa especialista em financiamento.",
    "real_estate": "🏠 Voltando a falar com nossa assistente de imóveis.",
}

PROPERTY_NOT_SHOWN_ERROR = (
    "Não encontrei esse imóvel nas opções já mostradas nesta conversa - qual delas você quer visitar?"
)

MISSING_LEAD_INFO_ERROR = (
    "Para agendar a visita, preciso do seu nome e de um contato (telefone ou e-mail) - pode me informar?"
)

def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value)


def _stated_by_client(value: str, state: "State") -> bool:
    # Phone numbers are compared digit-only so formatting differences (spaces, parentheses,
    # country code) don't cause a false rejection; everything else is a substring check.
    client_text = " ".join(m.content for m in state["messages"] if isinstance(m, HumanMessage) and isinstance(m.content, str))
    value_digits = _digits_only(value)
    if len(value_digits) >= 8:
        return value_digits in _digits_only(client_text)
    return value.lower() in client_text.lower()


class AgentTurn(BaseModel):
    """
    Bound to the model as a tool alongside the search/action tools (see tools.TOOLS) -
    calling it is how the model commits to a final reply for the turn, producing the
    reply and any newly-mentioned qualification fields together in one shot rather than
    a separate extraction call.

    Field names stay in English; `alias=` gives each field a Portuguese name in
    the schema handed to the LLM, matching Qualification's own aliasing (see
    that class's docstring for why).
    """

    model_config = ConfigDict(populate_by_name=True)

    reply: str = Field(
        alias="resposta",
        description=(
            "Mensagem em linguagem natural para responder ao cliente, em português. Nunca inclua "
            "JSON ou nomes de campos aqui - só o texto da conversa."
        ),
    )
    qualification: Qualification = Field(
        alias="qualificacao",
        description=(
            "Apenas os campos de qualificação mencionados ou esclarecidos na última mensagem do "
            "cliente. Deixe um campo vazio se não foi mencionado nesta mensagem - os campos já "
            "conhecidos são mantidos automaticamente, não precisa repeti-los."
        ),
    )


class TransferToMortgageAdvisor(BaseModel):
    """Chamada quando o cliente faz uma pergunta específica sobre financiamento (taxas,
    parcelamento, ITBI, escritura, condomínio/IPTU, elegibilidade) que deve ser respondida
    pelo especialista de financiamento em vez da assistente de imóveis."""

    model_config = ConfigDict(populate_by_name=True)

    reason: str = Field(alias="motivo", description="Breve motivo da transferência, para registro interno.")


class TransferToRealEstate(BaseModel):
    """Chamada quando a conversa volta a ser sobre escolha de imóvel, cidade/região ou
    investimento - fora do escopo do especialista de financiamento."""

    model_config = ConfigDict(populate_by_name=True)

    reason: str = Field(alias="motivo", description="Breve motivo da transferência, para registro interno.")


def merge_qualification(previous: Qualification, update: Qualification) -> Qualification:
    merged = previous.model_dump()
    for field, value in update.model_dump().items():
        if value is not None:
            merged[field] = value
    return Qualification(**merged)


def merge_shown_listings(previous: dict, update: dict) -> dict:
    merged = dict(previous)
    for property_id, snapshot in update.items():
        merged.setdefault(property_id, snapshot)
    return merged


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    qualification: Annotated[Qualification, merge_qualification]
    current_specialist: Annotated[Specialist, lambda _previous, update: update]
    shown_listings: Annotated[dict, merge_shown_listings]
    conversation_id: str
    channel: str


def _specialist_node(
    state: State, system_prompt: str, base_tools: list, transfer_tool: type[BaseModel], log_label: str
) -> dict:
    # tool_choice="required" + parallel_tool_calls=False guarantees exactly one tool call
    # per response, which route_after_model and finalize_node rely on when indexing
    # tool_calls[0]/tool_calls[-1] without checking length. Once TOOL_RESULT_FINALIZE_THRESHOLD
    # is reached, tool_choice is narrowed to force AgentTurn specifically - a text nudge alone
    # isn't reliable, models will keep re-calling a search tool on an unsatisfying result.
    tool_results_this_turn = sum(1 for m in state["messages"] if isinstance(m, ToolMessage))
    force_finalize = tool_results_this_turn >= TOOL_RESULT_FINALIZE_THRESHOLD
    tool_choice = FINAL_ANSWER_TOOL if force_finalize else "required"
    model = get_chat_model().bind_tools(
        [*base_tools, AgentTurn, transfer_tool], tool_choice=tool_choice, parallel_tool_calls=False
    )
    known_so_far = state["qualification"].model_dump_json(exclude_none=True)
    context_content = (
        f"Data de hoje: {date.today().isoformat()}. Use esta data como referência real para "
        "calcular qualquer data relativa mencionada pelo cliente (ex: amanhã, semana que vem) "
        "antes de chamar agendar_visita - nunca assuma outra data de hoje.\n"
        f"Informações já coletadas nesta conversa (não pergunte de novo o que já está aqui): {known_so_far}"
    )

    if force_finalize:
        context_content += (
            "\nVocê já reuniu resultados de busca suficientes nesta resposta. Não chame mais "
            "nenhuma ferramenta de busca agora - use AgentTurn para responder ao cliente com o "
            "que você já obteve, mesmo que não seja um resultado perfeito."
        )

    context_message = {"role": "system", "content": context_content}

    response: AIMessage = model.invoke(
        [
            {"role": "system", "content": system_prompt},
            context_message,
            *state["messages"],
        ]
    )

    # Tool name(s) only, never full arguments - those may carry lead-provided PII.
    logger.info("%s node called: %s", log_label, [call["name"] for call in response.tool_calls])
    for call in response.tool_calls:
        if call["name"] == "agendar_visita":
            args = call.get("args", {})
            logger.info(
                "agendar_visita called with property_id=%s data_hora_desejada=%s",
                args.get("property_id"),
                args.get("data_hora_desejada"),
            )

    return {"messages": [response]}


def real_estate_node(state: State) -> dict:
    return _specialist_node(
        state, prompts.REAL_ESTATE_AGENT_SYSTEM_PROMPT, tools.TOOLS, TransferToMortgageAdvisor, "real_estate"
    )


def mortgage_advisor_node(state: State) -> dict:
    return _specialist_node(
        state,
        prompts.MORTGAGE_ADVISOR_SYSTEM_PROMPT,
        tools.MORTGAGE_ADVISOR_TOOLS,
        TransferToRealEstate,
        "mortgage_advisor",
    )


def route_after_model(state: State) -> str:
    call_name = state["messages"][-1].tool_calls[0]["name"]
    if call_name == FINAL_ANSWER_TOOL:
        return "finalize"
    if call_name in TRANSFER_TOOLS:
        return "transfer"
    if call_name == "agendar_visita":
        return "validate_visita"
    return "tools"


def entry_router(state: State) -> str:
    return state.get("current_specialist", "real_estate")


def transfer_node(state: State) -> dict:
    # The ToolMessage reply is required: OpenAI rejects a replayed history where an assistant
    # tool_calls message isn't immediately followed by a matching tool response.
    call = state["messages"][-1].tool_calls[0]
    target = TRANSFER_TOOLS[call["name"]]

    logger.info("Transfer requested: -> %s", target)

    tool_message = ToolMessage(content=TRANSFER_NOTICES[target], tool_call_id=call["id"])
    return {"messages": [tool_message], "current_specialist": target}


def validate_visita_node(state: State) -> dict:
    call = state["messages"][-1].tool_calls[0]
    args = call["args"]
    property_id = str(args.get("property_id"))

    if property_id not in state.get("shown_listings", {}):
        logger.info("agendar_visita rejected: property_id=%s not in this conversation's shown_listings", property_id)
        rejection = ToolMessage(
            content=json.dumps({"status": "error", "detail": PROPERTY_NOT_SHOWN_ERROR}),
            tool_call_id=call["id"],
        )
        return {"messages": [rejection]}

    nome_lead = (args.get("nome_lead") or "").strip()
    contato_lead = (args.get("contato_lead") or "").strip()
    if (
        not nome_lead
        or not contato_lead
        or not _stated_by_client(nome_lead, state)
        or not _stated_by_client(contato_lead, state)
    ):
        logger.info("agendar_visita rejected: nome_lead/contato_lead missing, blank, or not found in the client's own messages")
        rejection = ToolMessage(
            content=json.dumps({"status": "error", "detail": MISSING_LEAD_INFO_ERROR}),
            tool_call_id=call["id"],
        )
        return {"messages": [rejection]}

    return {}


def route_after_validate_visita(state: State) -> str:
    # validate_visita_node leaves the AIMessage tool call untouched when the property_id
    # checks out; a rejection appends a ToolMessage in its place instead.
    return "tools" if isinstance(state["messages"][-1], AIMessage) else "real_estate"


def _shown_listings_from_this_turn(state: State) -> dict:
    # buscar_imoveis (tools.py) returns a JSON string precisely so it can be loaded back here.
    buscar_imoveis_call_ids = {
        call["id"]
        for message in state["messages"]
        if isinstance(message, AIMessage)
        for call in message.tool_calls
        if call["name"] == "buscar_imoveis"
    }
    shown = {}
    for message in state["messages"]:
        if isinstance(message, ToolMessage) and message.tool_call_id in buscar_imoveis_call_ids:
            for listing in json.loads(message.content):
                shown[str(listing["id"])] = listing
    return shown


def _handoff_notice_this_turn(state: State) -> str | None:
    # Only human/assistant turns ever cross main.py's HTTP boundary, so every ToolMessage in
    # state["messages"] was added during this graph.invoke() call, never replayed from an
    # earlier turn - finding one here reliably means the transfer happened this turn.
    for message in state["messages"]:
        if isinstance(message, ToolMessage):
            for target, notice in TRANSFER_NOTICES.items():
                if message.content == notice:
                    return HANDOFF_NOTICES[target]
    return None


DETALHES_DO_IMOVEL_PATH = quote("Detalhes_do_Imóvel")


def _listing_links_block(shown_this_turn: dict) -> str | None:
    if not shown_this_turn:
        return None
    links = [
        f"[{listing.get('neighborhood') or listing.get('city') or 'ver imóvel'}]"
        f"({config.WEBSITE_PUBLIC_URL}/{DETALHES_DO_IMOVEL_PATH}?listing_id={quote(str(property_id))})"
        for property_id, listing in shown_this_turn.items()
    ]
    return "🔗 " + " · ".join(links)


def finalize_node(state: State) -> dict:
    last = state["messages"][-1]
    call = next(c for c in last.tool_calls if c["name"] == FINAL_ANSWER_TOOL)
    turn = AgentTurn(**call["args"])

    reply = turn.reply
    handoff_notice = _handoff_notice_this_turn(state)
    if handoff_notice:
        reply = f"{handoff_notice}\n\n{reply}"

    shown_this_turn = _shown_listings_from_this_turn(state)
    links_block = _listing_links_block(shown_this_turn)
    if links_block:
        reply = f"{reply}\n\n{links_block}"

    # Reusing `last.id` makes add_messages *replace* the pending tool-call message instead of
    # appending after it - required since AgentTurn's call is never itself answered by a real
    # ToolMessage, which OpenAI would otherwise reject on replay. usage_metadata is carried
    # over from `last` so it isn't silently lost - main.py's tracing needs it.
    final_message = AIMessage(content=reply, id=last.id, usage_metadata=last.usage_metadata)

    logger.info(
        "%s turn finalized: qualification fields known so far=%s",
        state.get("current_specialist", "real_estate"),
        list(turn.qualification.model_dump(exclude_none=True).keys()),
    )

    return {
        "messages": [final_message],
        "qualification": turn.qualification,
        "shown_listings": shown_this_turn,
    }


def build_graph():
    graph = StateGraph(State)
    graph.add_node("real_estate", real_estate_node)
    graph.add_node("mortgage_advisor", mortgage_advisor_node)
    graph.add_node("tools_real_estate", ToolNode(tools.TOOLS))
    graph.add_node("tools_mortgage", ToolNode(tools.MORTGAGE_ADVISOR_TOOLS))
    graph.add_node("transfer", transfer_node)
    graph.add_node("validate_visita", validate_visita_node)
    graph.add_node("finalize", finalize_node)

    entry_targets = {"real_estate": "real_estate", "mortgage_advisor": "mortgage_advisor"}
    graph.add_conditional_edges(START, entry_router, entry_targets)
    graph.add_conditional_edges("transfer", entry_router, entry_targets)

    graph.add_conditional_edges(
        "real_estate",
        route_after_model,
        {
            "finalize": "finalize",
            "transfer": "transfer",
            "tools": "tools_real_estate",
            "validate_visita": "validate_visita",
        },
    )
    graph.add_conditional_edges(
        "mortgage_advisor",
        route_after_model,
        {"finalize": "finalize", "transfer": "transfer", "tools": "tools_mortgage"},
    )
    graph.add_conditional_edges(
        "validate_visita", route_after_validate_visita, {"tools": "tools_real_estate", "real_estate": "real_estate"}
    )
    graph.add_edge("tools_real_estate", "real_estate")
    graph.add_edge("tools_mortgage", "mortgage_advisor")
    graph.add_edge("finalize", END)
    return graph.compile()
