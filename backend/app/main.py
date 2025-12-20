import os
import time

from app.celery_app import celery_app
from celery.result import AsyncResult
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class SubmitRequest(BaseModel):
    text: str


app = FastAPI()

# Allow CORS from the frontend. Read allowed origins from env or default to localhost:3000
cors_origins = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/submit")
def submit(req: SubmitRequest):
    """Submit text for background processing. Returns a Celery task id."""
    # Record the start time when the request is received
    request_start_time = time.time()
    task = celery_app.send_task("app.tasks.process_text", args=[req.text, request_start_time])
    return {"task_id": task.id}


@app.get("/status/{task_id}")
def status(task_id: str):
    """Get status/result for a task id, including progress meta if available."""
    result = AsyncResult(task_id, app=celery_app)
    response = {"task_id": task_id, "state": result.state}

    # Celery stores progress metadata in result.info for non-final states
    info = result.info
    if info is not None:
        # meta could contain current/total/percent
        response["meta"] = info

    if result.state == "SUCCESS":
        response["result"] = result.result
    elif result.state == "FAILURE":
        response["error"] = str(result.result)

    return response
