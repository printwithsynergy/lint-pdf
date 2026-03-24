"""Integration tests for the run_preflight task pipeline."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lintpdf.api.models import Base, Job, JobFinding, JobStatus, Tenant, TenantPlan
from lintpdf.api.storage import InMemoryStorage
from lintpdf.queue.tasks import run_preflight

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")
TEST_WEBHOOK_SECRET = "test-webhook-secret"

# Minimal valid PDF bytes
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
    b"/MediaBox [0 0 612 792] >>\nendobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
    b"startxref\n206\n%%EOF\n"
)


@dataclass
class FakeSummary:
    total_findings: int = 0
    error_count: int = 0
    warning_count: int = 0
    advisory_count: int = 0
    passed: bool = True
    page_count: int = 1
    file_size_bytes: int = 1000


@dataclass
class FakeFinding:
    inspection_id: str = "TEST-001"
    severity: Any = None
    message: str = "Test finding"
    page_num: int | None = 1
    details: dict[str, Any] | None = None
    source: str = "engine"
    category: str | None = None

    def __post_init__(self) -> None:
        if self.severity is None:
            from lintpdf.analyzers.finding import Severity

            self.severity = Severity.ADVISORY


@dataclass
class FakeResult:
    job_id: str = ""
    profile_id: str = "lintpdf-default"
    findings: list[Any] | None = None
    summary: FakeSummary | None = None
    metadata: dict[str, Any] | None = None
    duration_ms: int = 100

    def __post_init__(self) -> None:
        if self.findings is None:
            self.findings = []
        if self.summary is None:
            self.summary = FakeSummary()
        if self.metadata is None:
            self.metadata = {}


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite engine with FK enforcement."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """In-memory SQLite session for testing."""
    session_factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = session_factory()

    # Seed tenant
    tenant = Tenant(
        id=TENANT_ID,
        name="Test Tenant",
        api_key_hash="testhash_placeholder",
        plan=TenantPlan.FREE,
    )
    session.add(tenant)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(db_engine)
        db_engine.dispose()


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def job_in_db(db_session: Session) -> Job:
    """Create a pending job in the DB."""
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        tenant_id=TENANT_ID,
        status=JobStatus.PENDING,
        profile_id="lintpdf-default",
        file_key=f"uploads/{job_id}/input.pdf",
        file_name="test.pdf",
        file_size=len(MINIMAL_PDF),
    )
    db_session.add(job)
    db_session.commit()
    return job


class TestRunPreflightPipeline:
    """Test the full run_preflight task pipeline with mocked dependencies."""

    def _run_task(
        self,
        db_session: Session,
        storage: InMemoryStorage,
        job: Job,
        *,
        orchestrator_result: FakeResult | None = None,
    ) -> dict[str, Any]:
        """Run the task with patched dependencies."""
        if orchestrator_result is None:
            orchestrator_result = FakeResult(
                job_id=str(job.id),
                profile_id=job.profile_id,
            )

        # Seed the PDF in storage
        storage._files[job.file_key] = MINIMAL_PDF

        mock_orchestrator = MagicMock()
        mock_orchestrator.run.return_value = orchestrator_result

        with (
            patch("lintpdf.api.database.get_db_session", return_value=db_session),
            patch("lintpdf.api.storage.get_storage", return_value=storage),
            patch(
                "lintpdf.profiles.orchestrator.PreflightOrchestrator",
                return_value=mock_orchestrator,
            ),
        ):
            # Call directly — Celery's run() skips __call__ dispatch
            return run_preflight.run(
                str(job.id),
                job.profile_id,
                job.file_key,
            )

    def test_successful_run(
        self, db_session: Session, storage: InMemoryStorage, job_in_db: Job
    ) -> None:
        result = self._run_task(db_session, storage, job_in_db)
        assert result["status"] == "complete"
        assert result["job_id"] == str(job_in_db.id)
        assert "duration_ms" in result

    def test_job_marked_complete(
        self, db_session: Session, storage: InMemoryStorage, job_in_db: Job
    ) -> None:
        job_id = job_in_db.id
        self._run_task(db_session, storage, job_in_db)
        # Re-query since the task committed and may have detached the instance
        db_session.expire_all()
        job = db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None
        assert job.status == JobStatus.COMPLETE
        assert job.completed_at is not None
        assert job.duration_ms is not None
        assert job.result_json is not None

    def test_findings_stored(
        self, db_session: Session, storage: InMemoryStorage, job_in_db: Job
    ) -> None:
        fake_result = FakeResult(
            job_id=str(job_in_db.id),
            findings=[
                FakeFinding(),
                FakeFinding(inspection_id="TEST-002", message="Second finding"),
            ],
        )
        self._run_task(db_session, storage, job_in_db, orchestrator_result=fake_result)

        findings = db_session.query(JobFinding).filter(JobFinding.job_id == job_in_db.id).all()
        assert len(findings) == 2
        assert findings[0].inspection_id == "TEST-001"
        assert findings[1].inspection_id == "TEST-002"

    def test_results_uploaded_to_storage(
        self, db_session: Session, storage: InMemoryStorage, job_in_db: Job
    ) -> None:
        self._run_task(db_session, storage, job_in_db)
        results_key = f"{TENANT_ID}/{job_in_db.id}/results.json"
        assert results_key in storage._files

    def test_summary_stored(
        self, db_session: Session, storage: InMemoryStorage, job_in_db: Job
    ) -> None:
        job_id = job_in_db.id
        fake_result = FakeResult(
            job_id=str(job_in_db.id),
            summary=FakeSummary(
                total_findings=3, error_count=1, warning_count=1, advisory_count=1, passed=False
            ),
        )
        self._run_task(db_session, storage, job_in_db, orchestrator_result=fake_result)
        db_session.expire_all()
        job = db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None
        assert job.result_json["summary"]["total_findings"] == 3
        assert job.result_json["summary"]["passed"] is False

    @staticmethod
    def test_job_not_found(db_session: Session, storage: InMemoryStorage) -> None:
        with (
            patch("lintpdf.api.database.get_db_session", return_value=db_session),
            patch("lintpdf.api.storage.get_storage", return_value=storage),
        ):
            result = run_preflight.run(
                str(uuid.uuid4()),
                "lintpdf-default",
                "nonexistent/key",
            )
            assert result["status"] == "failed"
            assert "not found" in result["error"].lower()

    def test_failed_job_marked_in_db(
        self, db_session: Session, storage: InMemoryStorage, job_in_db: Job
    ) -> None:
        """When the orchestrator raises, job should be marked failed in DB."""
        from celery.exceptions import Retry

        job_id = job_in_db.id
        storage._files[job_in_db.file_key] = MINIMAL_PDF

        mock_orchestrator = MagicMock()
        mock_orchestrator.run.side_effect = RuntimeError("Parse error")

        with (
            patch("lintpdf.api.database.get_db_session", return_value=db_session),
            patch("lintpdf.api.storage.get_storage", return_value=storage),
            patch(
                "lintpdf.profiles.orchestrator.PreflightOrchestrator",
                return_value=mock_orchestrator,
            ),
            pytest.raises((RuntimeError, Retry)),
        ):
            run_preflight.run(
                str(job_in_db.id),
                job_in_db.profile_id,
                job_in_db.file_key,
            )

        db_session.expire_all()
        job = db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert "Parse error" in (job.error_message or "")


class TestDispatchTenantWebhooks:
    """Test webhook dispatching from task pipeline."""

    def test_webhooks_queued_on_completion(
        self, db_session: Session, storage: InMemoryStorage, job_in_db: Job
    ) -> None:
        """Verify dispatch_webhook.delay is called when webhooks exist."""
        from lintpdf.api.models import WebhookEndpoint

        db_session.add(
            WebhookEndpoint(
                id=uuid.uuid4(),
                tenant_id=TENANT_ID,
                url="https://example.com/hook",
                secret=TEST_WEBHOOK_SECRET,
                events=["job.completed"],
                is_active=True,
            )
        )
        db_session.commit()

        storage._files[job_in_db.file_key] = MINIMAL_PDF
        mock_orchestrator = MagicMock()
        mock_orchestrator.run.return_value = FakeResult(job_id=str(job_in_db.id))

        with (
            patch("lintpdf.api.database.get_db_session", return_value=db_session),
            patch("lintpdf.api.storage.get_storage", return_value=storage),
            patch(
                "lintpdf.profiles.orchestrator.PreflightOrchestrator",
                return_value=mock_orchestrator,
            ),
            patch("lintpdf.queue.tasks.dispatch_webhook") as mock_dispatch,
        ):
            run_preflight.run(
                str(job_in_db.id),
                job_in_db.profile_id,
                job_in_db.file_key,
            )

        mock_dispatch.delay.assert_called_once()
        call_kwargs = mock_dispatch.delay.call_args[1]
        assert call_kwargs["webhook_url"] == "https://example.com/hook"
        assert call_kwargs["event"] == "job.completed"

    def test_inactive_webhooks_skipped(
        self, db_session: Session, storage: InMemoryStorage, job_in_db: Job
    ) -> None:
        from lintpdf.api.models import WebhookEndpoint

        db_session.add(
            WebhookEndpoint(
                id=uuid.uuid4(),
                tenant_id=TENANT_ID,
                url="https://example.com/hook",
                secret=TEST_WEBHOOK_SECRET,
                events=["job.completed"],
                is_active=False,
            )
        )
        db_session.commit()

        storage._files[job_in_db.file_key] = MINIMAL_PDF
        mock_orchestrator = MagicMock()
        mock_orchestrator.run.return_value = FakeResult(job_id=str(job_in_db.id))

        with (
            patch("lintpdf.api.database.get_db_session", return_value=db_session),
            patch("lintpdf.api.storage.get_storage", return_value=storage),
            patch(
                "lintpdf.profiles.orchestrator.PreflightOrchestrator",
                return_value=mock_orchestrator,
            ),
            patch("lintpdf.queue.tasks.dispatch_webhook") as mock_dispatch,
        ):
            run_preflight.run(
                str(job_in_db.id),
                job_in_db.profile_id,
                job_in_db.file_key,
            )

        mock_dispatch.delay.assert_not_called()
