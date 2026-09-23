import json
from datetime import date
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src import graph
from src.graph import (
    FINAL_ANSWER_TOOL,
    AgentTurn,
    State,
    entry_router,
    finalize_node,
    merge_qualification,
    merge_shown_listings,
    mortgage_advisor_node,
    real_estate_node,
    route_after_model,
    route_after_validate_visita,
    transfer_node,
    validate_visita_node,
)
from src.qualification import Intent, Qualification


def test_merge_qualification_fills_null_fields_only():
    previous = Qualification(intent=Intent.RENT, rooms=2)
    update = Qualification(price_min=1500.0, price_max=2000.0)

    merged = merge_qualification(previous, update)

    assert merged.intent == Intent.RENT
    assert merged.rooms == 2
    assert merged.price_min == 1500.0
    assert merged.price_max == 2000.0


def test_merge_qualification_overwrites_when_update_has_value():
    previous = Qualification(rooms=2)
    update = Qualification(rooms=3)

    merged = merge_qualification(previous, update)

    assert merged.rooms == 3


def test_merge_qualification_keeps_existing_when_update_is_null():
    previous = Qualification(rooms=2)
    update = Qualification(rooms=None)

    merged = merge_qualification(previous, update)

    assert merged.rooms == 2


def test_merge_shown_listings_adds_new_ids():
    previous = {"1": {"city": "Taubaté"}}
    update = {"2": {"city": "Ubatuba"}}

    merged = merge_shown_listings(previous, update)

    assert merged == {"1": {"city": "Taubaté"}, "2": {"city": "Ubatuba"}}


def test_merge_shown_listings_keeps_existing_snapshot_for_same_id():
    previous = {"1": {"city": "Taubaté", "price": 2000}}
    update = {"1": {"city": "Taubaté", "price": 9999}}

    merged = merge_shown_listings(previous, update)

    assert merged == {"1": {"city": "Taubaté", "price": 2000}}


def test_real_estate_node_binds_search_tools_and_agent_turn_and_forces_a_call(monkeypatch):
    fake_response = AIMessage(
        content="",
        tool_calls=[{"name": FINAL_ANSWER_TOOL, "args": {}, "id": "call_1"}],
    )
    fake_bound_model = MagicMock()
    fake_bound_model.invoke.return_value = fake_response
    fake_model = MagicMock()
    fake_model.bind_tools.return_value = fake_bound_model

    monkeypatch.setattr(graph, "get_chat_model", lambda: fake_model)

    state: State = {
        "messages": [HumanMessage(content="quero alugar um apartamento")],
        "qualification": Qualification(),
    }

    result = real_estate_node(state)

    assert result["messages"][0] is fake_response
    bound_tools = fake_model.bind_tools.call_args.args[0]
    tool_names = {getattr(t, "name", getattr(t, "__name__", None)) for t in bound_tools}
    assert tool_names == {
        "buscar_imoveis",
        "buscar_dados_geograficos",
        "buscar_rentabilidade",
        "agendar_visita",
        "AgentTurn",
        "TransferToMortgageAdvisor",
    }
    assert fake_model.bind_tools.call_args.kwargs["tool_choice"] == "required"
    assert fake_model.bind_tools.call_args.kwargs["parallel_tool_calls"] is False


def test_real_estate_node_logs_agendar_visita_non_pii_args(monkeypatch, caplog):
    fake_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "agendar_visita",
                "args": {
                    "property_id": 1,
                    "nome_lead": "Maria",
                    "contato_lead": "maria@example.com",
                    "data_hora_desejada": "2026-10-01T15:00:00",
                },
                "id": "call_1",
            }
        ],
    )
    fake_bound_model = MagicMock()
    fake_bound_model.invoke.return_value = fake_response
    fake_model = MagicMock()
    fake_model.bind_tools.return_value = fake_bound_model
    monkeypatch.setattr(graph, "get_chat_model", lambda: fake_model)

    state: State = {"messages": [HumanMessage(content="pode agendar?")], "qualification": Qualification()}

    with caplog.at_level("INFO"):
        real_estate_node(state)

    logged = "\n".join(caplog.messages)
    assert "property_id=1" in logged
    assert "data_hora_desejada=2026-10-01T15:00:00" in logged
    assert "Maria" not in logged
    assert "maria@example.com" not in logged


