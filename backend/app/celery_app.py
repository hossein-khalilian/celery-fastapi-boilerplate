import os
from pathlib import Path

from celery import Celery
from dotenv import load_dotenv

# backend/.env when running locally (Docker also injects env via env_file)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
BACKEND_URL = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "worker",
    broker=BROKER_URL,
    backend=BACKEND_URL,
    include=["app.tasks.process_text", "app.tasks.process_text_webhook"],
)

celery_app.conf.update(task_track_started=True)
