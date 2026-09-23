from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_returns_initial_state_without_starting_the_poll_loop():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "starting"
    assert body["last_run_at"] is None
    assert body["last_error"] is None