def test_specialist_node_context_includes_todays_date_for_relative_date_calculations(monkeypatch):
    fake_response = AIMessage(content="", tool_calls=[{"name": FINAL_ANSWER_TOOL, "args": {}, "id": "call_1"}])
    fake_bound_model = MagicMock()
    fake_bound_model.invoke.return_value = fake_response
    fake_model = MagicMock()
    fake_model.bind_tools.return_value = fake_bound_model
    monkeypatch.setattr(graph, "get_chat_model", lambda: fake_model)

    class _FixedDate:
        @staticmethod
        def today():
            return date(2026, 9, 19)

    monkeypatch.setattr(graph, "date", _FixedDate)

    state: State = {"messages": [HumanMessage(content="oi")], "qualification": Qualification()}
    real_estate_node(state)

    context_message = fake_bound_model.invoke.call_args.args[0][1]
    assert "2026-09-19" in context_message["content"]


def test_specialist_node_forces_finalize_after_enough_tool_results(monkeypatch):
    fake_response = AIMessage(content="", tool_calls=[{"name": FINAL_ANSWER_TOOL, "args": {}, "id": "call_1"}])
    fake_bound_model = MagicMock()
    fake_bound_model.invoke.return_value = fake_response
    fake_model = MagicMock()
    fake_model.bind_tools.return_value = fake_bound_model
    monkeypatch.setattr(graph, "get_chat_model", lambda: fake_model)

    messages: list = [HumanMessage(content="tem apartamento em Campos do Jordão?")]
    for i in range(3):
        messages.append(AIMessage(content="", tool_calls=[{"name": "buscar_imoveis", "args": {}, "id": f"call_{i}"}]))
        messages.append(ToolMessage(content="[]", tool_call_id=f"call_{i}"))
    state: State = {"messages": messages, "qualification": Qualification()}

    real_estate_node(state)

    context_message = fake_bound_model.invoke.call_args.args[0][1]
    assert "Não chame mais" in context_message["content"]


def test_specialist_node_does_not_force_finalize_before_threshold(monkeypatch):
    fake_response = AIMessage(content="", tool_calls=[{"name": FINAL_ANSWER_TOOL, "args": {}, "id": "call_1"}])
    fake_bound_model = MagicMock()
    fake_bound_model.invoke.return_value = fake_response
    fake_model = MagicMock()
    fake_model.bind_tools.return_value = fake_bound_model
    monkeypatch.setattr(graph, "get_chat_model", lambda: fake_model)

    state: State = {
        "messages": [
            HumanMessage(content="tem apartamento em Campos do Jordão?"),
            ToolMessage(content="[]", tool_call_id="call_1"),
        ],
        "qualification": Qualification(),
    }

    real_estate_node(state)

    context_message = fake_bound_model.invoke.call_args.args[0][1]
    assert "Não chame mais" not in context_message["content"]


def test_mortgage_advisor_node_binds_financing_tool_and_transfer_back(monkeypatch):
    fake_response = AIMessage(
        content="",
        tool_calls=[{"name": FINAL_ANSWER_TOOL, "args": {}, "id": "call_1"}],
    )
    fake_bound_model = MagicMock()
    fake_bound_model.invoke.return_value = fake_response
    fake_model = MagicMock()
    fake_model.bind_tools.return_value = fake_bound_model

    monkeypatch.setattr(graph, "get_chat_model", lambda: fake_model)

    state: State = {
        "messages": [HumanMessage(content="quanto é o ITBI?")],
        "qualification": Qualification(),
        "current_specialist": "mortgage_advisor",
    }

    result = mortgage_advisor_node(state)

    assert result["messages"][0] is fake_response
    bound_tools = fake_model.bind_tools.call_args.args[0]
    tool_names = {getattr(t, "name", getattr(t, "__name__", None)) for t in bound_tools}
    assert tool_names == {"buscar_financiamento", "AgentTurn", "TransferToRealEstate"}


