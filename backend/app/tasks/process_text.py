import time

from app.celery_app import celery_app


@celery_app.task(bind=True, name="app.tasks.process_text")
def process_text(self, text: str, request_start_time: float):
    """Simulate a long-running text processing task and report progress.

    The task updates its state periodically with meta: {current, total, percent}.
    request_start_time is the timestamp when the request was received by the endpoint.
    """
    # naive step count: use number of words (or fallback to 5 steps)
    words = text.split()
    total_steps = len(words) if len(words) > 0 else 5

    # simulate incremental processing and send progress updates
    for i in range(total_steps):
        # simulate work for this step
        time.sleep(1)
        percent = int(((i + 1) / total_steps) * 100)
        # update progress state
        self.update_state(
            state="PROGRESS",
            meta={
                "current": i + 1,
                "total": total_steps,
                "percent": percent,
            },
        )

    # Calculate total elapsed time from when request was received to when task completes
    elapsed_time = time.time() - request_start_time

    # final result
    processed = {
        "original_length": len(text),
        "word_count": len(words),
        "reversed": text[::-1],
        "elapsed_time": round(elapsed_time, 2),  # Total time from request to completion
    }
    return processed
