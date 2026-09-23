from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src import main
from src.main import app

client = TestClient(app)


def test_health_returns_initial_state_without_starting_the_poll_loop():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "starting"
    assert body["last_update_id"] is None
    assert body["last_error"] is None


def test_push_relays_to_telegram_client_send_message(monkeypatch):
    fake_send_message = MagicMock()
    monkeypatch.setattr(main.telegram_client, "send_message", fake_send_message)

    response = client.post("/push", json={"chat_id": 123, "text": "Oi de novo!"})

    assert response.status_code == 200
    assert response.json() == {"status": "sent"}
    fake_send_message.assert_called_once_with(123, "Oi de novo!")
