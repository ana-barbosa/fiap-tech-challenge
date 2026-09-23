from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def _sample_payload(**overrides):
    payload = {
        "listing_type": "sale",
        "city": "Taubaté",
        "neighborhood": "Centro",
        "property_type": "apartment",
        "price": 350000,
        "rooms": 2,
        "area_sqm": 65,
        "description": "Apartamento reformado no centro.",
        "status": "available",
    }
    payload.update(overrides)
    return payload


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_property():
    created = client.post("/properties", json=_sample_payload())
    assert created.status_code == 201
    listing_id = created.json()["id"]

    fetched = client.get(f"/properties/{listing_id}")
    assert fetched.status_code == 200
    assert fetched.json()["city"] == "Taubaté"


def test_list_properties_defaults_to_available_status():
    client.post("/properties", json=_sample_payload(city="Jacareí"))
    response = client.get("/properties")
    assert response.status_code == 200
    assert all(item["status"] == "available" for item in response.json())


def test_list_properties_filters_by_city():
    client.post("/properties", json=_sample_payload(city="Lorena"))
    response = client.get("/properties", params={"city": "Lorena"})
    assert response.status_code == 200
    assert all(item["city"] == "Lorena" for item in response.json())


def test_get_property_not_found():
    response = client.get("/properties/999999")
    assert response.status_code == 404


def test_update_property_status():
    created = client.post("/properties", json=_sample_payload(city="Cruzeiro"))
    listing_id = created.json()["id"]

    updated = client.patch(f"/properties/{listing_id}", json={"status": "sold"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "sold"


def test_update_property_not_found():
    response = client.patch("/properties/999999", json={"status": "sold"})
    assert response.status_code == 404


def _visit_payload(property_id, **overrides):
    payload = {
        "property_id": property_id,
        "conversation_id": "conv-1",
        "lead_name": "Maria",
        "lead_contact": "maria@example.com",
        "requested_datetime": "2999-01-01T10:00:00",
    }
    payload.update(overrides)
    return payload


def test_visit_requires_future_datetime():
    created = client.post("/properties", json=_sample_payload(city="Caçapava"))
    listing_id = created.json()["id"]

    payload = _visit_payload(listing_id, requested_datetime="2000-01-01T10:00:00")
    response = client.post("/visits", json=payload)
    assert response.status_code == 422


def test_visit_for_missing_property_returns_404():
    payload = _visit_payload(999999)
    response = client.post("/visits", json=payload)
    assert response.status_code == 404


def test_visit_for_unavailable_property_returns_409():
    created = client.post("/properties", json=_sample_payload(city="Guaratinguetá"))
    listing_id = created.json()["id"]
    client.patch(f"/properties/{listing_id}", json={"status": "sold"})

    payload = _visit_payload(listing_id)
    response = client.post("/visits", json=payload)
    assert response.status_code == 409


def test_visit_success_returns_broker_info_and_id():
    created = client.post("/properties", json=_sample_payload(city="Pindamonhangaba"))
    listing_id = created.json()["id"]

    payload = _visit_payload(listing_id)
    response = client.post("/visits", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["broker_name"]
    assert body["broker_contact"]
    assert isinstance(body["id"], int)
    assert body["conversation_id"] == payload["conversation_id"]
    assert body["lead_name"] == payload["lead_name"]
    assert body["lead_contact"] == payload["lead_contact"]


def test_visit_is_persisted_and_queryable_by_conversation_id():
    created = client.post("/properties", json=_sample_payload(city="Lorena"))
    listing_id = created.json()["id"]

    payload = _visit_payload(listing_id, conversation_id="conv-persist")
    booked = client.post("/visits", json=payload)
    assert booked.status_code == 201

    response = client.get("/visits", params={"conversation_id": "conv-persist"})
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["property_id"] == listing_id
    assert rows[0]["id"] == booked.json()["id"]
    assert rows[0]["conversation_id"] == "conv-persist"
    assert rows[0]["lead_name"] == payload["lead_name"]
    assert rows[0]["lead_contact"] == payload["lead_contact"]


def test_visits_filter_by_property_id_and_status():
    created = client.post("/properties", json=_sample_payload(city="Aparecida"))
    listing_id = created.json()["id"]
    client.post("/visits", json=_visit_payload(listing_id, conversation_id="conv-filter"))

    response = client.get("/visits", params={"property_id": listing_id, "status": "confirmed"})
    assert response.status_code == 200
    assert all(row["property_id"] == listing_id for row in response.json())


def test_visits_empty_when_conversation_id_unknown():
    response = client.get("/visits", params={"conversation_id": "no-such-conversation"})
    assert response.status_code == 200
    assert response.json() == []


def test_visits_with_no_filters_returns_all():
    created = client.post("/properties", json=_sample_payload(city="Ubatuba"))
    listing_id = created.json()["id"]
    client.post("/visits", json=_visit_payload(listing_id, conversation_id="conv-no-filter"))

    response = client.get("/visits")
    assert response.status_code == 200
    assert any(row["property_id"] == listing_id for row in response.json())
