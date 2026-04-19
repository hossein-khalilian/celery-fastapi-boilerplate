from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import health, tasks, webhooks
from app.utils.config import cors_origins

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(webhooks.router)
