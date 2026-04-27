from typing import Any

from pydantic import BaseModel


class SubmitRequest(BaseModel):
    text: str


class WebhookSubmitRequest(BaseModel):
    text: str


class WebhookPayload(BaseModel):
    task_id: str
    state: str
    result: Any | None = None
    error: str | None = None