def test_route_after_model_goes_to_finalize_when_agent_turn_called():
    state: State = {
        "messages": [
            AIMessage(content="", tool_calls=[{"name": FINAL_ANSWER_TOOL, "args": {}, "id": "1"}])
        ],
        "qualification": Qualification(),
    }

    assert route_after_model(state) == "finalize"


def test_route_after_model_goes_to_tools_when_search_tool_called():
    state: State = {
        "messages": [
            AIMessage(content="", tool_calls=[{"name": "buscar_imoveis", "args": {}, "id": "1"}])
        ],
        "qualification": Qualification(),
    }

    assert route_after_model(state) == "tools"


def test_route_after_model_goes_to_transfer_when_transfer_tool_called():
    state: State = {
        "messages": [
            AIMessage(content="", tool_calls=[{"name": "TransferToMortgageAdvisor", "args": {}, "id": "1"}])
        ],
        "qualification": Qualification(),
    }

    assert route_after_model(state) == "transfer"


def test_route_after_model_goes_to_validate_visita_when_agendar_visita_called():
    state: State = {
        "messages": [
            AIMessage(content="", tool_calls=[{"name": "agendar_visita", "args": {}, "id": "1"}])
        ],
        "qualification": Qualification(),
    }

    assert route_after_model(state) == "validate_visita"


def test_entry_router_defaults_to_real_estate_when_missing():
    state: State = {"messages": [], "qualification": Qualification()}
    assert entry_router(state) == "real_estate"


def test_entry_router_honors_current_specialist():
    state: State = {"messages": [], "qualification": Qualification(), "current_specialist": "mortgage_advisor"}
    assert entry_router(state) == "mortgage_advisor"


def test_transfer_node_acknowledges_call_and_flips_specialist():
    state: State = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "TransferToMortgageAdvisor", "args": {"motivo": "pergunta de ITBI"}, "id": "call_1"}],
            )
        ],
        "qualification": Qualification(),
        "current_specialist": "real_estate",
    }

    result = transfer_node(state)

    assert result["current_specialist"] == "mortgage_advisor"
    tool_message = result["messages"][0]
    assert isinstance(tool_message, ToolMessage)
    assert tool_message.tool_call_id == "call_1"
    assert tool_message.content == graph.TRANSFER_NOTICES["mortgage_advisor"]


def test_validate_visita_node_passes_through_when_property_id_was_shown():
    human = HumanMessage(content="Meu nome é Maria, meu e-mail é maria@x.com")
    pending = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "agendar_visita",
                "args": {"property_id": 34, "nome_lead": "Maria", "contato_lead": "maria@x.com", "data_hora_desejada": "2026-10-01T15:00:00"},
                "id": "call_1",
            }
        ],
    )
    state: State = {
        "messages": [human, pending],
        "qualification": Qualification(),
        "shown_listings": {"34": {"city": "Taubaté"}},
    }

    result = validate_visita_node(state)

    assert result == {}


def test_validate_visita_node_rejects_unknown_property_id():
    pending = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "agendar_visita",
                "args": {"property_id": 999, "nome_lead": "Maria", "contato_lead": "maria@x.com", "data_hora_desejada": "2026-10-01T15:00:00"},
                "id": "call_1",
            }
        ],
    )
    state: State = {"messages": [pending], "qualification": Qualification(), "shown_listings": {"34": {}}}

    result = validate_visita_node(state)

    rejection = result["messages"][0]
    assert isinstance(rejection, ToolMessage)
    assert rejection.tool_call_id == "call_1"
    assert json.loads(rejection.content) == {"status": "error", "detail": graph.PROPERTY_NOT_SHOWN_ERROR}


