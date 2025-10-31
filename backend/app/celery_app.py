import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
BACKEND_URL = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "worker",
    broker=BROKER_URL,
    backend=BACKEND_URL,
)

celery_app.conf.update(task_track_started=True)

# Ensure tasks are imported so they are registered with the Celery app when the
# module is loaded (required for workers started with -A celery_app.celery).
try:
    import tasks  # noqa: F401 (register tasks)
except Exception:
    # best-effort import; worker will raise if tasks are missing
    pass
