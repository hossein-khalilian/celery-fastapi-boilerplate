import asyncio
import os
import time
from uuid import uuid4

from app.celery_app import celery_app
from app.webhook_inbox import (
    inbox_status,
    inbox_token_exists,
    reserve_inbox_token,
    store_delivery,
)
from app.webhook_sse import publish_delivery, register_waiter, sse_chunk, unregister_waiter
from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


class SubmitRequest(BaseModel):
    text: str


class WebhookSubmitRequest(BaseModel):
    text: str


app = FastAPI()

# Allow CORS from the frontend (e.g. https://dev.ir). Read origins from env or default to *
cors_origins = [
    origin.strip() for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base URL the Celery worker uses to POST webhook callbacks (must be reachable from worker)
WEBHOOK_CALLBACK_BASE = os.environ.get(
    "WEBHOOK_CALLBACK_BASE", "http://backend:5000"
).rstrip("/")


@app.get("/health")
def health():
    """Health check for load balancers and CI."""
    return {"status": "ok"}


@app.post("/submit")
def submit(req: SubmitRequest):
    """Submit text for background processing. Returns a Celery task id."""
    # Record the start time when the request is received
    request_start_time = time.time()
    task = celery_app.send_task(
        "app.tasks.process_text", args=[req.text, request_start_time]
    )
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


@app.post("/webhook/submit")
def webhook_submit(req: WebhookSubmitRequest):
    """Enqueue the webhook task; worker notifies ``/webhook/inbox/{token}`` when done."""
    request_start_time = time.time()
    inbox_token = str(uuid4())
    reserve_inbox_token(inbox_token)
    webhook_url = f"{WEBHOOK_CALLBACK_BASE}/webhook/inbox/{inbox_token}"
    task = celery_app.send_task(
        "app.tasks.process_text_webhook",
        args=[req.text, request_start_time, webhook_url],
        kwargs={"webhook_secret": None},
    )
    return {
        "task_id": task.id,
        "inbox_token": inbox_token,
        "webhook_url": webhook_url,
    }


@app.post("/webhook/inbox/{token}")
async def webhook_inbox_post(token: str, request: Request):
    """Receive POST from the worker (same JSON shape as ``deliver_webhook``)."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Expected JSON body") from None
    if not isinstance(payload, dict):
        raise HTTPException(400, "Body must be a JSON object")
    if not store_delivery(token, payload):
        raise HTTPException(404, "Unknown inbox token")
    await publish_delivery(token, payload)
    return {"ok": True}


@app.get("/webhook/inbox/{token}")
def webhook_inbox_get(token: str):
    """Poll for a delivery (optional; compare UI prefers SSE)."""
    st = inbox_status(token)
    if not st.get("exists"):
        raise HTTPException(404, "Unknown inbox token")
    return st


@app.get("/webhook/stream/{token}")
async def webhook_stream(token: str):
    """Server-Sent Events: push the same JSON body as ``POST /webhook/inbox`` when it arrives."""
    if not inbox_token_exists(token):
        raise HTTPException(404, "Unknown inbox token")

    async def events():
        q = await register_waiter(token)
        try:
            st = inbox_status(token)
            if st.get("received") and st.get("payload"):
                yield sse_chunk(st["payload"])
                return
            payload = await asyncio.wait_for(q.get(), timeout=3600.0)
            yield sse_chunk(payload)
        except asyncio.TimeoutError:
            return
        finally:
            await unregister_waiter(token, q)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
