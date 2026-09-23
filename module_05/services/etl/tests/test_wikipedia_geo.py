from unittest.mock import MagicMock, patch

from src import wikipedia_geo

REGION_HTML = """
<div id="mw-content-text">
  <ul>
    <li><a href="/wiki/Taubat%C3%A9">Taubaté</a></li>
    <li><a href="https://pt.wikipedia.org/wiki/Cunha_(S%C3%A3o_Paulo)">Cunha</a></li>
  </ul>
</div>
"""

CITY_HTML = """
<table class="infobox">
  <tr><th>População</th><td>300.000 <sup class="reference">[1]</sup></td></tr>
</table>
<div id="mw-content-text">
  <p>Taubaté é uma cidade no Vale do Paraíba.</p>
  <p>Segundo parágrafo com mais contexto.</p>
</div>
"""


def _response(text):
    mock = MagicMock()
    mock.text = text
    mock.raise_for_status.return_value = None
    return mock


def setup_function():
    wikipedia_geo._region_index_cache = None


def test_resolve_city_url_uses_region_page_index():
    with patch("src.wikipedia_geo.requests.get", return_value=_response(REGION_HTML)):
        assert wikipedia_geo.resolve_city_url("Taubaté") == "https://pt.wikipedia.org/wiki/Taubat%C3%A9"
        assert wikipedia_geo.resolve_city_url("Cunha") == "https://pt.wikipedia.org/wiki/Cunha_(S%C3%A3o_Paulo)"


def test_resolve_city_url_falls_back_to_constructed_slug_when_not_on_region_page():
    with patch("src.wikipedia_geo.requests.get", return_value=_response(REGION_HTML)):
        url = wikipedia_geo.resolve_city_url("Cidade Desconhecida")
    assert url == "https://pt.wikipedia.org/wiki/Cidade_Desconhecida"


def test_scrape_city_geo_extracts_infobox_and_prose_and_strips_citation_markers():
    with patch("src.wikipedia_geo.requests.get", side_effect=[_response(REGION_HTML), _response(CITY_HTML)]):
        result = wikipedia_geo.scrape_city_geo("Taubaté")

    assert result["metadata"]["city"] == "Taubaté"
    assert result["metadata"]["populacao"] == "300.000"
    assert "Taubaté é uma cidade" in result["document"]
    assert "Segundo parágrafo" in result["document"]
