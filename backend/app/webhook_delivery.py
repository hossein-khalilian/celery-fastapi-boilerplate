"""POST task completion payloads to a caller-provided URL (compare with polling /status)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


def deliver_webhook(
    webhook_url: str | None,
    webhook_secret: str | None,
    task_id: str,
    state: str,
    *,
    result: Any | None = None,
    error: str | None = None,
) -> None:
    """Notify webhook_url when a task finishes. Failures to deliver are logged, not raised."""
    if not webhook_url:
        return

    payload: dict[str, Any] = {"task_id": task_id, "state": state}
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error

    body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if webhook_secret:
        sig = hmac.new(
            webhook_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={sig}"

    try:
        r = requests.post(webhook_url, data=body, headers=headers, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning(
            "Webhook delivery failed for task_id=%s url=%s: %s",
            task_id,
            webhook_url,
            e,
        )
