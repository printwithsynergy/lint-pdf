"""Tests for the trial (/api/v1/trial/*) and trial admin endpoints.

Covers:
- The auto-submit env gate (LINTPDF_TRIAL_AUTO_SUBMIT) on /api/v1/trial/submit
- The shared _queue_preflight_for_file helper used by both auto-submit and the
  admin manual trigger
- The GET /api/v1/admin/trials/config endpoint that exposes the flag to the UI
"""

from __future__ import annotations

import uuid
from io import BytesIO
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from lintpdf.api.models import (
    Job,
    JobStatus,
    TrialFile,
    TrialSubmission,
    TrialSubmissionStatus,
)
from lintpdf.api.routes.trial import _queue_preflight_for_file

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


ADMIN_KEY = "test-trial-admin-key"
TRIAL_SECRET = "test-trial-secret"


@pytest.fixture(autouse=True)
def _set_trial_env(monkeypatch):
    """Seed admin key and trial secret for all tests in this module."""
    monkeypatch.setenv("LINTPDF_ADMIN_API_KEY", ADMIN_KEY)
    monkeypatch.setenv("LINTPDF_TRIAL_SECRET", TRIAL_SECRET)


def _seed_submission_with_file(
    db: Session, *, file_bytes: bytes = b"%PDF-1.4\n%fake"
) -> tuple[TrialSubmission, TrialFile]:
    """Insert a PENDING submission + one trial file into the in-memory DB.

    The file is also written to InMemoryStorage so that
    _queue_preflight_for_file can download it.
    """
    from lintpdf.api.storage import get_storage

    submission_id = uuid.uuid4()
    file_id = uuid.uuid4()
    file_key = f"trial/{submission_id}/{file_id}.pdf"

    # Write directly into InMemoryStorage so storage.download_pdf() can find it.
    storage = get_storage()
    storage._files[file_key] = file_bytes  # type: ignore[attr-defined]

    submission = TrialSubmission(
        id=submission_id,
        name="Test User",
        email="test@example.com",
        company="Acme",
        phone=None,
        file_count=1,
        status=TrialSubmissionStatus.PENDING,
    )
    trial_file = TrialFile(
        id=file_id,
        submission_id=submission_id,
        file_name="fixture.pdf",
        file_size=len(file_bytes),
        file_key=file_key,
        scan_clean=True,
    )
    db.add(submission)
    db.add(trial_file)
    db.commit()
    db.refresh(submission)
    db.refresh(trial_file)
    return submission, trial_file


# ---------------------------------------------------------------------------
# _queue_preflight_for_file helper
# ---------------------------------------------------------------------------


class TestQueuePreflightHelper:
    """The shared helper used by both admin trigger and auto-submit."""

    @staticmethod
    async def test_creates_job_and_queues_task(db_session: Session) -> None:
        submission, trial_file = _seed_submission_with_file(db_session)

        # run_preflight.apply_async is auto-mocked by conftest._mock_celery_delay
        from lintpdf.queue import tasks

        tasks.run_preflight.apply_async.reset_mock()
        job_id = await _queue_preflight_for_file(
            db_session, submission, trial_file, "lintpdf-default"
        )
        db_session.commit()

        # A Job row should exist
        job = db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None
        assert job.status == JobStatus.PENDING
        assert job.profile_id == "lintpdf-default"
        assert job.file_name == "fixture.pdf"

        # TrialFile should now point at the job
        db_session.refresh(trial_file)
        assert trial_file.job_id == job_id

        # Submission should have flipped to PROCESSING
        db_session.refresh(submission)
        assert submission.status == TrialSubmissionStatus.PROCESSING

        # Celery task queued exactly once
        assert tasks.run_preflight.apply_async.call_count == 1
        call_args = tasks.run_preflight.apply_async.call_args
        assert call_args.kwargs["queue"] == "default"
        assert call_args.kwargs["args"][0] == str(job_id)
        assert call_args.kwargs["args"][1] == "lintpdf-default"


# ---------------------------------------------------------------------------
# GET /api/v1/admin/trials/config
# ---------------------------------------------------------------------------


