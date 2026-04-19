import time

from app.celery_app import celery_app
from app.utils.schemas import SubmitRequest
from celery.result import AsyncResult
from fastapi import APIRouter

router = APIRouter(tags=["tasks"])


@router.post("/submit")
def submit(req: SubmitRequest):
    """Submit text for background processing. Returns a Celery task id."""
    request_start_time = time.time()
    task = celery_app.send_task(
        "app.tasks.process_text", args=[req.text, request_start_time]
    )
    return {"task_id": task.id}


@router.get("/status/{task_id}")
def status(task_id: str):
    """Get status/result for a task id, including progress meta if available."""
    result = AsyncResult(task_id, app=celery_app)
    response = {"task_id": task_id, "state": result.state}

    info = result.info
    if info is not None:
        response["meta"] = info

    if result.state == "SUCCESS":
        response["result"] = result.result
    elif result.state == "FAILURE":
        response["error"] = str(result.result)

    return response
