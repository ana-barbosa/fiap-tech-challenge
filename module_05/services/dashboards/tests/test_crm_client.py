import sys
from pathlib import Path
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crm_client import CrmUnavailableError, get_property, list_properties, list_visits, photo_url  # noqa: E402


def test_list_properties_returns_json_on_success():
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = [{"id": 1}]
    fake_response.raise_for_status = Mock()
    with patch("crm_client.requests.get", return_value=fake_response) as mocked_get:
        result = list_properties(city="Ubatuba")
    assert result == [{"id": 1}]
    assert mocked_get.call_args.kwargs["params"] == {"city": "Ubatuba"}


def test_list_properties_omits_none_filters():
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = []
    fake_response.raise_for_status = Mock()
    with patch("crm_client.requests.get", return_value=fake_response) as mocked_get:
        list_properties(city=None, status="sold")
    assert mocked_get.call_args.kwargs["params"] == {"status": "sold"}


def test_list_properties_raises_crm_unavailable_on_connection_error():
    with patch("crm_client.requests.get", side_effect=requests.ConnectionError("boom")):
        try:
            list_properties()
            assert False, "expected CrmUnavailableError"
        except CrmUnavailableError:
            pass


def test_get_property_returns_none_on_404():
    fake_response = Mock(status_code=404)
    with patch("crm_client.requests.get", return_value=fake_response):
        assert get_property(999) is None


def test_get_property_returns_json_on_success():
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = {"id": 1, "city": "Taubaté"}
    fake_response.raise_for_status = Mock()
    with patch("crm_client.requests.get", return_value=fake_response):
        assert get_property(1) == {"id": 1, "city": "Taubaté"}


def test_list_visits_returns_json_on_success():
    fake_response = Mock(status_code=200)
    fake_response.json.return_value = [{"id": 1, "property_id": 34}]
    fake_response.raise_for_status = Mock()
    with patch("crm_client.requests.get", return_value=fake_response) as mocked_get:
        result = list_visits(conversation_id="conv-1")
    assert result == [{"id": 1, "property_id": 34}]
    assert mocked_get.call_args.kwargs["params"] == {"conversation_id": "conv-1"}


def test_list_visits_raises_crm_unavailable_on_connection_error():
    with patch("crm_client.requests.get", side_effect=requests.ConnectionError("boom")):
        try:
            list_visits()
            assert False, "expected CrmUnavailableError"
        except CrmUnavailableError:
            pass


def test_photo_url_uses_public_base_url():
    assert photo_url("12/0.jpg").endswith("/static/photos/12/0.jpg")
