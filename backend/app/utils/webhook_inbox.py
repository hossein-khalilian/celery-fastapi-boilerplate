"""In-memory inbox for webhook deliveries (worker POST → SSE and optional GET poll)."""

from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()
# None value = reserved, worker has not POSTed yet
_inbox: dict[str, dict[str, Any] | None] = {}


def reserve_inbox_token(token: str) -> None:
    with _lock:
        _inbox[token] = None


def inbox_token_exists(token: str) -> bool:
    with _lock:
        return token in _inbox


def store_delivery(token: str, payload: dict[str, Any]) -> bool:
    with _lock:
        if token not in _inbox:
            return False
        _inbox[token] = payload
        return True


def inbox_status(token: str) -> dict[str, Any]:
    """Return whether token exists and, if so, whether payload arrived."""
    with _lock:
        if token not in _inbox:
            return {"exists": False}
        val = _inbox[token]
        if val is None:
            return {"exists": True, "received": False}
        return {"exists": True, "received": True, "payload": val}
