from unittest.mock import MagicMock, patch

import pytest
import requests as requests_module

from src import crm_client


def _response(payload):
    mock = MagicMock()
    mock.json.return_value = payload
    mock.raise_for_status.return_value = None
    return mock


def test_paginates_until_a_short_page_is_returned():
    page1 = [{"id": i} for i in range(crm_client.PAGE_LIMIT)]
    page2 = [{"id": 100}, {"id": 101}]
    with patch("src.crm_client.requests.get", side_effect=[_response(page1), _response(page2)]) as mock_get:
        listings = crm_client.fetch_available_listings()

    assert len(listings) == crm_client.PAGE_LIMIT + 2
    assert mock_get.call_count == 2
    assert mock_get.call_args_list[0].kwargs["params"]["offset"] == 0
    assert mock_get.call_args_list[1].kwargs["params"]["offset"] == crm_client.PAGE_LIMIT
    assert mock_get.call_args_list[0].kwargs["params"]["status"] == "available"


def test_single_short_page_stops_after_one_request():
    with patch("src.crm_client.requests.get", return_value=_response([{"id": 1}])) as mock_get:
        listings = crm_client.fetch_available_listings()
    assert listings == [{"id": 1}]
    assert mock_get.call_count == 1


def test_request_exception_raises_crm_unavailable_error():
    with patch("src.crm_client.requests.get", side_effect=requests_module.RequestException("boom")):
        with pytest.raises(crm_client.CrmUnavailableError):
            crm_client.fetch_available_listings()