class TestAdminTrialsConfigEndpoint:
    """The config endpoint that exposes the auto-submit flag to the admin UI."""

    @staticmethod
    def test_returns_flag_when_off(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LINTPDF_TRIAL_AUTO_SUBMIT", "false")
        resp = client.get(
            "/api/v1/admin/trials/config",
            headers={"X-Admin-Key": ADMIN_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["auto_submit"] is False
        assert data["auto_submit_profile_id"] == "lintpdf-default"

    @staticmethod
    def test_returns_flag_when_on(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LINTPDF_TRIAL_AUTO_SUBMIT", "true")
        monkeypatch.setenv("LINTPDF_TRIAL_AUTO_SUBMIT_PROFILE_ID", "lintpdf-print-ready")
        resp = client.get(
            "/api/v1/admin/trials/config",
            headers={"X-Admin-Key": ADMIN_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["auto_submit"] is True
        assert data["auto_submit_profile_id"] == "lintpdf-print-ready"

    @staticmethod
    def test_requires_admin_key(client: TestClient) -> None:
        resp = client.get("/api/v1/admin/trials/config")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/trial/submit — auto-submit env gate
# ---------------------------------------------------------------------------


def _mock_s3_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch InMemoryStorage._get_client so trial submit's direct S3 calls work.

    The trial submit handler stores files under a custom key path by
    reaching through ``storage._get_client()`` — previously a ``put_object``
    call (pre-streaming), now ``upload_fileobj`` (post bulk-files step 1
    streaming upload rewrite). We stub both on the fake client so the
    bytes land in ``InMemoryStorage._files`` and downstream
    ``download_pdf`` resolves the same key.
    """
    from lintpdf.api.storage import get_storage

    storage = get_storage()

    def put_object(Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:  # noqa: N803
        storage._files[Key] = Body  # type: ignore[attr-defined]

    def upload_fileobj(
        Fileobj: Any,  # noqa: N803
        Bucket: str,  # noqa: N803
        Key: str,  # noqa: N803
        ExtraArgs: dict[str, Any] | None = None,  # noqa: N803
    ) -> None:
        Fileobj.seek(0)
        storage._files[Key] = Fileobj.read()  # type: ignore[attr-defined]

    fake_client = MagicMock()
    fake_client.put_object.side_effect = put_object
    fake_client.upload_fileobj.side_effect = upload_fileobj
    monkeypatch.setattr(storage, "_get_client", lambda: fake_client)


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


class TestSubmitTrialAutoSubmitGate:
    """LINTPDF_TRIAL_AUTO_SUBMIT controls whether preflight is auto-queued."""

    @staticmethod
    def _submit(client: TestClient):
        return client.post(
            "/api/v1/trial/submit",
            headers={"X-Trial-Secret": TRIAL_SECRET},
            data={
                "name": "Quincy",
                "email": "quincy@example.com",
                "company": "Acme",
                "phone": "",
            },
            files={"files": ("fixture.pdf", BytesIO(MINIMAL_PDF), "application/pdf")},
        )

    def test_submit_pending_when_auto_submit_off(
        self,
        client: TestClient,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("LINTPDF_TRIAL_AUTO_SUBMIT", "false")
        _mock_s3_storage(monkeypatch)

        from lintpdf.queue import tasks

        tasks.run_preflight.apply_async.reset_mock()
        resp = self._submit(client)
        assert resp.status_code == 201, resp.text

        submission = (
            db_session.query(TrialSubmission)
            .filter(TrialSubmission.email == "quincy@example.com")
            .first()
        )
        assert submission is not None
        assert submission.status == TrialSubmissionStatus.PENDING

        # No preflight task should have been queued
        assert tasks.run_preflight.apply_async.call_count == 0

    def test_submit_processing_when_auto_submit_on(
        self,
        client: TestClient,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("LINTPDF_TRIAL_AUTO_SUBMIT", "true")
        _mock_s3_storage(monkeypatch)

        from lintpdf.queue import tasks

        tasks.run_preflight.apply_async.reset_mock()
        resp = self._submit(client)
        assert resp.status_code == 201, resp.text

        submission = (
            db_session.query(TrialSubmission)
            .filter(TrialSubmission.email == "quincy@example.com")
            .first()
        )
        assert submission is not None
        assert submission.status == TrialSubmissionStatus.PROCESSING

        # Exactly one preflight task queued (one file in the fixture)
        assert tasks.run_preflight.apply_async.call_count == 1

        # The trial file should now point at a Job row
        trial_file = (
            db_session.query(TrialFile).filter(TrialFile.submission_id == submission.id).first()
        )
        assert trial_file is not None
        assert trial_file.job_id is not None
        job = db_session.query(Job).filter(Job.id == trial_file.job_id).first()
        assert job is not None
        assert job.status == JobStatus.PENDING

    def test_submit_succeeds_even_if_auto_queue_raises(
        self,
        client: TestClient,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If the Celery dispatch explodes, the submission must still be saved."""
        monkeypatch.setenv("LINTPDF_TRIAL_AUTO_SUBMIT", "true")
        _mock_s3_storage(monkeypatch)

        from lintpdf.queue import tasks

        tasks.run_preflight.apply_async.reset_mock()
        tasks.run_preflight.apply_async.side_effect = RuntimeError("broker down")

        try:
            resp = self._submit(client)
            assert resp.status_code == 201, resp.text

            submission = (
                db_session.query(TrialSubmission)
                .filter(TrialSubmission.email == "quincy@example.com")
                .first()
            )
            assert submission is not None
            # Status should NOT flip because the helper raised before flipping it
            # (or did flip but the rollback path leaves it PENDING — either way
            # the submission row is saved, which is what we need to assert).
            assert submission.status in (
                TrialSubmissionStatus.PENDING,
                TrialSubmissionStatus.PROCESSING,
            )
        finally:
            tasks.run_preflight.apply_async.side_effect = None