def test_validate_visita_node_rejects_blank_nome_lead():
    pending = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "agendar_visita",
                "args": {"property_id": 34, "nome_lead": "   ", "contato_lead": "maria@x.com", "data_hora_desejada": "2026-10-01T15:00:00"},
                "id": "call_1",
            }
        ],
    )
    state: State = {
        "messages": [pending],
        "qualification": Qualification(),
        "shown_listings": {"34": {"city": "Taubaté"}},
    }

    result = validate_visita_node(state)

    rejection = result["messages"][0]
    assert isinstance(rejection, ToolMessage)
    assert json.loads(rejection.content) == {"status": "error", "detail": graph.MISSING_LEAD_INFO_ERROR}


def test_validate_visita_node_rejects_missing_contato_lead():
    pending = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "agendar_visita",
                "args": {"property_id": 34, "nome_lead": "Maria", "data_hora_desejada": "2026-10-01T15:00:00"},
                "id": "call_1",
            }
        ],
    )
    state: State = {
        "messages": [pending],
        "qualification": Qualification(),
        "shown_listings": {"34": {"city": "Taubaté"}},
    }

    result = validate_visita_node(state)

    rejection = result["messages"][0]
    assert json.loads(rejection.content) == {"status": "error", "detail": graph.MISSING_LEAD_INFO_ERROR}


def test_validate_visita_node_rejects_placeholder_lead_info_never_stated_by_the_client():
    pending = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "agendar_visita",
                "args": {
                    "property_id": 34,
                    "nome_lead": "Cliente",
                    "contato_lead": "contato@cliente.com",
                    "data_hora_desejada": "2026-10-01T15:00:00",
                },
                "id": "call_1",
            }
        ],
    )
    state: State = {
        "messages": [HumanMessage(content="quero agendar uma visita"), pending],
        "qualification": Qualification(),
        "shown_listings": {"34": {"city": "Taubaté"}},
    }

    result = validate_visita_node(state)

    rejection = result["messages"][0]
    assert json.loads(rejection.content) == {"status": "error", "detail": graph.MISSING_LEAD_INFO_ERROR}


def test_validate_visita_node_accepts_phone_shaped_contact_regardless_of_formatting():
    human = HumanMessage(content="Sou a Maria, meu telefone é 12 99876 5432")
    pending = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "agendar_visita",
                "args": {
                    "property_id": 34,
                    "nome_lead": "Maria",
                    "contato_lead": "(12) 99876-5432",
                    "data_hora_desejada": "2026-10-01T15:00:00",
                },
                "id": "call_1",
            }
        ],
    )
    state: State = {
        "messages": [human, pending],
        "qualification": Qualification(),
        "shown_listings": {"34": {"city": "Taubaté"}},
    }

    assert validate_visita_node(state) == {}


def test_validate_visita_node_rejects_when_shown_listings_missing_entirely():
    pending = AIMessage(
        content="",
        tool_calls=[{"name": "agendar_visita", "args": {"property_id": 1}, "id": "call_1"}],
    )
    state: State = {"messages": [pending], "qualification": Qualification()}

    result = validate_visita_node(state)

    assert result["messages"][0].tool_call_id == "call_1"


def test_route_after_validate_visita_proceeds_to_tools_when_call_untouched():
    pending = AIMessage(
        content="", tool_calls=[{"name": "agendar_visita", "args": {"property_id": 1}, "id": "call_1"}]
    )
    state: State = {"messages": [pending], "qualification": Qualification()}

    assert route_after_validate_visita(state) == "tools"


def test_route_after_validate_visita_returns_to_real_estate_when_rejected():
    rejection = ToolMessage(content="{}", tool_call_id="call_1")
    state: State = {"messages": [rejection], "qualification": Qualification()}

    assert route_after_validate_visita(state) == "real_estate"


