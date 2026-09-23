import pytest
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import ValidationError

from src.qualification import Intent, InvestorProfile, Qualification, ValeDoParaibaCity


def test_empty_qualification_is_valid():
    q = Qualification()
    assert q.intent is None
    assert q.region is None


def test_typical_rent_qualification():
    q = Qualification(
        intent=Intent.RENT,
        price_min=1700.0,
        price_max=2300.0,
        rooms=2,
        region=[ValeDoParaibaCity.TAUBATE, ValeDoParaibaCity.SAO_JOSE_DOS_CAMPOS],
        lease_duration_months=12,
        move_in_date="2026-11-01",
    )
    assert q.region == [ValeDoParaibaCity.TAUBATE, ValeDoParaibaCity.SAO_JOSE_DOS_CAMPOS]
    assert q.lease_duration_months == 12


def test_typical_invest_qualification():
    q = Qualification(
        intent=Intent.INVEST,
        investor_profile=InvestorProfile.FIRST_TIME,
        ticket_size=300_000.0,
        expected_return=0.08,
    )
    assert q.expected_return == 0.08


def test_region_accepts_exact_city_name_string():
    q = Qualification(region=["Ubatuba"])
    assert q.region == [ValeDoParaibaCity.UBATUBA]


def test_region_rejects_unknown_city():
    with pytest.raises(ValidationError, match="region"):
        Qualification(region=["Cidade Que Nao Existe"])


def test_region_wraps_bare_city_string_in_list():
    q = Qualification(region="Ilhabela")
    assert q.region == [ValeDoParaibaCity.ILHABELA]

    q_alias = Qualification(regiao="Taubaté")
    assert q_alias.region == [ValeDoParaibaCity.TAUBATE]


def test_price_min_above_max_rejected():
    with pytest.raises(ValidationError, match="price_min"):
        Qualification(price_min=3000.0, price_max=2000.0)


def test_negative_price_rejected():
    with pytest.raises(ValidationError):
        Qualification(price_min=-100.0)


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        Qualification(favorite_color="blue")


def test_constructs_by_portuguese_alias_too():
    q = Qualification(intencao="alugar", quartos=2)
    assert q.intent == Intent.RENT
    assert q.rooms == 2


def test_constructs_by_english_name_still_works():
    q = Qualification(intent="alugar", rooms=2)
    assert q.intent == Intent.RENT
    assert q.rooms == 2


def test_llm_facing_schema_uses_portuguese_keys():
    schema = convert_to_openai_tool(Qualification)["function"]["parameters"]["properties"]
    assert "intencao" in schema
    assert "intent" not in schema
    assert "preco_min" in schema
    assert "regiao" in schema
