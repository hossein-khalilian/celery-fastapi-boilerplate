"""Shared text-processing steps used by Celery task entrypoints."""

from __future__ import annotations

import time
from typing import Any


def run_text_pipeline(task: Any, text: str, request_start_time: float) -> dict:
    """Run the demo pipeline; ``task`` must support ``update_state`` like a Celery task."""
    words = text.split()
    total_steps = len(words) if len(words) > 0 else 5

    for i in range(total_steps):
        time.sleep(1)
        percent = int(((i + 1) / total_steps) * 100)
        task.update_state(
            state="PROGRESS",
            meta={
                "current": i + 1,
                "total": total_steps,
                "percent": percent,
            },
        )

    task.update_state(
        state="PROGRESS",
        meta={
            "current": total_steps,
            "total": total_steps,
            "percent": 100,
        },
    )
    time.sleep(0.1)

    elapsed_time = time.time() - request_start_time
    return {
        "original_length": len(text),
        "word_count": len(words),
        "reversed": text[::-1],
        "elapsed_time": round(elapsed_time, 2),
    }
