from typing import Any

from pydantic import BaseModel, HttpUrl


class SubmitRequest(BaseModel):
    text: str


class WebhookSubmitRequest(BaseModel):
    text: str
    webhook_url: HttpUrl
    webhook_secret: str | None = None


class WebhookPayload(BaseModel):
    task_id: str
    state: str
    result: Any | None = None
    error: str | None = None
