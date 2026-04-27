"""Helpers for formatting SSE chunks and waiting for inbox payloads."""

from __future__ import annotations

import asyncio
import json

from app.utils import redis_client
from app.utils.webhook_inbox import inbox_channel, inbox_status


def sse_chunk(payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":"), default=str)
    return f"data: {body}\n\n"


async def wait_inbox_payload(token: str, timeout: float = 30.0) -> dict:
    async def _wait() -> dict:
        initial_status = await inbox_status(token)
        if initial_status.get("received") and initial_status.get("payload") is not None:
            return initial_status["payload"]

        redis = await redis_client.get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(inbox_channel(token))
        try:
            # Handle race between initial status check and subscription.
            status_after_subscribe = await inbox_status(token)
            if status_after_subscribe.get("received") and status_after_subscribe.get(
                "payload"
            ) is not None:
                return status_after_subscribe["payload"]

            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if isinstance(data, str) and data:
                    return json.loads(data)
        finally:
            await pubsub.unsubscribe(inbox_channel(token))
            await pubsub.aclose()

    return await asyncio.wait_for(_wait(), timeout=timeout)

