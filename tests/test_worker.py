"""Tests for Celery worker initialization and task processing."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest

from lintpdf.queue.app import create_celery_app

TEST_SECRET = "test-webhook-secret"


@pytest.fixture
def celery_app():
    """Create a test Celery app."""
    return create_celery_app(broker_url="memory://")


class TestCeleryAppCreation:
    """Tests for Celery app configuration."""

    @staticmethod
    def test_creates_app(celery_app) -> None:
        assert celery_app.main == "lintpdf"

    @staticmethod
    def test_json_serializer(celery_app) -> None:
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.accept_content == ["json"]

    @staticmethod
    def test_utc_timezone(celery_app) -> None:
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    @staticmethod
    def test_task_time_limits(celery_app) -> None:
        assert celery_app.conf.task_time_limit == 600
        assert celery_app.conf.task_soft_time_limit == 540

    @staticmethod
    def test_worker_prefetch_one(celery_app) -> None:
        assert celery_app.conf.worker_prefetch_multiplier == 1

    @staticmethod
    def test_acks_late(celery_app) -> None:
        assert celery_app.conf.task_acks_late is True

    @staticmethod
    def test_max_tasks_per_child(celery_app) -> None:
        # Recycle workers after each task to bound memory growth — the
        # OCR / image pipelines hold on to large pikepdf + Pillow buffers
        # that don't fully release between calls. ``1`` matches the value
        # used by the Railway production worker rollout.
        assert celery_app.conf.worker_max_tasks_per_child == 1

    @staticmethod
    def test_beat_schedule_has_cleanup(celery_app) -> None:
        schedule = celery_app.conf.beat_schedule
        assert "cleanup-expired-reports" in schedule
        task_conf = schedule["cleanup-expired-reports"]
        assert task_conf["task"] == "lintpdf.queue.tasks.cleanup_expired_reports"
        assert task_conf["schedule"] == 86400.0

    @staticmethod
    def test_broker_url_from_arg() -> None:
        app = create_celery_app(broker_url="redis://custom:6380/1")
        assert "redis://custom:6380/1" in str(app.conf.broker_url)


class TestWorkerInit:
    """Tests for the worker_init signal handler."""

    @staticmethod
    def test_on_worker_init_calls_init_db() -> None:
        """_on_worker_init should initialize the database."""
        with (
            patch("lintpdf.api.database.init_db") as mock_init_db,
            patch.dict("os.environ", {"LINTPDF_DATABASE_URL": "postgresql://test:5432/testdb"}),
        ):
            from lintpdf.queue.worker import _on_worker_init

            _on_worker_init()
            mock_init_db.assert_called_once_with("postgresql://test:5432/testdb")

    @staticmethod
    def test_on_worker_init_raises_without_url() -> None:
        """_on_worker_init should raise if LINTPDF_DATABASE_URL is not set."""
        import os

        with (
            patch.dict("os.environ", {}, clear=True),
        ):
            os.environ.pop("LINTPDF_DATABASE_URL", None)
            from lintpdf.queue.worker import _on_worker_init

            with pytest.raises(RuntimeError, match="LINTPDF_DATABASE_URL"):
                _on_worker_init()

    @staticmethod
    def test_worker_module_exports_app() -> None:
        """The worker module should export the celery app."""
        from lintpdf.queue.worker import app

        assert app is not None

    @staticmethod
    def test_reset_db_state_drops_engine() -> None:
        """``reset_db_state`` must null out the cached engine + session factory.

        Regression guard for the 2026-04-22 prod stall: without this reset
        inside ``worker_process_init``, each forked Celery worker
        inherits the parent's psycopg2 sockets and silently dies on its
        first query (no Soft/Hard TimeLimit — just missing heartbeats).
        """
        from unittest.mock import MagicMock, patch

        from lintpdf.api import database as db_module

        # Swap the real engine out for a MagicMock; ``init_db`` uses
        # Postgres-only pool kwargs that SQLite's SingletonThreadPool
        # rejects, so we mock at the create_engine layer instead of
        # pointing at a real URL.
        fake_engine = MagicMock()
        with patch("lintpdf.api.database.create_engine", return_value=fake_engine):
            db_module.reset_db_state()  # start clean
            db_module.init_db("postgresql://fake@host/db")
            assert db_module._db_state["engine"] is fake_engine
            assert db_module._db_state["session_local"] is not None

            db_module.reset_db_state()
            assert db_module._db_state["engine"] is None
            assert db_module._db_state["session_local"] is None

        # ``dispose(close=False)`` is the critical call — ``close=True``
        # would shut down sockets shared with the parent process.
        fake_engine.dispose.assert_called_once_with(close=False)

    @staticmethod
    def test_worker_process_init_hook_resets_db_state() -> None:
        """The Celery worker-fork signal handler must call reset_db_state."""
        from unittest.mock import patch

        from lintpdf.queue.app import _configure_worker_process

        with (
            patch("lintpdf.api.database.reset_db_state") as mock_reset,
            patch("lintpdf.api.logging_config.configure_logging") as mock_log,
        ):
            _configure_worker_process()
            mock_log.assert_called_once()
            mock_reset.assert_called_once()


class TestRunPreflightTask:
    """Tests for the run_preflight Celery task."""

    @staticmethod
    def test_task_is_registered() -> None:
        """run_preflight should be registered as a Celery task."""
        from lintpdf.queue.tasks import run_preflight

        assert run_preflight.name == "lintpdf.preflight.run"

    @staticmethod
    def test_task_retry_config() -> None:
        from lintpdf.queue.tasks import run_preflight

        assert run_preflight.max_retries == 2
        assert run_preflight.default_retry_delay == 10

    @staticmethod
    def test_task_time_limits() -> None:
        from lintpdf.queue.tasks import run_preflight

        # Hard limit 600s / soft limit 540s — gives the analyzer chain
        # enough headroom for large packaging artwork PDFs while still
        # catching genuinely-stuck jobs. Soft fires first so the task
        # marks the job FAILED gracefully before Celery sends SIGKILL.
        assert run_preflight.time_limit == 600
        assert run_preflight.soft_time_limit == 540

    def _run_preflight_fn(self, retries=0, **kwargs):
        """Call run_preflight's underlying function with a mock self context."""
        from lintpdf.queue.tasks import run_preflight

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

        with patch("lintpdf.api.database.get_db_session", return_value=mock_db):
            result = self._run_preflight_fn(
                job_id="00000000-0000-0000-0000-000000000001",
                profile_id="lintpdf-default",
                file_key="uploads/test.pdf",
            )
        assert result["status"] == "failed"
        assert result["error"] == "Job not found"
        mock_db.close.assert_called_once()

    def test_successful_preflight_run(self) -> None:
        """Successful preflight should return complete status."""
        import contextlib

        from lintpdf.profiles.orchestrator import PreflightResult, PreflightSummary

        mock_db = MagicMock()
        mock_job = MagicMock()
        mock_job.tenant_id = "tenant-123"
        # Avoid OverridesEnvelope.model_validate(MagicMock) blowing up on
        # the override-application path — set to None so the branch skips.
        mock_job.overrides = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        mock_storage = MagicMock()
        mock_storage.download_pdf.return_value = b"%PDF-1.4 fake"

        mock_result = PreflightResult(
            job_id="test-job",
            profile_id="lintpdf-default",
            findings=[],
            summary=PreflightSummary(
                total_findings=0,
                error_count=0,
                warning_count=0,
                advisory_count=0,
                passed=True,
                page_count=1,
                file_size_bytes=1024,
            ),
            metadata={"pdf_version": "1.4"},
            duration_ms=42,
        )

        @contextlib.contextmanager
        def _fake_icc_resolver(*_a, **_kw):
            # No ICC profile path — orchestrator handles None gracefully.
            yield None

        with (
            patch("lintpdf.api.database.get_db_session", return_value=mock_db),
            patch("lintpdf.api.storage.get_storage", return_value=mock_storage),
            patch("lintpdf.profiles.registry.ProfileRegistry") as MockRegistry,  # noqa: N806
            patch("lintpdf.profiles.orchestrator.PreflightOrchestrator") as MockOrch,  # noqa: N806
            patch("lintpdf.epm.icc_resolver.resolve_active_icc_profile", _fake_icc_resolver),
            patch("lintpdf.queue.tasks._dispatch_tenant_webhooks"),
        ):
            MockRegistry.return_value.get.return_value = MagicMock()
            MockOrch.return_value.run.return_value = mock_result

            result = self._run_preflight_fn(
                job_id="00000000-0000-0000-0000-000000000001",
                profile_id="lintpdf-default",
                file_key="uploads/test.pdf",
            )

        assert result["status"] == "complete"
        assert result["profile_id"] == "lintpdf-default"
        assert "duration_ms" in result
        mock_db.commit.assert_called()
        mock_db.close.assert_called_once()

    def test_r2_failure_falls_back_to_redis(self) -> None:
        """When R2 download fails, task should try Redis cache."""
        import contextlib

        from lintpdf.profiles.orchestrator import PreflightResult, PreflightSummary

        mock_db = MagicMock()
        mock_job = MagicMock()
        mock_job.tenant_id = "tenant-123"
        mock_job.overrides = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        mock_storage = MagicMock()
        mock_storage.download_pdf.side_effect = Exception("R2 unreachable")

        mock_redis = MagicMock()
        mock_redis.get.return_value = b"%PDF-1.4 cached"

        mock_result = PreflightResult(
            job_id="test-job",
            profile_id="lintpdf-default",
            findings=[],
            summary=PreflightSummary(
                total_findings=0,
                error_count=0,
                warning_count=0,
                advisory_count=0,
                passed=True,
                page_count=1,
                file_size_bytes=1024,
            ),
            metadata={"pdf_version": "1.4"},
            duration_ms=10,
        )

        @contextlib.contextmanager
        def _fake_icc_resolver(*_a, **_kw):
            yield None

        with (
            patch("lintpdf.api.database.get_db_session", return_value=mock_db),
            patch("lintpdf.api.storage.get_storage", return_value=mock_storage),
            patch("lintpdf.api.middleware.get_redis_client", return_value=mock_redis),
            patch("lintpdf.profiles.registry.ProfileRegistry") as MockReg,  # noqa: N806
            patch("lintpdf.profiles.orchestrator.PreflightOrchestrator") as MockOrch,  # noqa: N806
            patch("lintpdf.epm.icc_resolver.resolve_active_icc_profile", _fake_icc_resolver),
            patch("lintpdf.queue.tasks._dispatch_tenant_webhooks"),
        ):
            MockReg.return_value.get.return_value = MagicMock()
            MockOrch.return_value.run.return_value = mock_result

            result = self._run_preflight_fn(
                job_id="00000000-0000-0000-0000-000000000001",
                profile_id="lintpdf-default",
                file_key="uploads/test.pdf",
            )

        assert result["status"] == "complete"
        mock_redis.get.assert_any_call("pdf_cache:uploads/test.pdf")

    def test_complete_failure_no_pdf(self) -> None:
        """When both R2 and Redis fail with max retries, return failed status."""
        mock_db = MagicMock()
        mock_job = MagicMock()
        mock_job.tenant_id = "tenant-123"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job

        mock_storage = MagicMock()
        mock_storage.download_pdf.side_effect = Exception("R2 down")

        with (
            patch("lintpdf.api.database.get_db_session", return_value=mock_db),
            patch("lintpdf.api.storage.get_storage", return_value=mock_storage),
            patch("lintpdf.api.middleware.get_redis_client", return_value=None),
        ):
            # retries=2 == max_retries, so it won't call self.retry
            result = self._run_preflight_fn(
                retries=2,
                job_id="00000000-0000-0000-0000-000000000001",
                profile_id="lintpdf-default",
                file_key="uploads/test.pdf",
            )

        assert result["status"] == "failed"
        assert "Cannot retrieve PDF" in result["error"]


