"""Tests for Celery worker initialization and task processing."""

from __future__ import annotations

# skipcq: PYL-R0201
import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest

from grounded.queue.app import create_celery_app


@pytest.fixture
def celery_app():
    """Create a test Celery app."""
    return create_celery_app(broker_url="memory://")


class TestCeleryAppCreation:
    """Tests for Celery app configuration."""

    def test_creates_app(self, celery_app) -> None:
        assert celery_app.main == "grounded"

    def test_json_serializer(self, celery_app) -> None:
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.accept_content == ["json"]

    def test_utc_timezone(self, celery_app) -> None:
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_task_time_limits(self, celery_app) -> None:
        assert celery_app.conf.task_time_limit == 600
        assert celery_app.conf.task_soft_time_limit == 540

    def test_worker_prefetch_one(self, celery_app) -> None:
        assert celery_app.conf.worker_prefetch_multiplier == 1

    def test_acks_late(self, celery_app) -> None:
        assert celery_app.conf.task_acks_late is True

    def test_max_tasks_per_child(self, celery_app) -> None:
        assert celery_app.conf.worker_max_tasks_per_child == 25

    def test_beat_schedule_has_cleanup(self, celery_app) -> None:
        schedule = celery_app.conf.beat_schedule
        assert "cleanup-expired-reports" in schedule
        task_conf = schedule["cleanup-expired-reports"]
        assert task_conf["task"] == "grounded.queue.tasks.cleanup_expired_reports"
        assert task_conf["schedule"] == 86400.0

    def test_broker_url_from_arg(self) -> None:
        app = create_celery_app(broker_url="redis://custom:6380/1")
        assert "redis://custom:6380/1" in str(app.conf.broker_url)


class TestWorkerInit:
    """Tests for the worker_init signal handler."""

    def test_on_worker_init_calls_init_db(self) -> None:
        """_on_worker_init should initialize the database."""
        with (
            patch("grounded.api.database.init_db") as mock_init_db,
            patch.dict("os.environ", {"GROUNDED_DATABASE_URL": "postgresql://test:5432/testdb"}),
        ):
            from grounded.queue.worker import _on_worker_init

            _on_worker_init()
            mock_init_db.assert_called_once_with("postgresql://test:5432/testdb")

    def test_on_worker_init_uses_default_url(self) -> None:
        """_on_worker_init should use default database URL if env var is not set."""
        import os

        with (
            patch("grounded.api.database.init_db") as mock_init_db,
            patch.dict("os.environ", {}, clear=True),
        ):
            os.environ.pop("GROUNDED_DATABASE_URL", None)
            from grounded.queue.worker import _on_worker_init

            _on_worker_init()
            mock_init_db.assert_called_once_with(
                "postgresql://grounded:grounded@localhost:5432/grounded"
            )

    def test_worker_module_exports_app(self) -> None:
        """The worker module should export the celery app."""
        from grounded.queue.worker import app

        assert app is not None


