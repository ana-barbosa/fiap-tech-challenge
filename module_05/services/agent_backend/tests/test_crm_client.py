from unittest.mock import MagicMock, patch

import pytest
import requests as requests_module

from src import crm_client


def _response(status_code, payload):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = payload
    return mock


def test_book_visit_returns_crm_confirmation_on_success():
    confirmation = {
        "id": 1,
        "property_id": 1,
        "broker_name": "Ana Corretora",
        "broker_contact": "ana@imobiliaria.com",
        "confirmed_datetime": "2026-10-01T15:00:00",
        "status": "confirmed",
    }
    with patch("src.crm_client.requests.post", return_value=_response(201, confirmation)) as mock_post:
        result = crm_client.book_visit(
            property_id=1,
            conversation_id="conv-1",
            lead_name="Maria",
            lead_contact="maria@example.com",
            requested_datetime="2026-10-01T15:00:00",
        )

    assert result == confirmation
    payload = mock_post.call_args.kwargs["json"]
    assert payload == {
        "property_id": 1,
        "conversation_id": "conv-1",
        "lead_name": "Maria",
        "lead_contact": "maria@example.com",
        "requested_datetime": "2026-10-01T15:00:00",
    }


def test_book_visit_includes_channel_only_when_given():
    with patch("src.crm_client.requests.post", return_value=_response(201, {})) as mock_post:
        crm_client.book_visit(
            property_id=1,
            conversation_id="conv-1",
            lead_name="Maria",
            lead_contact="maria@example.com",
            requested_datetime="2026-10-01T15:00:00",
            channel="telegram",
        )

    assert mock_post.call_args.kwargs["json"]["channel"] == "telegram"


def test_book_visit_returns_error_on_not_found():
    with patch("src.crm_client.requests.post", return_value=_response(404, {"detail": "Property not found"})):
        result = crm_client.book_visit(
            property_id=999,
            conversation_id="conv-1",
            lead_name="Maria",
            lead_contact="maria@example.com",
            requested_datetime="2026-10-01T15:00:00",
        )

    assert result == {"status": "error", "detail": "Property not found"}


def test_book_visit_returns_error_on_unavailable_property():
    body = {"detail": "Property is not available for visits"}
    with patch("src.crm_client.requests.post", return_value=_response(409, body)):
        result = crm_client.book_visit(
            property_id=1,
            conversation_id="conv-1",
            lead_name="Maria",
            lead_contact="maria@example.com",
            requested_datetime="2026-10-01T15:00:00",
        )

    assert result == {"status": "error", "detail": "Property is not available for visits"}


def test_book_visit_returns_generic_message_for_list_shaped_validation_detail():
    body = {"detail": [{"loc": ["body", "lead_name"], "msg": "field required", "type": "missing"}]}
    with patch("src.crm_client.requests.post", return_value=_response(422, body)):
        result = crm_client.book_visit(
            property_id=1,
            conversation_id="conv-1",
            lead_name="",
            lead_contact="maria@example.com",
            requested_datetime="2026-10-01T15:00:00",
        )

    assert result["status"] == "error"
    assert isinstance(result["detail"], str)


def test_book_visit_returns_error_when_crm_unreachable():
    with patch("src.crm_client.requests.post", side_effect=requests_module.RequestException("boom")):
        result = crm_client.book_visit(
            property_id=1,
            conversation_id="conv-1",
            lead_name="Maria",
            lead_contact="maria@example.com",
            requested_datetime="2026-10-01T15:00:00",
        )

    assert result["status"] == "error"


def test_get_confirmed_visit_property_ids_returns_ids_from_crm_response():
    visits = [{"property_id": 34, "status": "confirmed"}, {"property_id": 12, "status": "confirmed"}]
    with patch("src.crm_client.requests.get", return_value=_response(200, visits)) as mock_get:
        result = crm_client.get_confirmed_visit_property_ids("conv-1")

    assert result == {"34", "12"}
    assert mock_get.call_args.kwargs["params"] == {"conversation_id": "conv-1", "status": "confirmed"}


def test_get_confirmed_visit_property_ids_returns_empty_set_when_no_visits():
    with patch("src.crm_client.requests.get", return_value=_response(200, [])):
        result = crm_client.get_confirmed_visit_property_ids("conv-1")

    assert result == set()


def test_get_confirmed_visit_property_ids_raises_when_crm_unreachable():
    with patch("src.crm_client.requests.get", side_effect=requests_module.RequestException("boom")):
        with pytest.raises(crm_client.CrmUnavailableError):
            crm_client.get_confirmed_visit_property_ids("conv-1")


def test_list_visits_returns_json_on_success():
    visits = [{"id": 1, "property_id": 34}]
    with patch("src.crm_client.requests.get", return_value=_response(200, visits)) as mock_get:
        result = crm_client.list_visits(conversation_id="conv-1")

    assert result == visits
    assert mock_get.call_args.kwargs["params"] == {"conversation_id": "conv-1"}


def test_list_visits_omits_none_filters():
    with patch("src.crm_client.requests.get", return_value=_response(200, [])) as mock_get:
        crm_client.list_visits(conversation_id=None, status="confirmed")

    assert mock_get.call_args.kwargs["params"] == {"status": "confirmed"}


def test_list_visits_raises_when_crm_unreachable():
    with patch("src.crm_client.requests.get", side_effect=requests_module.RequestException("boom")):
        with pytest.raises(crm_client.CrmUnavailableError):
            crm_client.list_visits()


def test_list_properties_returns_json_on_success():
    listings = [{"id": 1, "city": "Taubaté"}]
    with patch("src.crm_client.requests.get", return_value=_response(200, listings)) as mock_get:
        result = crm_client.list_properties(status="available", city="Taubaté")

    assert result == listings
    assert mock_get.call_args.kwargs["params"] == {"status": "available", "city": "Taubaté"}


def test_list_properties_omits_none_filters():
    with patch("src.crm_client.requests.get", return_value=_response(200, [])) as mock_get:
        crm_client.list_properties(status="available", listing_type=None)

    assert mock_get.call_args.kwargs["params"] == {"status": "available"}


def test_list_properties_raises_when_crm_unreachable():
    with patch("src.crm_client.requests.get", side_effect=requests_module.RequestException("boom")):
        with pytest.raises(crm_client.CrmUnavailableError):
            crm_client.list_properties()


def test_get_property_returns_none_on_404():
    with patch("src.crm_client.requests.get", return_value=_response(404, {})):
        assert crm_client.get_property(999) is None


def test_get_property_returns_json_on_success():
    listing = {"id": 1, "city": "Taubaté"}
    with patch("src.crm_client.requests.get", return_value=_response(200, listing)):
        assert crm_client.get_property(1) == listing


def test_get_property_raises_when_crm_unreachable():
    with patch("src.crm_client.requests.get", side_effect=requests_module.RequestException("boom")):
        with pytest.raises(crm_client.CrmUnavailableError):
            crm_client.get_property(1)
