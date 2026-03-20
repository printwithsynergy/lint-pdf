"""Tests for Celery app configuration."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.queue.app import celery_app, create_celery_app


class TestCeleryApp:
    def test_create_app_returns_celery(self) -> None:
        app = create_celery_app()
        assert app.main == "grounded"

    def test_default_broker(self) -> None:
        app = create_celery_app()
        assert "redis://localhost:6379/0" in str(app.conf.broker_url)

    def test_custom_broker(self) -> None:
        app = create_celery_app(broker_url="redis://custom:6380/1")
        assert "redis://custom:6380/1" in str(app.conf.broker_url)

    def test_task_serializer_json(self) -> None:
        assert celery_app.conf.task_serializer == "json"

    def test_time_limits(self) -> None:
        assert celery_app.conf.task_time_limit == 600
        assert celery_app.conf.task_soft_time_limit == 540

    def test_worker_prefetch_multiplier(self) -> None:
        assert celery_app.conf.worker_prefetch_multiplier == 1

    def test_task_acks_late(self) -> None:
        assert celery_app.conf.task_acks_late is True

    def test_utc_enabled(self) -> None:
        assert celery_app.conf.enable_utc is True
