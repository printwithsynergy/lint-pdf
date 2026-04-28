"""Tests for Celery task definitions."""

from __future__ import annotations

from lintpdf.queue.tasks import dispatch_webhook, run_preflight


class TestRunPreflightTask:
    @staticmethod
    def test_task_is_registered() -> None:
        assert run_preflight.name == "lintpdf.preflight.run"

    @staticmethod
    def test_task_max_retries() -> None:
        assert run_preflight.max_retries == 2

    @staticmethod
    def test_task_time_limit() -> None:
        # 600s limit was raised from 300s so AI-heavy jobs have room to
        # complete when Modal is slow on cold starts.
        assert run_preflight.time_limit == 600

    @staticmethod
    def test_task_soft_time_limit() -> None:
        assert run_preflight.soft_time_limit == 540


class TestDispatchWebhookTask:
    @staticmethod
    def test_task_is_registered() -> None:
        assert dispatch_webhook.name == "lintpdf.webhook.dispatch"

    @staticmethod
    def test_task_max_retries() -> None:
        # Raised from 3 to 10 to ride out long upstream outages (see the
        # webhook retention + retry-budget work around commit 9634390).
        assert dispatch_webhook.max_retries == 10
