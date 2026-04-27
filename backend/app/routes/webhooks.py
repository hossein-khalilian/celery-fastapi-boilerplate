import asyncio
import time

from app.celery_app import celery_app
from app.utils.config import webhook_callback_base
from app.utils.schemas import WebhookPayload, WebhookSubmitRequest
from app.utils.webhook_inbox import (
    create_inbox_token,
    inbox_status,
    inbox_token_exists,
    publish_delivery_event,
    store_delivery,
)
from app.utils.webhook_sse import sse_chunk, wait_inbox_payload
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

router = APIRouter(tags=["webhooks"])


@router.post("/webhook/submit")
async def webhook_submit(req: WebhookSubmitRequest):
    """Enqueue processing and dispatch webhook delivery on the webhooks queue."""
    request_start_time = time.time()
    task = celery_app.send_task(
        "app.tasks.process_text_webhook",
        args=[req.text, request_start_time, str(req.webhook_url)],
        kwargs={"webhook_secret": req.webhook_secret},
    )
    return {"task_id": task.id}


@router.post("/webhook/inbox/register")
async def webhook_inbox_register():
    """Create a backend inbox token and callback URL for frontend SSE consumers."""
    token = await create_inbox_token()
    callback_url = f"{webhook_callback_base()}/webhook/inbox/{token}"
    return {"inbox_token": token, "webhook_url": callback_url}


@router.post("/webhook/inbox/{token}")
async def webhook_inbox_post(token: str, request: Request):
    """Receive POST from the worker (same JSON shape as ``deliver_webhook``)."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Expected JSON body") from None
    if not isinstance(payload, dict):
        raise HTTPException(400, "Body must be a JSON object")
    try:
        validated_payload = WebhookPayload.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(400, f"Invalid webhook payload: {exc.errors()}") from None
    if not await store_delivery(
        token, validated_payload.model_dump(mode="json", exclude_none=True)
    ):
        raise HTTPException(404, "Unknown inbox token")
    await publish_delivery_event(
        token,
        validated_payload.model_dump(mode="json", exclude_none=True),
    )
    return {"ok": True}


@router.get("/webhook/inbox/{token}")
async def webhook_inbox_get(token: str):
    """Poll for a delivery (optional; compare UI prefers SSE)."""
    st = await inbox_status(token)
    if not st.get("exists"):
        raise HTTPException(404, "Unknown inbox token")
    return st


@router.get("/webhook/stream/{token}")
async def webhook_stream(token: str):
    """Server-Sent Events: push the same JSON body as ``POST /webhook/inbox`` when it arrives."""
    if not await inbox_token_exists(token):
        raise HTTPException(404, "Unknown inbox token")

    async def events():
        try:
            payload = await wait_inbox_payload(token, timeout=3600.0)
            yield sse_chunk(payload)
        except asyncio.TimeoutError:
            return

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
