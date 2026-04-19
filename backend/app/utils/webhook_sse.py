"""SSE subscribers for webhook inbox deliveries (backend → browser)."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

_lock = asyncio.Lock()
_waiters: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)


async def register_waiter(token: str) -> asyncio.Queue[dict[str, Any]]:
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1)
    async with _lock:
        _waiters[token].append(q)
    return q


async def unregister_waiter(token: str, q: asyncio.Queue[dict[str, Any]]) -> None:
    async with _lock:
        lst = _waiters.get(token)
        if not lst:
            return
        try:
            lst.remove(q)
        except ValueError:
            return
        if not lst:
            del _waiters[token]


async def publish_delivery(token: str, payload: dict[str, Any]) -> None:
    async with _lock:
        queues = list(_waiters.get(token, ()))
    for q in queues:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass


def sse_chunk(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, default=str, separators=(',', ':'))}\n\n".encode(
        "utf-8"
    )
