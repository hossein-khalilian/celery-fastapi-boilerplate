"""Dedicated Celery task for webhook delivery."""

from __future__ import annotations

import logging
import random

import requests

from app.celery_app import celery_app
from app.utils.config import (
    webhook_max_retries,
    webhook_retry_backoff_cap_seconds,
    webhook_retry_jitter_seconds,
)
from app.utils.webhook_delivery import deliver_webhook as send_webhook

logger = logging.getLogger(__name__)


def _should_retry(exc: requests.RequestException) -> bool:
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


@celery_app.task(
    bind=True, name="app.tasks.deliver_webhook", max_retries=webhook_max_retries()
)
def deliver_webhook(
    self,
    webhook_url: str | None,
    webhook_secret: str | None,
    task_id: str,
    state: str,
    *,
    result=None,
    error: str | None = None,
):
    if not webhook_url:
        return

    try:
        send_webhook(
            webhook_url,
            webhook_secret,
            task_id,
            state,
            result=result,
            error=error,
            raise_on_failure=True,
        )
    except requests.RequestException as exc:
        if _should_retry(exc):
            countdown = min(
                2**self.request.retries, webhook_retry_backoff_cap_seconds()
            ) + random.randint(0, webhook_retry_jitter_seconds())
            logger.warning(
                "Webhook transient failure for task_id=%s url=%s; retry=%s in %ss: %s",
                task_id,
                webhook_url,
                self.request.retries + 1,
                countdown,
                exc,
            )
            raise self.retry(exc=exc, countdown=countdown) from exc

        logger.error(
            "Webhook permanent failure for task_id=%s url=%s: %s",
            task_id,
            webhook_url,
            exc,
        )
