"""Webhook variant: same work as ``process_text``, then enqueue delivery."""

from app.celery_app import celery_app
from app.services.text_pipeline import run_text_pipeline
from app.tasks.deliver_webhook import deliver_webhook


@celery_app.task(bind=True, name="app.tasks.process_text_webhook")
def process_text_webhook(
    self,
    text: str,
    request_start_time: float,
    webhook_url: str | None,
    webhook_secret: str | None = None,
):
    """Like ``process_text``, but enqueues webhook delivery on completion."""
    task_id = self.request.id
    try:
        processed = run_text_pipeline(self, text, request_start_time)
        deliver_webhook.delay(
            webhook_url,
            webhook_secret,
            task_id,
            "SUCCESS",
            result=processed,
        )
        return processed
    except Exception as e:
        deliver_webhook.delay(
            webhook_url,
            webhook_secret,
            task_id,
            "FAILURE",
            error=str(e),
        )
        raise
