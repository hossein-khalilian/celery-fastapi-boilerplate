"""Isolate webhook Redis usage so tests do not require a live Redis server."""

import pytest
import fakeredis.aioredis


@pytest.fixture(autouse=True)
def _fake_webhook_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)

    async def get_redis():
        return fake

    monkeypatch.setattr("app.utils.redis_client.get_redis", get_redis)
