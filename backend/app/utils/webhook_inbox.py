"""Redis-backed inbox for webhook deliveries (worker POST → pub/sub → SSE on any API replica)."""

from __future__ import annotations

import json
from typing import Any

from app.utils import redis_client

INBOX_PREFIX = "webhook:inbox:"
PUB_PREFIX = "webhook:pub:"
_INBOX_TTL_SEC = 86400


def _inbox_key(token: str) -> str:
    return f"{INBOX_PREFIX}{token}"


def delivery_pubsub_channel(token: str) -> str:
    """Channel name for Redis PUBLISH/SUBSCRIBE for this inbox token."""
    return f"{PUB_PREFIX}{token}"


def _dump_compact(obj: dict[str, Any]) -> str:
    return json.dumps(obj, default=str, separators=(",", ":"))


async def reserve_inbox_token(token: str) -> None:
    r = await redis_client.get_redis()
    await r.set(_inbox_key(token), json.dumps(None), ex=_INBOX_TTL_SEC)


async def inbox_token_exists(token: str) -> bool:
    r = await redis_client.get_redis()
    return bool(await r.exists(_inbox_key(token)))


async def store_delivery(token: str, payload: dict[str, Any]) -> bool:
    r = await redis_client.get_redis()
    key = _inbox_key(token)
    if not await r.exists(key):
        return False
    body = _dump_compact(payload)
    await r.set(key, body, ex=_INBOX_TTL_SEC)
    await r.publish(delivery_pubsub_channel(token), body)
    return True


async def inbox_status(token: str) -> dict[str, Any]:
    r = await redis_client.get_redis()
    raw = await r.get(_inbox_key(token))
    if raw is None:
        return {"exists": False}
    if raw == "null":
        return {"exists": True, "received": False}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"exists": True, "received": False}
    return {"exists": True, "received": True, "payload": payload}