def test_finalize_node_extracts_reply_and_qualification_and_reuses_message_id():
    pending = AIMessage(
        content="",
        id="pending-id",
        tool_calls=[
            {
                "name": FINAL_ANSWER_TOOL,
                "args": {
                    "resposta": "Oi! Me conta mais sobre o que você procura.",
                    "qualificacao": {"intencao": "alugar"},
                },
                "id": "call_1",
            }
        ],
    )
    state: State = {"messages": [pending], "qualification": Qualification()}

    result = finalize_node(state)

    final_message = result["messages"][0]
    assert isinstance(final_message, AIMessage)
    assert final_message.id == "pending-id"
    assert final_message.tool_calls == []
    assert final_message.content == "Oi! Me conta mais sobre o que você procura."
    assert result["qualification"].intent == Intent.RENT
    assert result["shown_listings"] == {}


def test_finalize_node_preserves_usage_metadata_for_observability_tracing():
    pending = AIMessage(
        content="",
        id="pending-id",
        tool_calls=[
            {
                "name": FINAL_ANSWER_TOOL,
                "args": {"resposta": "Oi!", "qualificacao": {}},
                "id": "call_1",
            }
        ],
        usage_metadata={"input_tokens": 120, "output_tokens": 30, "total_tokens": 150},
    )
    state: State = {"messages": [pending], "qualification": Qualification()}

    result = finalize_node(state)

    final_message = result["messages"][0]
    assert final_message.usage_metadata == {"input_tokens": 120, "output_tokens": 30, "total_tokens": 150}


def test_finalize_node_extracts_shown_listings_from_this_turns_buscar_imoveis_calls():
    search_call = AIMessage(
        content="",
        tool_calls=[{"name": "buscar_imoveis", "args": {"query": "casa de praia"}, "id": "call_1"}],
    )
    search_result = ToolMessage(
        content=json.dumps([{"id": "34", "city": "Ubatuba", "price": 650000}]),
        tool_call_id="call_1",
    )
    pending = AIMessage(
        content="",
        id="pending-id",
        tool_calls=[
            {"name": FINAL_ANSWER_TOOL, "args": {"resposta": "Achei uma casa!", "qualificacao": {}}, "id": "call_2"}
        ],
    )
    state: State = {
        "messages": [search_call, search_result, pending],
        "qualification": Qualification(),
        "shown_listings": {},
    }

    result = finalize_node(state)

    assert result["shown_listings"] == {"34": {"id": "34", "city": "Ubatuba", "price": 650000}}


def test_finalize_node_prepends_handoff_notice_when_transfer_happened_this_turn():
    transfer_ack = ToolMessage(content=graph.TRANSFER_NOTICES["mortgage_advisor"], tool_call_id="call_1")
    pending = AIMessage(
        content="",
        id="pending-id",
        tool_calls=[
            {"name": FINAL_ANSWER_TOOL, "args": {"resposta": "O ITBI fica entre 2% e 3%.", "qualificacao": {}}, "id": "call_2"}
        ],
    )
    state: State = {"messages": [transfer_ack, pending], "qualification": Qualification()}

    result = finalize_node(state)

    assert result["messages"][0].content == (
        "🏦 Você agora está falando com nossa especialista em financiamento.\n\nO ITBI fica entre 2% e 3%."
    )


def test_finalize_node_no_notice_when_no_transfer_this_turn():
    pending = AIMessage(
        content="",
        id="pending-id",
        tool_calls=[
            {"name": FINAL_ANSWER_TOOL, "args": {"resposta": "2 quartos, entendido.", "qualificacao": {}}, "id": "call_1"}
        ],
    )
    state: State = {"messages": [pending], "qualification": Qualification()}

    result = finalize_node(state)

    assert result["messages"][0].content == "2 quartos, entendido."


