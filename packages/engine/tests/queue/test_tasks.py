"""Tests for Celery task definitions."""

from __future__ import annotations

from grounded.queue.tasks import dispatch_webhook, run_preflight


class TestRunPreflightTask:
    @staticmethod
    def test_task_is_registered() -> None:
        assert run_preflight.name == "grounded.preflight.run"

    @staticmethod
    def test_task_max_retries() -> None:
        assert run_preflight.max_retries == 2

    @staticmethod
    def test_task_time_limit() -> None:
        assert run_preflight.time_limit == 300

    @staticmethod
    def test_task_soft_time_limit() -> None:
        assert run_preflight.soft_time_limit == 270


class TestDispatchWebhookTask:
    @staticmethod
    def test_task_is_registered() -> None:
        assert dispatch_webhook.name == "grounded.webhook.dispatch"

    @staticmethod
    def test_task_max_retries() -> None:
        assert dispatch_webhook.max_retries == 3
