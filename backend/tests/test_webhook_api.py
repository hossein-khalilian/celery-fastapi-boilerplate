"""Webhook compare API (no Celery broker required for inbox routes)."""

from unittest.mock import MagicMock, patch

from app.main import app
from app.utils.webhook_inbox import reserve_inbox_token
from fastapi.testclient import TestClient

client = TestClient(app)


def test_webhook_inbox_post_and_get():
    reserve_inbox_token("demo-token")
    r = client.post(
        "/webhook/inbox/demo-token",
        json={"task_id": "t1", "state": "SUCCESS", "result": {"ok": True}},
    )
    assert r.status_code == 200
    g = client.get("/webhook/inbox/demo-token")
    assert g.status_code == 200
    data = g.json()
    assert data["received"] is True
    assert data["payload"]["state"] == "SUCCESS"


def test_webhook_inbox_unknown_token():
    r = client.post("/webhook/inbox/does-not-exist", json={"state": "SUCCESS"})
    assert r.status_code == 404


@patch("app.routes.webhooks.celery_app.send_task")
def test_webhook_submit_returns_task_and_inbox(mock_send: MagicMock):
    mock_send.return_value = MagicMock(id="celery-task-id")
    r = client.post("/webhook/submit", json={"text": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert body["task_id"] == "celery-task-id"
    assert "inbox_token" in body
    mock_send.assert_called_once()


def test_webhook_stream_unknown_token():
    r = client.get("/webhook/stream/does-not-exist")
    assert r.status_code == 404


def test_webhook_stream_after_delivery():
    reserve_inbox_token("sse-late")
    r = client.post(
        "/webhook/inbox/sse-late",
        json={"task_id": "t1", "state": "SUCCESS", "result": {"ok": True}},
    )
    assert r.status_code == 200
    with client.stream("GET", "/webhook/stream/sse-late") as resp:
        assert resp.status_code == 200
        body = b"".join(resp.iter_bytes())
    assert b"data:" in body
    assert b'"state":"SUCCESS"' in body
