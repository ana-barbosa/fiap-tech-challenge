import json
from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from . import crm_client, search


@tool
def buscar_imoveis(
    query: str,
    cidades: list[str] | None = None,
    tipo_imovel: str | None = None,
    tipo_anuncio: str | None = None,
    preco_min: float | None = None,
    preco_max: float | None = None,
    quartos: int | None = None,
) -> str:
    """Busca semântica nos imóveis disponíveis (dados reais), com filtros estruturados
    opcionais. Só preencha um filtro (cidades, tipo_imovel, preco_min/max, quartos) com um
    valor que o cliente já informou explicitamente - nunca chame esta ferramenta de novo só
    para tentar valores diferentes de um filtro que o cliente não informou (ex: testar
    quartos=1, depois 2, depois 3): se quiser refinar por um dado que falta, pergunte ao
    cliente em vez de adivinhar. tipo_anuncio deve ser exatamente "sale" (venda) ou "rent"
    (aluguel) - nunca a intenção do cliente em português. quartos é um mínimo (ex: quartos=2
    retorna imóveis com 2 ou mais quartos), não uma busca exata. Use antes de citar qualquer imóvel
    real ao cliente. Retorna uma lista JSON de imóveis com seus ids reais - reutilize esses
    ids ao chamar agendar_visita depois, nunca invente um."""
    results = search.search_listings(
        query=query,
        cities=cidades,
        property_type=tipo_imovel,
        listing_type=tipo_anuncio,
        price_min=preco_min,
        price_max=preco_max,
        rooms=quartos,
    )
    # json.dumps (not LangChain's default str()/repr()) keeps this ToolMessage's content
    # valid JSON, since graph.py's shown_listings bookkeeping calls json.loads() on it.
    return json.dumps(results)


@tool
def buscar_dados_geograficos(query: str) -> list[dict]:
    """Busca semântica em dados geográficos reais das cidades do Vale do Paraíba
    (população, clima, elevação, transporte). Use quando o cliente descrever
    características de uma cidade em vez de nomear uma, antes de sugerir candidatas."""
    return search.search_geo(query)


@tool
def buscar_rentabilidade(
    query: str, cidades: list[str] | None = None, tipo_imovel: str | None = None
) -> list[dict]:
    """Busca segmentos de rentabilidade (yield bruto anual) calculados a partir dos
    imóveis reais, por cidade/bairro/tipo de imóvel. Use para responder perguntas de
    retorno esperado em conversas de investimento."""
    return search.search_roi(query, cities=cidades, property_type=tipo_imovel)


@tool
def agendar_visita(
    property_id: int,
    nome_lead: str,
    contato_lead: str,
    data_hora_desejada: str,
    conversation_id: Annotated[str, InjectedState("conversation_id")],
    channel: Annotated[str, InjectedState("channel")],
) -> dict:
    """Agenda uma visita a um imóvel específico junto ao CRM. Só chame esta ferramenta depois
    que o cliente já tiver dado, nesta conversa, TODOS os quatro dados abaixo - nunca invente,
    suponha ou preencha um deles por conta própria. Se qualquer um estiver faltando, não chame
    esta ferramenta: use AgentTurn para perguntar o que falta primeiro.
    property_id deve vir de um resultado real de buscar_imoveis, nunca inventado.
    nome_lead e contato_lead devem ter sido informados explicitamente pelo cliente.
    data_hora_desejada deve ser uma data/hora futura em ISO 8601 (ex: "2026-10-01T15:00:00"),
    calculada a partir da data de hoje informada no contexto da conversa - nunca um palpite.
    Retorna a confirmação com corretor e horário em caso de sucesso, ou {"status": "error",
    "detail": ...} se o imóvel não existir, não estiver disponível, ou a data for inválida -
    nesse caso, peça a informação correta ao cliente em vez de tentar novamente com outro
    palpite."""
    return crm_client.book_visit(
        property_id=property_id,
        conversation_id=conversation_id,
        lead_name=nome_lead,
        lead_contact=contato_lead,
        requested_datetime=data_hora_desejada,
        channel=channel,
    )


TOOLS = [buscar_imoveis, buscar_dados_geograficos, buscar_rentabilidade, agendar_visita]


@tool
def buscar_financiamento(query: str) -> list[dict]:
    """Busca semântica na base de conhecimento sobre financiamento imobiliário (programas
    de financiamento, ITBI, escritura, condomínio/IPTU, elegibilidade e documentação). Use
    antes de responder qualquer pergunta sobre financiamento - nunca invente taxas, prazos
    ou percentuais que não vieram desta busca."""
    return search.search_financing(query)


MORTGAGE_ADVISOR_TOOLS = [buscar_financiamento]