def test_finalize_node_appends_listing_links_for_this_turns_buscar_imoveis_results(monkeypatch):
    monkeypatch.setattr(graph.config, "WEBSITE_PUBLIC_URL", "http://website.test")
    search_call = AIMessage(
        content="",
        tool_calls=[{"name": "buscar_imoveis", "args": {"query": "casa de praia"}, "id": "call_1"}],
    )
    search_result = ToolMessage(
        content=json.dumps([{"id": "34", "city": "Ubatuba", "neighborhood": "Praia Grande", "price": 650000}]),
        tool_call_id="call_1",
    )
    pending = AIMessage(
        content="",
        id="pending-id",
        tool_calls=[
            {"name": FINAL_ANSWER_TOOL, "args": {"resposta": "Achei uma casa!", "qualificacao": {}}, "id": "call_2"}
        ],
    )
    state: State = {
        "messages": [search_call, search_result, pending],
        "qualification": Qualification(),
        "shown_listings": {},
    }

    result = finalize_node(state)

    assert result["messages"][0].content == (
        "Achei uma casa!\n\n🔗 [Praia Grande](http://website.test/Detalhes_do_Im%C3%B3vel?listing_id=34)"
    )


def test_finalize_node_listing_link_url_has_no_raw_non_ascii_characters():
    search_call = AIMessage(
        content="",
        tool_calls=[{"name": "buscar_imoveis", "args": {"query": "casa de praia"}, "id": "call_1"}],
    )
    search_result = ToolMessage(
        content=json.dumps([{"id": "34", "city": "Ubatuba", "neighborhood": "Praia Grande", "price": 650000}]),
        tool_call_id="call_1",
    )
    pending = AIMessage(
        content="",
        id="pending-id",
        tool_calls=[
            {"name": FINAL_ANSWER_TOOL, "args": {"resposta": "Achei uma casa!", "qualificacao": {}}, "id": "call_2"}
        ],
    )
    state: State = {
        "messages": [search_call, search_result, pending],
        "qualification": Qualification(),
        "shown_listings": {},
    }

    result = finalize_node(state)

    url = result["messages"][0].content.split("(")[1].split(")")[0]
    assert url.isascii()


def test_finalize_node_no_links_block_when_no_listings_shown_this_turn():
    pending = AIMessage(
        content="",
        id="pending-id",
        tool_calls=[
            {"name": FINAL_ANSWER_TOOL, "args": {"resposta": "2 quartos, entendido.", "qualificacao": {}}, "id": "call_1"}
        ],
    )
    state: State = {"messages": [pending], "qualification": Qualification()}

    result = finalize_node(state)

    assert result["messages"][0].content == "2 quartos, entendido."


def test_build_graph_compiles():
    compiled = graph.build_graph()
    assert compiled is not None


def test_build_graph_runs_full_tool_loop_then_finalizes(monkeypatch):
    search_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "buscar_imoveis",
                "args": {"query": "casa de praia", "cidades": ["Ubatuba"]},
                "id": "call_1",
            }
        ],
    )
    final_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": FINAL_ANSWER_TOOL,
                "args": {
                    "resposta": "Achei uma casa de praia em Ubatuba para você!",
                    "qualificacao": {"intencao": "comprar"},
                },
                "id": "call_2",
            }
        ],
    )
    fake_bound_model = MagicMock()
    fake_bound_model.invoke.side_effect = [search_call, final_call]
    fake_model = MagicMock()
    fake_model.bind_tools.return_value = fake_bound_model

    monkeypatch.setattr(graph, "get_chat_model", lambda: fake_model)

    compiled = graph.build_graph()
    result = compiled.invoke(
        {
            "messages": [HumanMessage(content="quero uma casa de praia em Ubatuba")],
            "qualification": Qualification(),
        }
    )

    assert fake_bound_model.invoke.call_count == 2
    assert result["qualification"].intent == Intent.BUY
    last_message = result["messages"][-1]
    assert last_message.content.startswith("Achei uma casa de praia em Ubatuba para você!\n\n🔗 ")
    assert last_message.tool_calls == []


