"""POST task completion payloads to a caller-provided URL (compare with polling /status)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

import requests

from app.utils.config import webhook_timeout_seconds
from app.utils.schemas import WebhookPayload

logger = logging.getLogger(__name__)


def deliver_webhook(
    webhook_url: str,
    webhook_secret: str | None,
    task_id: str,
    state: str,
    *,
    result: object | None = None,
    error: str | None = None,
    raise_on_failure: bool = False,
) -> None:
    """Notify webhook_url when a task finishes. Failures to deliver are logged, not raised."""
    payload = WebhookPayload(task_id=task_id, state=state, result=result, error=error)
    body = json.dumps(
        payload.model_dump(mode="json", exclude_none=True),
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if webhook_secret:
        sig = hmac.new(
            webhook_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={sig}"

    try:
        r = requests.post(
            webhook_url,
            data=body,
            headers=headers,
            timeout=webhook_timeout_seconds(),
        )
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning(
            "Webhook delivery failed for task_id=%s url=%s: %s",
            task_id,
            webhook_url,
            e,
        )
        if raise_on_failure:
            raise
