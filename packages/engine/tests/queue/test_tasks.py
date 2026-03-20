"""Tests for Celery task definitions."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.queue.tasks import dispatch_webhook, run_preflight


class TestRunPreflightTask:
    def test_task_is_registered(self) -> None:
        assert run_preflight.name == "grounded.preflight.run"

    def test_task_max_retries(self) -> None:
        assert run_preflight.max_retries == 2

    def test_task_time_limit(self) -> None:
        assert run_preflight.time_limit == 300

    def test_task_soft_time_limit(self) -> None:
        assert run_preflight.soft_time_limit == 270


class TestDispatchWebhookTask:
    def test_task_is_registered(self) -> None:
        assert dispatch_webhook.name == "grounded.webhook.dispatch"

    def test_task_max_retries(self) -> None:
        assert dispatch_webhook.max_retries == 3
