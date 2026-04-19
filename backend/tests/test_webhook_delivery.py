"""Webhook delivery helpers (no broker required)."""

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from app.utils.webhook_delivery import deliver_webhook


def test_deliver_skipped_when_no_url():
    with patch("app.utils.webhook_delivery.requests.post") as post:
        deliver_webhook(None, None, "tid", "SUCCESS", result={})
        post.assert_not_called()


def test_deliver_posts_json_and_signature():
    captured = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = headers
        r = MagicMock()
        r.raise_for_status = MagicMock()
        return r

    with patch("app.utils.webhook_delivery.requests.post", side_effect=fake_post):
        deliver_webhook(
            "https://example.com/hook",
            "my-secret",
            "abc-123",
            "SUCCESS",
            result={"ok": True},
        )

    assert captured["url"] == "https://example.com/hook"
    payload = json.loads(captured["data"].decode())
    assert payload == {
        "task_id": "abc-123",
        "state": "SUCCESS",
        "result": {"ok": True},
    }
    sig_header = captured["headers"]["X-Webhook-Signature"]
    assert sig_header.startswith("sha256=")
    expected = hmac.new(
        b"my-secret", captured["data"], hashlib.sha256
    ).hexdigest()
    assert sig_header == f"sha256={expected}"