class TestCleanupExpiredReports:
    """Tests for the cleanup_expired_reports task."""

    @staticmethod
    def test_task_is_registered() -> None:
        from lintpdf.queue.tasks import cleanup_expired_reports

        assert cleanup_expired_reports.name == "lintpdf.queue.tasks.cleanup_expired_reports"

    @staticmethod
    def test_cleanup_returns_count() -> None:
        mock_db = MagicMock()
        mock_storage = MagicMock()
        mock_service = MagicMock()
        mock_service.cleanup_expired.return_value = 7

        with (
            patch("lintpdf.api.database.get_db_session", return_value=mock_db),
            patch("lintpdf.api.storage.get_storage", return_value=mock_storage),
            patch("lintpdf.reports.service.ReportService", return_value=mock_service),
        ):
            from lintpdf.queue.tasks import cleanup_expired_reports

            result = cleanup_expired_reports()
        assert result == {"cleaned": 7}
        mock_db.close.assert_called_once()


class TestDispatchWebhook:
    """Tests for the dispatch_webhook task."""

    @staticmethod
    def test_task_is_registered() -> None:
        from lintpdf.queue.tasks import dispatch_webhook

        assert dispatch_webhook.name == "lintpdf.webhook.dispatch"

    @staticmethod
    def test_task_retry_config() -> None:
        from lintpdf.queue.tasks import _RETRY_CEILING, dispatch_webhook

        # ``max_retries`` matches the hard ceiling (10) — per-endpoint
        # ``WebhookEndpoint.max_retries`` overrides are clamped against
        # this in ``min(endpoint.max_retries, _RETRY_CEILING)``. Default
        # retry delay is 5s; the in-task exponential backoff overrides.
        assert dispatch_webhook.max_retries == _RETRY_CEILING
        assert dispatch_webhook.default_retry_delay == 5

    @staticmethod
    def test_successful_dispatch() -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        with patch("httpx.post", return_value=mock_response):
            from lintpdf.queue.tasks import dispatch_webhook

            result = dispatch_webhook(
                webhook_url="https://example.com/webhook",
                webhook_secret=TEST_SECRET,
                event="job.completed",
                payload={"job_id": "123", "status": "complete"},
            )

        assert result["status"] == "delivered"
        assert result["url"] == "https://example.com/webhook"
        assert result["event"] == "job.completed"
        assert result["status_code"] == 200

    @staticmethod
    def test_dispatch_sends_hmac_signature() -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        with patch("httpx.post", return_value=mock_response) as mock_post:
            from lintpdf.queue.tasks import dispatch_webhook

            payload = {"job_id": "123"}
            secret = TEST_SECRET
            dispatch_webhook(
                webhook_url="https://example.com/hook",
                webhook_secret=secret,
                event="job.completed",
                payload=payload,
            )

            call_kwargs = mock_post.call_args
            headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
            assert headers["X-LintPDF-Event"] == "job.completed"
            assert headers["X-LintPDF-Signature"].startswith("sha256=")

            # Verify the signature is correct
            body = json.dumps(payload, sort_keys=True, default=str)
            expected_sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            assert headers["X-LintPDF-Signature"] == f"sha256={expected_sig}"

    @staticmethod
    def test_dispatch_failure_returns_error() -> None:
        # Stub ``self.retry`` to immediately raise ``MaxRetriesExceededError``
        # so the dispatcher falls through to its terminal failed-return
        # path. Without the stub, ``self.retry()`` raises a ``Retry``
        # exception that Celery's worker would catch — but we're calling
        # the task synchronously outside the worker.
        from celery.exceptions import MaxRetriesExceededError

        from lintpdf.queue.tasks import dispatch_webhook

        with (
            patch("httpx.post", side_effect=Exception("Connection refused")),
            patch.object(dispatch_webhook, "retry", side_effect=MaxRetriesExceededError("test")),
        ):
            result = dispatch_webhook(
                webhook_url="https://example.com/webhook",
                webhook_secret=TEST_SECRET,
                event="job.failed",
                payload={"error": "timeout"},
            )

        assert result["status"] == "failed"
        assert "Connection refused" in result["error"]


