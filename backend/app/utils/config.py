"""Environment-backed settings for the API."""

import os


def cors_origins() -> list[str]:
    return [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]


def webhook_callback_base() -> str:
    return os.environ.get("WEBHOOK_CALLBACK_BASE", "http://backend:5000").rstrip("/")
