"""Webhook variant: same work as ``process_text``, then POST completion to a URL."""

from app.celery_app import celery_app
from app.tasks.text_pipeline import run_text_pipeline
from app.webhook_delivery import deliver_webhook


@celery_app.task(bind=True, name="app.tasks.process_text_webhook")
def process_text_webhook(
    self,
    text: str,
    request_start_time: float,
    webhook_url: str | None,
    webhook_secret: str | None = None,
):
    """Like ``process_text``, but notifies ``webhook_url`` on success or failure."""
    task_id = self.request.id
    try:
        processed = run_text_pipeline(self, text, request_start_time)
        deliver_webhook(
            webhook_url,
            webhook_secret,
            task_id,
            "SUCCESS",
            result=processed,
        )
        return processed
    except Exception as e:
        deliver_webhook(
            webhook_url,
            webhook_secret,
            task_id,
            "FAILURE",
            error=str(e),
        )
        raise
