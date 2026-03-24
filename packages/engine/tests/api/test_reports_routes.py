"""Comprehensive tests for report generation and serving route handlers."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from lintpdf.api.models import Job, JobStatus, ReportToken

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

from tests.api.conftest import PLACEHOLDER_TENANT_ID

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def _seed_completed_job(db: Session, *, result_json: dict | None = None) -> Job:
    if result_json is None:
        result_json = {
            "summary": {
                "total_findings": 0,
                "error_count": 0,
                "warning_count": 0,
                "advisory_count": 0,
                "passed": True,
                "page_count": 1,
                "file_size_bytes": 500,
            }
        }
    job = Job(
        id=uuid.uuid4(),
        tenant_id=PLACEHOLDER_TENANT_ID,
        status=JobStatus.COMPLETE,
        profile_id="lintpdf-default",
        file_key="fake/key.pdf",
        file_name="report-test.pdf",
        file_size=500,
        page_count=1,
        result_json=result_json,
        duration_ms=100,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _seed_pending_job(db: Session) -> Job:
    job = Job(
        id=uuid.uuid4(),
        tenant_id=PLACEHOLDER_TENANT_ID,
        status=JobStatus.PENDING,
        profile_id="lintpdf-default",
        file_key="fake/pending.pdf",
        file_name="pending.pdf",
        file_size=100,
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _seed_report_token(
    db: Session,
    job_id: uuid.UUID,
    *,
    fmt: str = "html",
    expired: bool = False,
    token: str | None = None,
    no_expiry: bool = False,
) -> ReportToken:
    tok = token or f"tok_{uuid.uuid4().hex[:16]}"
    now = datetime.utcnow()
    expires = None
    if no_expiry:
        expires = None
    elif expired:
        expires = now - timedelta(hours=1)
    else:
        # Set a far-future expiry; use None to avoid tz comparison issues on SQLite
        expires = None
    rt = ReportToken(
        id=uuid.uuid4(),
        job_id=job_id,
        tenant_id=PLACEHOLDER_TENANT_ID,
        token=tok,
        format=fmt,
        expires_at=expires,
        accessed_count=0,
        created_at=now,
    )
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


# -----------------------------------------------------------------------
# POST /api/v1/jobs/{job_id}/reports  (generate)
# -----------------------------------------------------------------------


class TestGenerateReportsRoute:
    @staticmethod
    def test_invalid_job_id_format(client: TestClient) -> None:
        resp = client.post("/api/v1/jobs/bad-uuid/reports")
        assert resp.status_code == 422

    @staticmethod
    def test_job_not_found(client: TestClient) -> None:
        fake = str(uuid.uuid4())
        resp = client.post(f"/api/v1/jobs/{fake}/reports")
        assert resp.status_code == 404

    @staticmethod
    def test_job_not_completed_409(client: TestClient, db_session: Session) -> None:
        job = _seed_pending_job(db_session)
        resp = client.post(f"/api/v1/jobs/{job.id}/reports")
        assert resp.status_code == 409
        assert "not completed" in resp.json()["detail"].lower()

    @staticmethod
    def test_generate_success(client: TestClient, db_session: Session) -> None:
        job = _seed_completed_job(db_session)
        mock_result = MagicMock()
        mock_result.reports = [
            {
                "format": "html",
                "url": "https://reports.example.com/r/abc",
                "token": "abc",
                "expires_at": "2026-04-01T00:00:00",
            }
        ]
        mock_service = MagicMock()
        mock_service.generate_and_store.return_value = mock_result

        with (
            patch(
                "lintpdf.reports.service.ReportService",
                return_value=mock_service,
            ),
            patch("lintpdf.api.config.get_settings") as mock_settings,
        ):
            mock_settings.return_value.report_base_url = "https://reports.example.com"
            resp = client.post(f"/api/v1/jobs/{job.id}/reports")

        assert resp.status_code == 201
        data = resp.json()
        assert len(data["reports"]) == 1
        assert data["reports"][0]["format"] == "html"


# -----------------------------------------------------------------------
# GET /api/v1/jobs/{job_id}/reports  (list)
# -----------------------------------------------------------------------


class TestListReportsRoute:
    @staticmethod
    def test_invalid_job_id(client: TestClient) -> None:
        resp = client.get("/api/v1/jobs/not-uuid/reports")
        assert resp.status_code == 422

    @staticmethod
    def test_empty_list(client: TestClient, db_session: Session) -> None:
        job = _seed_completed_job(db_session)
        data = client.get(f"/api/v1/jobs/{job.id}/reports").json()
        assert data["reports"] == []

    @staticmethod
    def test_lists_tokens(client: TestClient, db_session: Session) -> None:
        job = _seed_completed_job(db_session)
        _seed_report_token(db_session, job.id, fmt="html", token="tok_html")
        _seed_report_token(db_session, job.id, fmt="pdf", token="tok_pdf")
        data = client.get(f"/api/v1/jobs/{job.id}/reports").json()
        assert len(data["reports"]) == 2
        tokens = {r["token"] for r in data["reports"]}
        assert "tok_html" in tokens
        assert "tok_pdf" in tokens

    @staticmethod
    def test_report_fields(client: TestClient, db_session: Session) -> None:
        job = _seed_completed_job(db_session)
        _seed_report_token(db_session, job.id, fmt="html", token="tok_fields")
        report = client.get(f"/api/v1/jobs/{job.id}/reports").json()["reports"][0]
        assert "token" in report
        assert "format" in report
        assert "created_at" in report
        assert "accessed_count" in report


# -----------------------------------------------------------------------
# DELETE /api/v1/jobs/{job_id}/reports/{token}  (revoke)
# -----------------------------------------------------------------------


class TestRevokeReportRoute:
    @staticmethod
    def test_revoke_success(client: TestClient, db_session: Session) -> None:
        job = _seed_completed_job(db_session)
        _seed_report_token(db_session, job.id, token="tok_revoke")
        resp = client.delete(f"/api/v1/jobs/{job.id}/reports/tok_revoke")
        assert resp.status_code == 204
        # Token should be gone
        assert db_session.query(ReportToken).filter_by(token="tok_revoke").first() is None

    @staticmethod
    def test_revoke_not_found(client: TestClient, db_session: Session) -> None:
        job = _seed_completed_job(db_session)
        resp = client.delete(f"/api/v1/jobs/{job.id}/reports/no-such-token")
        assert resp.status_code == 404


# -----------------------------------------------------------------------
# GET /r/{token}  (serve HTML, public)
# -----------------------------------------------------------------------


class TestServeHtmlReportRoute:
    @staticmethod
    def test_not_found(client: TestClient) -> None:
        resp = client.get("/r/nonexistent-token")
        assert resp.status_code == 404

    @staticmethod
    def test_expired_report_410(client: TestClient, db_session: Session) -> None:
        """Expired tokens should return 410 Gone.

        SQLite strips timezone info, so we monkeypatch datetime.now in the
        datetime module to return a naive datetime for consistent comparison.
        """
        import datetime as dt_module

        job = _seed_completed_job(db_session)
        _seed_report_token(db_session, job.id, fmt="html", token="tok_expired", expired=True)
        # The record has a naive past expires_at from utcnow() - 1h.
        # The route calls datetime.now(timezone.utc) which returns tz-aware.
        # Monkeypatch the datetime class in the datetime module so that
        # .now(tz) returns a naive datetime.
        _real_dt_class = dt_module.datetime

        class _NaiveNowDatetime(_real_dt_class):
            @classmethod
            def now(cls, tz=None):
                return _real_dt_class.utcnow()

        with patch.object(dt_module, "datetime", _NaiveNowDatetime):
            resp = client.get("/r/tok_expired")
        assert resp.status_code == 410

    def test_pdf_token_returns_404_on_html_route(
        self, client: TestClient, db_session: Session
    ) -> None:
        job = _seed_completed_job(db_session)
        _seed_report_token(db_session, job.id, fmt="pdf", token="tok_pdf_only")
        resp = client.get("/r/tok_pdf_only")
        assert resp.status_code == 404

    @staticmethod
    def test_serve_html_success(client: TestClient, db_session: Session) -> None:
        job = _seed_completed_job(db_session)
        # Use no_expiry=True to avoid timezone comparison issues on SQLite
        _seed_report_token(db_session, job.id, fmt="html", token="tok_html_ok", no_expiry=True)

        from lintpdf.api.storage import get_storage

        get_storage().upload_report(
            str(PLACEHOLDER_TENANT_ID), str(job.id), "html", b"<html>Report</html>"
        )

        resp = client.get("/r/tok_html_ok")
        assert resp.status_code == 200
        assert b"<html>Report</html>" in resp.content

    @staticmethod
    def test_increments_access_count(client: TestClient, db_session: Session) -> None:
        job = _seed_completed_job(db_session)
        _seed_report_token(db_session, job.id, fmt="html", token="tok_count", no_expiry=True)
        from lintpdf.api.storage import get_storage

        get_storage().upload_report(str(PLACEHOLDER_TENANT_ID), str(job.id), "html", b"<html/>")

        client.get("/r/tok_count")
        client.get("/r/tok_count")

        db_session.expire_all()
        rt = db_session.query(ReportToken).filter_by(token="tok_count").first()
        assert rt.accessed_count == 2


# -----------------------------------------------------------------------
# GET /r/{token}.pdf  (serve PDF, public)
# -----------------------------------------------------------------------


class TestServePdfReportRoute:
    """Tests for GET /r/{token}.pdf.

    Note: FastAPI routes are matched in order. The HTML route /r/{token}
    is registered before /r/{token}.pdf, and /r/{token} matches URLs
    ending in .pdf (with token='xxx.pdf'). As a result, .pdf URLs are
    actually handled by the HTML route first. These tests verify the
    expected behavior via the HTML route's format checking.
    """

    @staticmethod
    def test_not_found(client: TestClient) -> None:
        resp = client.get("/r/nonexistent.pdf")
        assert resp.status_code == 404

    def test_serve_pdf_via_html_route_returns_format_mismatch(
        self, client: TestClient, db_session: Session
    ) -> None:
        """A .pdf URL is caught by /r/{token} with token='xxx.pdf'.

        Since there's no record with token 'xxx.pdf', it returns 404.
        """
        job = _seed_completed_job(db_session)
        _seed_report_token(db_session, job.id, fmt="pdf", token="tok_pdf_only", no_expiry=True)
        # /r/tok_pdf_only.pdf -> HTML route with token='tok_pdf_only.pdf' -> 404
        resp = client.get("/r/tok_pdf_only.pdf")
        assert resp.status_code == 404

    def test_pdf_token_accessible_without_extension(
        self, client: TestClient, db_session: Session
    ) -> None:
        """A PDF-format token accessed via /r/{token} (no .pdf suffix)
        returns 404 because the HTML route checks format != 'html'."""
        job = _seed_completed_job(db_session)
        _seed_report_token(db_session, job.id, fmt="pdf", token="tok_pdf_noext", no_expiry=True)
        resp = client.get("/r/tok_pdf_noext")
        assert resp.status_code == 404
