from unittest.mock import patch

import pytest
import requests

from app.tasks.deliver_webhook import deliver_webhook
from app.tasks.process_text_webhook import process_text_webhook


@patch("app.tasks.process_text_webhook.deliver_webhook.delay")
@patch("app.tasks.process_text_webhook.run_text_pipeline")
def test_process_text_webhook_enqueues_success(mock_pipeline, mock_delay):
    mock_pipeline.return_value = {"ok": True}
    process_text_webhook.request.id = "task-123"

    result = process_text_webhook.run("hello", 123.0, "https://example.com/hook", "sec")

    assert result == {"ok": True}
    mock_delay.assert_called_once_with(
        "https://example.com/hook",
        "sec",
        "task-123",
        "SUCCESS",
        result={"ok": True},
    )


@patch("app.tasks.process_text_webhook.deliver_webhook.delay")
@patch("app.tasks.process_text_webhook.run_text_pipeline")
def test_process_text_webhook_enqueues_failure(mock_pipeline, mock_delay):
    process_text_webhook.request.id = "task-fail"
    mock_pipeline.side_effect = ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        process_text_webhook.run("hello", 123.0, "https://example.com/hook", "sec")

    mock_delay.assert_called_once_with(
        "https://example.com/hook",
        "sec",
        "task-fail",
        "FAILURE",
        error="boom",
    )


@patch("app.tasks.deliver_webhook.send_webhook")
def test_deliver_webhook_task_forwards_payload(mock_deliver):
    deliver_webhook.run(
        "https://example.com/hook",
        "secret",
        "task-1",
        "SUCCESS",
        result={"value": 1},
    )

    mock_deliver.assert_called_once_with(
        "https://example.com/hook",
        "secret",
        "task-1",
        "SUCCESS",
        result={"value": 1},
        error=None,
        raise_on_failure=True,
    )


@patch("app.tasks.deliver_webhook.webhook_retry_jitter_seconds", return_value=0)
@patch("app.tasks.deliver_webhook.random.randint", return_value=0)
@patch("app.tasks.deliver_webhook.send_webhook")
def test_deliver_webhook_task_retries_transient_error(
    mock_deliver, _mock_randint, _mock_jitter
):
    exc = requests.Timeout("timed out")
    mock_deliver.side_effect = exc
    with patch.object(
        deliver_webhook, "retry", side_effect=RuntimeError("retry-triggered")
    ) as mock_retry:
        with pytest.raises(RuntimeError, match="retry-triggered"):
            deliver_webhook.run(
                "https://example.com/hook",
                "secret",
                "task-2",
                "FAILURE",
                error="boom",
            )

    mock_retry.assert_called_once_with(exc=exc, countdown=1)