class TestDispatchTenantWebhooks:
    """Tests for the _dispatch_tenant_webhooks helper."""

    @staticmethod
    def test_dispatches_to_active_endpoints() -> None:
        from lintpdf.queue.tasks import _dispatch_tenant_webhooks

        mock_db = MagicMock()
        endpoint = MagicMock()
        endpoint.url = "https://example.com/hook"
        endpoint.secret = TEST_SECRET
        endpoint.events = []  # empty = subscribe to all
        endpoint.is_active = True
        mock_db.query.return_value.filter.return_value.all.return_value = [endpoint]

        with patch("lintpdf.queue.tasks.dispatch_webhook") as mock_dispatch:
            _dispatch_tenant_webhooks(mock_db, "tenant-123", "job.completed", {"job_id": "abc"})
            mock_dispatch.delay.assert_called_once()

    @staticmethod
    def test_filters_by_event_type() -> None:
        from lintpdf.queue.tasks import _dispatch_tenant_webhooks

        mock_db = MagicMock()
        endpoint = MagicMock()
        endpoint.url = "https://example.com/hook"
        endpoint.secret = TEST_SECRET
        endpoint.events = ["job.failed"]  # only subscribed to failures
        endpoint.is_active = True
        mock_db.query.return_value.filter.return_value.all.return_value = [endpoint]

        with patch("lintpdf.queue.tasks.dispatch_webhook") as mock_dispatch:
            _dispatch_tenant_webhooks(mock_db, "tenant-123", "job.completed", {"job_id": "abc"})
            mock_dispatch.delay.assert_not_called()

    @staticmethod
    def test_matching_event_dispatches() -> None:
        from lintpdf.queue.tasks import _dispatch_tenant_webhooks

        mock_db = MagicMock()
        endpoint = MagicMock()
        endpoint.url = "https://example.com/hook"
        endpoint.secret = TEST_SECRET
        endpoint.events = ["job.completed", "job.failed"]
        endpoint.is_active = True
        mock_db.query.return_value.filter.return_value.all.return_value = [endpoint]

        with patch("lintpdf.queue.tasks.dispatch_webhook") as mock_dispatch:
            _dispatch_tenant_webhooks(mock_db, "tenant-123", "job.completed", {"job_id": "abc"})
            mock_dispatch.delay.assert_called_once()