def test_build_graph_hands_off_mid_turn_to_mortgage_advisor(monkeypatch):
    transfer_call = AIMessage(
        content="",
        tool_calls=[
            {"name": "TransferToMortgageAdvisor", "args": {"motivo": "pergunta sobre ITBI"}, "id": "call_1"}
        ],
    )
    final_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": FINAL_ANSWER_TOOL,
                "args": {
                    "resposta": "O ITBI geralmente fica entre 2% e 3%.",
                    "qualificacao": {},
                },
                "id": "call_2",
            }
        ],
    )
    fake_bound_model = MagicMock()
    fake_bound_model.invoke.side_effect = [transfer_call, final_call]
    fake_model = MagicMock()
    fake_model.bind_tools.return_value = fake_bound_model

    monkeypatch.setattr(graph, "get_chat_model", lambda: fake_model)

    compiled = graph.build_graph()
    result = compiled.invoke(
        {
            "messages": [HumanMessage(content="quanto é o ITBI?")],
            "qualification": Qualification(),
            "current_specialist": "real_estate",
        }
    )

    assert fake_bound_model.invoke.call_count == 2
    assert result["current_specialist"] == "mortgage_advisor"
    last_message = result["messages"][-1]
    assert last_message.content == "🏦 Você agora está falando com nossa especialista em financiamento.\n\nO ITBI geralmente fica entre 2% e 3%."
    assert last_message.tool_calls == []


def test_build_graph_hands_off_mid_turn_back_to_real_estate(monkeypatch):
    transfer_call = AIMessage(
        content="",
        tool_calls=[{"name": "TransferToRealEstate", "args": {"motivo": "quer ver imóveis"}, "id": "call_1"}],
    )
    final_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": FINAL_ANSWER_TOOL,
                "args": {
                    "resposta": "Me conta mais sobre o que procura.",
                    "qualificacao": {},
                },
                "id": "call_2",
            }
        ],
    )
    fake_bound_model = MagicMock()
    fake_bound_model.invoke.side_effect = [transfer_call, final_call]
    fake_model = MagicMock()
    fake_model.bind_tools.return_value = fake_bound_model

    monkeypatch.setattr(graph, "get_chat_model", lambda: fake_model)

    compiled = graph.build_graph()
    result = compiled.invoke(
        {
            "messages": [HumanMessage(content="na verdade quero ver imóveis")],
            "qualification": Qualification(),
            "current_specialist": "mortgage_advisor",
        }
    )

    assert fake_bound_model.invoke.call_count == 2
    assert result["current_specialist"] == "real_estate"
    last_message = result["messages"][-1]
    assert last_message.content == "🏠 Voltando a falar com nossa assistente de imóveis.\n\nMe conta mais sobre o que procura."


