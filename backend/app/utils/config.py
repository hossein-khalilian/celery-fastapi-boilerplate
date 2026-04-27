"""Environment-backed settings for the API."""

import os


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def cors_origins() -> list[str]:
    return [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]


def webhook_callback_base() -> str:
    return os.environ.get("WEBHOOK_CALLBACK_BASE", "http://backend:5000").rstrip("/")


def webhook_timeout_seconds() -> int:
    return _int_env("WEBHOOK_TIMEOUT_SECONDS", 10)


def webhook_max_retries() -> int:
    return _int_env("WEBHOOK_MAX_RETRIES", 5)


def webhook_retry_backoff_cap_seconds() -> int:
    return _int_env("WEBHOOK_RETRY_BACKOFF_CAP_SECONDS", 60)


def webhook_retry_jitter_seconds() -> int:
    return _int_env("WEBHOOK_RETRY_JITTER_SECONDS", 3)