class TestRunPreflightTask:
    """Tests for the run_preflight Celery task."""

    def test_task_is_registered(self) -> None:
        """run_preflight should be registered as a Celery task."""
        from grounded.queue.tasks import run_preflight

        assert run_preflight.name == "grounded.preflight.run"

    def test_task_retry_config(self) -> None:
        from grounded.queue.tasks import run_preflight

        assert run_preflight.max_retries == 2
        assert run_preflight.default_retry_delay == 10

    def test_task_time_limits(self) -> None:
        from grounded.queue.tasks import run_preflight

        assert run_preflight.time_limit == 300
        assert run_preflight.soft_time_limit == 270

    def _run_preflight_fn(self, retries=0, **kwargs):
        """Call run_preflight's underlying function with a mock self context."""
        from grounded.queue.tasks import run_preflight

        # Access the actual function from the Celery task's _decorated attribute
        # or use push_request to set up request context
        run_preflight.push_request(retries=retries)
        try:
            return run_preflight.run(**kwargs)
        finally:
            run_preflight.pop_request()

    def test_job_not_found_returns_failed(self) -> None:
        """If the job is not in the DB, return a failed status."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("grounded.api.database.get_db_session", return_value=mock_db):
            result = self._run_preflight_fn(
                job_id="00000000-0000-0000-0000-000000000001",
                profile_id="grounded-default",
                file_key="uploads/test.pdf",
            )
        assert result["status"] == "failed"
        assert result["error"] == "Job not found"
        mock_db.close.assert_called_once()

    def test_successful_preflight_run(self) -> None:
        """Successful preflight should return complete status."""
        from grounded.profiles.orchestrator import PreflightResult, PreflightSummary

        mock_db = MagicMock()
        mock_job = MagicMock()
        mock_job.tenant_id = "tenant-123"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        mock_storage = MagicMock()
        mock_storage.download_pdf.return_value = b"%PDF-1.4 fake"

        mock_result = PreflightResult(
            job_id="test-job",
            profile_id="grounded-default",
            findings=[],
            summary=PreflightSummary(
                total_findings=0,
                aground_count=0,
                squall_count=0,
                advisory_count=0,
                passed=True,
                page_count=1,
                file_size_bytes=1024,
            ),
            metadata={"pdf_version": "1.4"},
            duration_ms=42,
        )

        with (
            patch("grounded.api.database.get_db_session", return_value=mock_db),
            patch("grounded.api.storage.get_storage", return_value=mock_storage),
            patch("grounded.profiles.registry.ProfileRegistry") as MockRegistry,  # noqa: N806
            patch("grounded.profiles.orchestrator.PreflightOrchestrator") as MockOrch,  # noqa: N806
            patch("grounded.queue.tasks._dispatch_tenant_webhooks"),
        ):
            MockRegistry.return_value.get.return_value = MagicMock()
            MockOrch.return_value.run.return_value = mock_result

            result = self._run_preflight_fn(
                job_id="00000000-0000-0000-0000-000000000001",
                profile_id="grounded-default",
                file_key="uploads/test.pdf",
            )

        assert result["status"] == "complete"
        assert result["profile_id"] == "grounded-default"
        assert "duration_ms" in result
        mock_db.commit.assert_called()
        mock_db.close.assert_called_once()

    def test_r2_failure_falls_back_to_redis(self) -> None:
        """When R2 download fails, task should try Redis cache."""
        from grounded.profiles.orchestrator import PreflightResult, PreflightSummary

        mock_db = MagicMock()
        mock_job = MagicMock()
        mock_job.tenant_id = "tenant-123"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        mock_storage = MagicMock()
        mock_storage.download_pdf.side_effect = Exception("R2 unreachable")

        mock_redis = MagicMock()
        mock_redis.get.return_value = b"%PDF-1.4 cached"

        mock_result = PreflightResult(
            job_id="test-job",
            profile_id="grounded-default",
            findings=[],
            summary=PreflightSummary(
                total_findings=0,
                aground_count=0,
                squall_count=0,
                advisory_count=0,
                passed=True,
                page_count=1,
                file_size_bytes=1024,
            ),
            metadata={"pdf_version": "1.4"},
            duration_ms=10,
        )

        with (
            patch("grounded.api.database.get_db_session", return_value=mock_db),
            patch("grounded.api.storage.get_storage", return_value=mock_storage),
            patch("grounded.api.middleware.get_redis_client", return_value=mock_redis),
            patch("grounded.profiles.registry.ProfileRegistry") as MockReg,  # noqa: N806
            patch("grounded.profiles.orchestrator.PreflightOrchestrator") as MockOrch,  # noqa: N806
            patch("grounded.queue.tasks._dispatch_tenant_webhooks"),
        ):
            MockReg.return_value.get.return_value = MagicMock()
            MockOrch.return_value.run.return_value = mock_result

            result = self._run_preflight_fn(
                job_id="00000000-0000-0000-0000-000000000001",
                profile_id="grounded-default",
                file_key="uploads/test.pdf",
            )

        assert result["status"] == "complete"
        mock_redis.get.assert_called_once_with("pdf_cache:uploads/test.pdf")

    def test_complete_failure_no_pdf(self) -> None:
        """When both R2 and Redis fail with max retries, return failed status."""
        mock_db = MagicMock()
        mock_job = MagicMock()
        mock_job.tenant_id = "tenant-123"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        mock_storage = MagicMock()
        mock_storage.download_pdf.side_effect = Exception("R2 down")

        with (
            patch("grounded.api.database.get_db_session", return_value=mock_db),
            patch("grounded.api.storage.get_storage", return_value=mock_storage),
            patch("grounded.api.middleware.get_redis_client", return_value=None),
        ):
            # retries=2 == max_retries, so it won't call self.retry
            result = self._run_preflight_fn(
                retries=2,
                job_id="00000000-0000-0000-0000-000000000001",
                profile_id="grounded-default",
                file_key="uploads/test.pdf",
            )

        assert result["status"] == "failed"
        assert "Cannot retrieve PDF" in result["error"]


class TestCleanupExpiredReports:
    """Tests for the cleanup_expired_reports task."""

    def test_task_is_registered(self) -> None:
        from grounded.queue.tasks import cleanup_expired_reports

        assert cleanup_expired_reports.name == "grounded.queue.tasks.cleanup_expired_reports"

    def test_cleanup_returns_count(self) -> None:
        mock_db = MagicMock()
        mock_storage = MagicMock()
        mock_service = MagicMock()
        mock_service.cleanup_expired.return_value = 7

        with (
            patch("grounded.api.database.get_db_session", return_value=mock_db),
            patch("grounded.api.storage.get_storage", return_value=mock_storage),
            patch("grounded.reports.service.ReportService", return_value=mock_service),
        ):
            from grounded.queue.tasks import cleanup_expired_reports

            result = cleanup_expired_reports()
        assert result == {"cleaned": 7}
        mock_db.close.assert_called_once()


class TestDispatchWebhook:
    """Tests for the dispatch_webhook task."""

    def test_task_is_registered(self) -> None:
        from grounded.queue.tasks import dispatch_webhook

        assert dispatch_webhook.name == "grounded.webhook.dispatch"

    def test_task_retry_config(self) -> None:
        from grounded.queue.tasks import dispatch_webhook

        assert dispatch_webhook.max_retries == 3
        assert dispatch_webhook.default_retry_delay == 5

    def test_successful_dispatch(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        with patch("httpx.post", return_value=mock_response):
            from grounded.queue.tasks import dispatch_webhook

            result = dispatch_webhook(
                webhook_url="https://example.com/webhook",
                webhook_secret="secret123",  # skipcq: SCT-A000 — test fixture
                event="job.completed",
                payload={"job_id": "123", "status": "complete"},
            )

        assert result["status"] == "delivered"
        assert result["url"] == "https://example.com/webhook"
        assert result["event"] == "job.completed"
        assert result["status_code"] == 200

    def test_dispatch_sends_hmac_signature(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        with patch("httpx.post", return_value=mock_response) as mock_post:
            from grounded.queue.tasks import dispatch_webhook

            payload = {"job_id": "123"}
            secret = "my-secret"  # skipcq: SCT-A000 — test fixture
            dispatch_webhook(
                webhook_url="https://example.com/hook",
                webhook_secret=secret,
                event="job.completed",
                payload=payload,
            )

            call_kwargs = mock_post.call_args
            headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
            assert headers["X-Grounded-Event"] == "job.completed"
            assert headers["X-Grounded-Signature"].startswith("sha256=")

            # Verify the signature is correct
            body = json.dumps(payload, sort_keys=True, default=str)
            expected_sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            assert headers["X-Grounded-Signature"] == f"sha256={expected_sig}"

    def test_dispatch_failure_returns_error(self) -> None:
        with patch("httpx.post", side_effect=Exception("Connection refused")):
            from grounded.queue.tasks import dispatch_webhook

            result = dispatch_webhook(
                webhook_url="https://example.com/webhook",
                webhook_secret="secret",  # skipcq: SCT-A000 — test fixture
                event="job.failed",
                payload={"error": "timeout"},
            )

        assert result["status"] == "failed"
        assert "Connection refused" in result["error"]


class TestDispatchTenantWebhooks:
    """Tests for the _dispatch_tenant_webhooks helper."""

    def test_dispatches_to_active_endpoints(self) -> None:
        from grounded.queue.tasks import _dispatch_tenant_webhooks

        mock_db = MagicMock()
        endpoint = MagicMock()
        endpoint.url = "https://example.com/hook"
        endpoint.secret = "secret"  # skipcq: SCT-A000 — test fixture
        endpoint.events = []  # empty = subscribe to all
        endpoint.is_active = True
        mock_db.query.return_value.filter.return_value.all.return_value = [endpoint]

        with patch("grounded.queue.tasks.dispatch_webhook") as mock_dispatch:
            _dispatch_tenant_webhooks(mock_db, "tenant-123", "job.completed", {"job_id": "abc"})
            mock_dispatch.delay.assert_called_once()

    def test_filters_by_event_type(self) -> None:
        from grounded.queue.tasks import _dispatch_tenant_webhooks

        mock_db = MagicMock()
        endpoint = MagicMock()
        endpoint.url = "https://example.com/hook"
        endpoint.secret = "secret"  # skipcq: SCT-A000 — test fixture
        endpoint.events = ["job.failed"]  # only subscribed to failures
        endpoint.is_active = True
        mock_db.query.return_value.filter.return_value.all.return_value = [endpoint]

        with patch("grounded.queue.tasks.dispatch_webhook") as mock_dispatch:
            _dispatch_tenant_webhooks(mock_db, "tenant-123", "job.completed", {"job_id": "abc"})
            mock_dispatch.delay.assert_not_called()

    def test_matching_event_dispatches(self) -> None:
        from grounded.queue.tasks import _dispatch_tenant_webhooks

        mock_db = MagicMock()
        endpoint = MagicMock()
        endpoint.url = "https://example.com/hook"
        endpoint.secret = "secret"  # skipcq: SCT-A000 — test fixture
        endpoint.events = ["job.completed", "job.failed"]
        endpoint.is_active = True
        mock_db.query.return_value.filter.return_value.all.return_value = [endpoint]

        with patch("grounded.queue.tasks.dispatch_webhook") as mock_dispatch:
            _dispatch_tenant_webhooks(mock_db, "tenant-123", "job.completed", {"job_id": "abc"})
            mock_dispatch.delay.assert_called_once()
