# Webhook Queue and Worker Topology

This project uses two Celery workers with separate queues:

- `worker`: consumes `celery` queue and runs processing tasks such as `app.tasks.process_text` and `app.tasks.process_text_webhook`.
- `webhook-worker`: consumes `webhooks` queue and runs `app.tasks.deliver_webhook`.

`app.tasks.process_text_webhook` no longer performs webhook HTTP calls inline. It only runs the text pipeline, then enqueues `app.tasks.deliver_webhook` with payload fields:

- `task_id`
- `state`
- optional `result`
- optional `error`

## Why split workers

Webhook endpoints are external dependencies and can be slow or unreliable. Isolating delivery to a dedicated queue/worker prevents webhook latency and retries from blocking processing throughput.

## Local worker commands

From `backend/`:

- Processing worker (default queue only):
  - `celery -A app.celery_app worker --loglevel=info --queues=celery`
- Webhook worker:
  - `celery -A app.celery_app worker --loglevel=info --queues=webhooks`

In Docker Compose (`docker-compose.dev.yml` and `docker-compose.prod.yml`), these are provided as `worker` and `webhook-worker` services.

## Relevant environment variables

- `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`: Celery broker/result backend configuration.
- `WEBHOOK_CALLBACK_BASE`: base URL used by webhook submit flow to build inbox callback URL.
- `WEBHOOK_REDIS_URL`: Redis DB for webhook inbox/SSE state.
- `WEBHOOK_TIMEOUT_SECONDS`: HTTP timeout for webhook POST attempts.
- `WEBHOOK_MAX_RETRIES`: maximum Celery retries for transient webhook failures.
- `WEBHOOK_RETRY_BACKOFF_CAP_SECONDS`: cap for exponential retry backoff.
- `WEBHOOK_RETRY_JITTER_SECONDS`: random jitter range added to retry delay.

Webhook signatures are unchanged: when a secret is provided, delivery uses `X-Webhook-Signature: sha256=<hmac>`.
