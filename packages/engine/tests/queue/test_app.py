"""Tests for Celery app configuration."""

from __future__ import annotations

from lintpdf.queue.app import celery_app, create_celery_app


class TestCeleryApp:
    @staticmethod
    def test_create_app_returns_celery() -> None:
        app = create_celery_app(broker_url="memory://")
        assert app.main == "lintpdf"

    @staticmethod
    def test_custom_broker() -> None:
        app = create_celery_app(broker_url="redis://localhost:6379/0")
        assert "redis://localhost:6379/0" in str(app.conf.broker_url)

    @staticmethod
    def test_custom_broker_alt() -> None:
        app = create_celery_app(broker_url="redis://custom:6380/1")
        assert "redis://custom:6380/1" in str(app.conf.broker_url)

    @staticmethod
    def test_task_serializer_json() -> None:
        assert celery_app.conf.task_serializer == "json"

    @staticmethod
    def test_time_limits() -> None:
        assert celery_app.conf.task_time_limit == 600
        assert celery_app.conf.task_soft_time_limit == 540

    @staticmethod
    def test_worker_prefetch_multiplier() -> None:
        assert celery_app.conf.worker_prefetch_multiplier == 1

    @staticmethod
    def test_task_acks_late() -> None:
        assert celery_app.conf.task_acks_late is True

    @staticmethod
    def test_utc_enabled() -> None:
        assert celery_app.conf.enable_utc is True
