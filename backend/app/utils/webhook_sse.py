"""SSE helpers for webhook inbox (delivery signaled via Redis pub/sub)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.utils import redis_client
from app.utils.webhook_inbox import delivery_pubsub_channel, inbox_status


def sse_chunk(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, default=str, separators=(',', ':'))}\n\n".encode(
        "utf-8"
    )


async def wait_inbox_payload(token: str, timeout: float = 3600.0) -> dict[str, Any]:
    """Return delivery payload from inbox or the next message on the token pub/sub channel."""
    st = await inbox_status(token)
    if st.get("received") and st.get("payload") is not None:
        return st["payload"]

    r = await redis_client.get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(delivery_pubsub_channel(token))
    try:
        st = await inbox_status(token)
        if st.get("received") and st.get("payload") is not None:
            return st["payload"]

        async def first_data_message() -> str:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    return msg["data"]
            raise asyncio.TimeoutError

        data = await asyncio.wait_for(first_data_message(), timeout=timeout)
        return json.loads(data)
    finally:
        await pubsub.unsubscribe(delivery_pubsub_channel(token))
        await pubsub.aclose()
