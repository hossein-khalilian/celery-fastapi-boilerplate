"""Redis-backed webhook inbox storage for polling/SSE delivery."""

from __future__ import annotations

import json
from uuid import uuid4

from app.utils import redis_client

_INBOX_KEY_PREFIX = "webhook:inbox:"
_INBOX_CHANNEL_PREFIX = "webhook:inbox:events:"


def _inbox_key(token: str) -> str:
    return f"{_INBOX_KEY_PREFIX}{token}"


def inbox_channel(token: str) -> str:
    return f"{_INBOX_CHANNEL_PREFIX}{token}"


async def create_inbox_token() -> str:
    token = str(uuid4())
    await reserve_inbox_token(token)
    return token


async def reserve_inbox_token(token: str) -> None:
    redis = await redis_client.get_redis()
    await redis.hset(
        _inbox_key(token),
        mapping={"received": "0", "payload": ""},
    )


async def inbox_token_exists(token: str) -> bool:
    redis = await redis_client.get_redis()
    return bool(await redis.exists(_inbox_key(token)))


async def store_delivery(token: str, payload: dict) -> bool:
    if not await inbox_token_exists(token):
        return False
    redis = await redis_client.get_redis()
    await redis.hset(
        _inbox_key(token),
        mapping={"received": "1", "payload": json.dumps(payload, separators=(",", ":"))},
    )
    return True


async def publish_delivery_event(token: str, payload: dict) -> None:
    redis = await redis_client.get_redis()
    await redis.publish(
        inbox_channel(token),
        json.dumps(payload, separators=(",", ":")),
    )


async def inbox_status(token: str) -> dict:
    if not await inbox_token_exists(token):
        return {"exists": False, "received": False}
    redis = await redis_client.get_redis()
    payload_raw = await redis.hget(_inbox_key(token), "payload")
    received_raw = await redis.hget(_inbox_key(token), "received")
    received = received_raw == "1"
    payload = json.loads(payload_raw) if payload_raw else None
    return {"exists": True, "received": received, "payload": payload}

