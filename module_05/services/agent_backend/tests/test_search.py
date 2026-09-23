from src.search import search_financing, search_geo, search_listings, search_roi


def test_search_listings_semantic_only():
    results = search_listings("casa de praia perto da areia", n_results=1)
    assert results[0]["id"] == "2"
    assert results[0]["city"] == "Ubatuba"
    assert "description" in results[0]


def test_search_listings_filters_by_city():
    results = search_listings("apartamento", cities=["Taubaté"], n_results=5)
    assert all(r["city"] == "Taubaté" for r in results)
    assert len(results) == 1


def test_search_listings_filters_by_price_range():
    results = search_listings("imóvel", price_min=400_000.0, price_max=500_000.0, n_results=5)
    assert len(results) == 1
    assert results[0]["id"] == "3"


def test_search_listings_filters_by_listing_type():
    results = search_listings("imóvel", listing_type="rent", n_results=5)
    assert len(results) == 1
    assert results[0]["listing_type"] == "rent"


def test_search_listings_combines_multiple_filters():
    results = search_listings(
        "imóvel", cities=["Ubatuba", "São José dos Campos"], property_type="house", n_results=5
    )
    assert len(results) == 1
    assert results[0]["id"] == "2"


def test_search_listings_filters_by_rooms():
    # rooms is a minimum, not an exact match - listings with 2 or 3 rooms both qualify.
    results = search_listings("imóvel", rooms=2, n_results=5)
    assert {r["id"] for r in results} == {"1", "2", "3"}


def test_search_listings_filters_by_rooms_excludes_below_minimum():
    results = search_listings("imóvel", rooms=3, n_results=5)
    assert {r["id"] for r in results} == {"2", "3"}


def test_search_listings_no_filters_returns_all():
    results = search_listings("imóvel", n_results=10)
    assert len(results) == 3


def test_search_geo_returns_city_and_content():
    results = search_geo("cidade litorânea com praias", n_results=1)
    assert results[0]["city"] == "Ubatuba"
    assert "content" in results[0]


def test_search_roi_returns_seeded_segment():
    results = search_roi("yield em Taubaté", n_results=5)
    assert len(results) == 1
    assert results[0]["gross_yield"] == 0.072


def test_search_roi_filters_by_city():
    results = search_roi("yield", cities=["Ubatuba"], n_results=5)
    assert results == []


def test_search_roi_filters_by_property_type():
    results = search_roi("yield", property_type="apartment", n_results=5)
    assert len(results) == 1
    results_house = search_roi("yield", property_type="house", n_results=5)
    assert results_house == []


def test_search_financing_returns_topic_and_content():
    results = search_financing("qual o percentual do ITBI?", n_results=1)
    assert results[0]["topic"] == "itbi"
    assert "content" in results[0]
