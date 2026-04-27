from app.celery_app import celery_app
from app.services.text_pipeline import run_text_pipeline


@celery_app.task(bind=True, name="app.tasks.process_text")
def process_text(self, text: str, request_start_time: float):
    """Simulate a long-running text processing task and report progress.

    The task updates its state periodically with meta: {current, total, percent}.
    request_start_time is the timestamp when the request was received by the endpoint.
    """
    return run_text_pipeline(self, text, request_start_time)
