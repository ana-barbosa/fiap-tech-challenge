import json
from unittest.mock import MagicMock

from src import tools


def test_buscar_imoveis_maps_portuguese_args_to_search_listings(monkeypatch):
    fake_search = MagicMock(return_value=[{"id": "1"}])
    monkeypatch.setattr(tools.search, "search_listings", fake_search)

    result = tools.buscar_imoveis.invoke(
        {
            "query": "apartamento",
            "cidades": ["Taubaté"],
            "tipo_imovel": "apartment",
            "tipo_anuncio": "rent",
            "preco_min": 1000.0,
            "preco_max": 2000.0,
            "quartos": 2,
        }
    )

    assert json.loads(result) == [{"id": "1"}]
    fake_search.assert_called_once_with(
        query="apartamento",
        cities=["Taubaté"],
        property_type="apartment",
        listing_type="rent",
        price_min=1000.0,
        price_max=2000.0,
        rooms=2,
    )


def test_buscar_dados_geograficos_delegates_to_search_geo(monkeypatch):
    fake_search = MagicMock(return_value=[{"city": "Ubatuba"}])
    monkeypatch.setattr(tools.search, "search_geo", fake_search)

    result = tools.buscar_dados_geograficos.invoke({"query": "cidade litorânea"})

    assert result == [{"city": "Ubatuba"}]
    fake_search.assert_called_once_with("cidade litorânea")


def test_buscar_rentabilidade_delegates_to_search_roi(monkeypatch):
    fake_search = MagicMock(return_value=[{"segment": "Taubaté|Centro|apartment"}])
    monkeypatch.setattr(tools.search, "search_roi", fake_search)

    result = tools.buscar_rentabilidade.invoke(
        {"query": "yield", "cidades": ["Taubaté"], "tipo_imovel": "apartment"}
    )

    assert result == [{"segment": "Taubaté|Centro|apartment"}]
    fake_search.assert_called_once_with("yield", cities=["Taubaté"], property_type="apartment")


def test_agendar_visita_schema_hides_injected_conversation_id_from_the_llm():
    assert set(tools.agendar_visita.args) == {"property_id", "nome_lead", "contato_lead", "data_hora_desejada"}


def test_agendar_visita_delegates_to_crm_client(monkeypatch):
    fake_book_visit = MagicMock(return_value={"status": "confirmed"})
    monkeypatch.setattr(tools.crm_client, "book_visit", fake_book_visit)

    result = tools.agendar_visita.func(
        property_id=1,
        nome_lead="Maria",
        contato_lead="maria@example.com",
        data_hora_desejada="2026-10-01T15:00:00",
        conversation_id="conv-1",
        channel="telegram",
    )

    assert result == {"status": "confirmed"}
    fake_book_visit.assert_called_once_with(
        property_id=1,
        conversation_id="conv-1",
        lead_name="Maria",
        lead_contact="maria@example.com",
        requested_datetime="2026-10-01T15:00:00",
        channel="telegram",
    )


def test_tools_registers_all_four():
    names = {t.name for t in tools.TOOLS}
    assert names == {"buscar_imoveis", "buscar_dados_geograficos", "buscar_rentabilidade", "agendar_visita"}


def test_buscar_financiamento_delegates_to_search_financing(monkeypatch):
    fake_search = MagicMock(return_value=[{"topic": "itbi"}])
    monkeypatch.setattr(tools.search, "search_financing", fake_search)

    result = tools.buscar_financiamento.invoke({"query": "quanto é o ITBI?"})

    assert result == [{"topic": "itbi"}]
    fake_search.assert_called_once_with("quanto é o ITBI?")


def test_mortgage_advisor_tools_registers_financing_tool():
    names = {t.name for t in tools.MORTGAGE_ADVISOR_TOOLS}
    assert names == {"buscar_financiamento"}
