from pydantic import BaseModel


class SubmitRequest(BaseModel):
    text: str


class WebhookSubmitRequest(BaseModel):
    text: str