def test_shown_listings_survive_handoff_and_let_agendar_visita_succeed_without_a_fresh_search(monkeypatch):
    fake_bound_model = MagicMock()
    fake_model = MagicMock()
    fake_model.bind_tools.return_value = fake_bound_model
    monkeypatch.setattr(graph, "get_chat_model", lambda: fake_model)
    fake_book_visit = MagicMock(return_value={"status": "confirmed", "property_id": 2})
    monkeypatch.setattr(graph.tools.crm_client, "book_visit", fake_book_visit)

    compiled = graph.build_graph()

    fake_bound_model.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[{"name": "buscar_imoveis", "args": {"query": "casa de praia", "cidades": ["Ubatuba"]}, "id": "call_1"}],
        ),
        AIMessage(
            content="",
            tool_calls=[{"name": FINAL_ANSWER_TOOL, "args": {"resposta": "Achei uma casa em Ubatuba!", "qualificacao": {}}, "id": "call_2"}],
        ),
    ]
    turn1 = compiled.invoke(
        {
            "messages": [HumanMessage(content="quero uma casa de praia em Ubatuba")],
            "qualification": Qualification(),
            "current_specialist": "real_estate",
            "shown_listings": {},
            "conversation_id": "conv-1",
            "channel": "telegram",
        }
    )
    assert turn1["shown_listings"], "expected buscar_imoveis' real result to populate shown_listings"
    property_id = next(iter(turn1["shown_listings"]))

    fake_bound_model.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[{"name": "TransferToMortgageAdvisor", "args": {"motivo": "pergunta de financiamento"}, "id": "call_3"}],
        ),
        AIMessage(
            content="",
            tool_calls=[{"name": FINAL_ANSWER_TOOL, "args": {"resposta": "O ITBI fica entre 2% e 3%.", "qualificacao": {}}, "id": "call_4"}],
        ),
    ]
    turn2 = compiled.invoke(
        {
            "messages": [HumanMessage(content="quanto é o ITBI?")],
            "qualification": turn1["qualification"],
            "current_specialist": turn1["current_specialist"],
            "shown_listings": turn1["shown_listings"],
            "conversation_id": "conv-1",
            "channel": "telegram",
        }
    )
    assert turn2["current_specialist"] == "mortgage_advisor"
    assert turn2["shown_listings"] == turn1["shown_listings"]

    fake_bound_model.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[{"name": "TransferToRealEstate", "args": {"motivo": "quer agendar visita"}, "id": "call_5"}],
        ),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "agendar_visita",
                    "args": {
                        "property_id": int(property_id),
                        "nome_lead": "Maria",
                        "contato_lead": "maria@example.com",
                        "data_hora_desejada": "2026-10-01T15:00:00",
                    },
                    "id": "call_6",
                }
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[{"name": FINAL_ANSWER_TOOL, "args": {"resposta": "Visita agendada!", "qualificacao": {}}, "id": "call_7"}],
        ),
    ]
    turn3 = compiled.invoke(
        {
            "messages": [
                HumanMessage(
                    content="quero agendar uma visita na casa que vimos, meu nome é Maria e meu e-mail é maria@example.com"
                )
            ],
            "qualification": turn2["qualification"],
            "current_specialist": turn2["current_specialist"],
            "shown_listings": turn2["shown_listings"],
            "conversation_id": "conv-1",
            "channel": "telegram",
        }
    )

    assert turn3["current_specialist"] == "real_estate"
    fake_book_visit.assert_called_once_with(
        property_id=int(property_id),
        conversation_id="conv-1",
        lead_name="Maria",
        lead_contact="maria@example.com",
        requested_datetime="2026-10-01T15:00:00",
        channel="telegram",
    )
    assert turn3["messages"][-1].content.endswith("Visita agendada!")


def test_agendar_visita_rejected_end_to_end_when_property_id_was_never_shown(monkeypatch):
    fake_bound_model = MagicMock()
    fake_model = MagicMock()
    fake_model.bind_tools.return_value = fake_bound_model
    monkeypatch.setattr(graph, "get_chat_model", lambda: fake_model)
    fake_book_visit = MagicMock()
    monkeypatch.setattr(graph.tools.crm_client, "book_visit", fake_book_visit)

    fake_bound_model.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "agendar_visita",
                    "args": {
                        "property_id": 999,
                        "nome_lead": "Maria",
                        "contato_lead": "maria@example.com",
                        "data_hora_desejada": "2026-10-01T15:00:00",
                    },
                    "id": "call_1",
                }
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[{"name": FINAL_ANSWER_TOOL, "args": {"resposta": "Qual imóvel você quer visitar?", "qualificacao": {}}, "id": "call_2"}],
        ),
    ]

    compiled = graph.build_graph()
    result = compiled.invoke(
        {
            "messages": [HumanMessage(content="quero agendar uma visita no imóvel 999")],
            "qualification": Qualification(),
            "current_specialist": "real_estate",
            "shown_listings": {},
        }
    )

    fake_book_visit.assert_not_called()
    assert result["messages"][-1].content == "Qual imóvel você quer visitar?"
