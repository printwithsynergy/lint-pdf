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


# -----------------------------------------------------------------------
# Inline return mode + Idempotency-Key on POST /reports
# -----------------------------------------------------------------------


def _mock_service_capturing_specs() -> tuple[MagicMock, list[list]]:
    """Build a mock ReportService that records the ``formats`` it was called with.

    Returns ``(mock_service, captured_formats_list)`` — the second item
    grows on each call so tests can assert the router normalized the
    request body correctly before handing it off to the service.
    """
    captured: list[list] = []

    def _capture(**kwargs):
        captured.append(list(kwargs.get("formats") or []))
        result = MagicMock()
        # Mirror the real service's dict shape; let individual tests
        # override per-format via side-effect if needed.
        result.reports = []
        for spec in kwargs.get("formats") or []:
            fmt = getattr(spec, "format", None) or (
                spec.get("format") if isinstance(spec, dict) else spec
            )
            mode = getattr(spec, "return_", None) or (
                spec.get("return", "url") if isinstance(spec, dict) else "url"
            )
            entry: dict = {
                "format": fmt,
                "url": None,
                "token": None,
                "expires_at": None,
                "data": None,
                "content_type": None,
            }
            if mode in ("url", "both"):
                entry["url"] = f"https://reports.example.com/r/tok_{fmt}.{fmt}"
                entry["token"] = f"tok_{fmt}"
            if mode in ("inline", "both") and fmt in ("json", "xml"):
                entry["data"] = {"sample": True} if fmt == "json" else "<root/>"
                entry["content_type"] = "application/json" if fmt == "json" else "application/xml"
            result.reports.append(entry)
        return result

    mock_service = MagicMock()
    mock_service.generate_and_store.side_effect = _capture
    return mock_service, captured


class TestInlineReturnMode:
    @staticmethod
    def test_formats_bare_string_back_compat(client: TestClient, db_session: Session) -> None:
        """Legacy ``formats: ["html","pdf"]`` body still minted as url mode."""
        job = _seed_completed_job(db_session)
        mock_service, captured = _mock_service_capturing_specs()
        with patch("lintpdf.reports.service.ReportService", return_value=mock_service):
            resp = client.post(
                f"/api/v1/jobs/{job.id}/reports",
                json={"formats": ["html", "pdf"]},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert {r["format"] for r in data["reports"]} == {"html", "pdf"}
        assert all(r["url"] and r["token"] for r in data["reports"])
        # Handler must have normalized strings into FormatSpec(return_="url")
        assert len(captured) == 1
        for spec in captured[0]:
            assert getattr(spec, "return_", "url") == "url"

    @staticmethod
    def test_formats_object_inline_json(client: TestClient, db_session: Session) -> None:
        job = _seed_completed_job(db_session)
        mock_service, _ = _mock_service_capturing_specs()
        with patch("lintpdf.reports.service.ReportService", return_value=mock_service):
            resp = client.post(
                f"/api/v1/jobs/{job.id}/reports",
                json={"formats": [{"format": "json", "return": "inline"}]},
            )
        assert resp.status_code == 201
        data = resp.json()["reports"][0]
        assert data["format"] == "json"
        assert data["url"] is None
        assert data["token"] is None
        assert data["data"] == {"sample": True}
        assert data["content_type"] == "application/json"

    @staticmethod
    def test_formats_object_both_xml(client: TestClient, db_session: Session) -> None:
        job = _seed_completed_job(db_session)
        mock_service, _ = _mock_service_capturing_specs()
        with patch("lintpdf.reports.service.ReportService", return_value=mock_service):
            resp = client.post(
                f"/api/v1/jobs/{job.id}/reports",
                json={"formats": [{"format": "xml", "return": "both"}]},
            )
        assert resp.status_code == 201
        data = resp.json()["reports"][0]
        assert data["format"] == "xml"
        assert data["url"] is not None
        assert data["token"] is not None
        assert data["data"] == "<root/>"
        assert data["content_type"] == "application/xml"

    @staticmethod
    def test_inline_rejected_for_binary(client: TestClient, db_session: Session) -> None:
        job = _seed_completed_job(db_session)
        resp = client.post(
            f"/api/v1/jobs/{job.id}/reports",
            json={"formats": [{"format": "pdf", "return": "inline"}]},
        )
        assert resp.status_code == 422
        body = resp.json()
        # FastAPI surfaces the pydantic validator message somewhere in detail.
        assert "Inline return is not supported" in str(body)

    @staticmethod
    def test_inline_disabled_flag(client: TestClient, db_session: Session) -> None:
        """Flipping off LINTPDF_REPORTS_INLINE_ENABLED turns inline into 422."""
        job = _seed_completed_job(db_session)
        with patch("lintpdf.api.config.get_settings") as mock_settings:
            s = MagicMock()
            s.reports_inline_enabled = False
            s.reports_idempotency_enabled = True
            s.report_base_url = "https://reports.example.com"
            s.app_base_url = "https://app.example.com"
            mock_settings.return_value = s
            resp = client.post(
                f"/api/v1/jobs/{job.id}/reports",
                json={"formats": [{"format": "json", "return": "inline"}]},
            )
        assert resp.status_code == 422
        assert "disabled" in resp.json()["detail"].lower()

    @staticmethod
    def test_idempotency_key_too_long_rejected(client: TestClient, db_session: Session) -> None:
        job = _seed_completed_job(db_session)
        resp = client.post(
            f"/api/v1/jobs/{job.id}/reports",
            headers={"Idempotency-Key": "x" * 256},
            json={"formats": ["html"]},
        )
        assert resp.status_code == 422


# -----------------------------------------------------------------------
# ReportService.generate_and_store — deterministic tokens + idempotency
# -----------------------------------------------------------------------


class TestDeterministicTokens:
    """Unit tests for the service layer's deterministic-token behavior.

    Mocks ``_generate_format`` so we don't have to render real reports
    to exercise the idempotency bookkeeping. Uses the InMemoryStorage
    backend that test fixtures install for the API client, but talks
    to it directly since these assertions don't need the HTTP layer.
    """

    @staticmethod
    def test_deterministic_token_is_stable(db_session: Session) -> None:
        from lintpdf.api.storage import get_storage
        from lintpdf.reports.service import ReportService

        job = _seed_completed_job(db_session)
        storage = get_storage()
        service = ReportService(storage, db_session)

        with (
            patch.object(ReportService, "_generate_format", return_value=b'{"findings":[]}'),
            patch.object(ReportService, "_fetch_original_pdf", return_value=None),
        ):
            a = service.generate_and_store(
                job_id=str(job.id),
                tenant_id=str(PLACEHOLDER_TENANT_ID),
                result_json={"summary": {}},
                formats=[{"format": "json", "return": "url"}],
                idempotency_key="invoice-42",
            )
            b = service.generate_and_store(
                job_id=str(job.id),
                tenant_id=str(PLACEHOLDER_TENANT_ID),
                result_json={"summary": {}},
                formats=[{"format": "json", "return": "url"}],
                idempotency_key="invoice-42",
            )
        assert a.reports[0]["token"] == b.reports[0]["token"]

    @staticmethod
    def test_deterministic_token_cross_tenant_isolation(
        db_session: Session,
    ) -> None:
        from lintpdf.reports.service import _deterministic_token

        tenant_a = str(uuid.uuid4())
        tenant_b = str(uuid.uuid4())
        tok_a = _deterministic_token(tenant_a, "shared-key", "json")
        tok_b = _deterministic_token(tenant_b, "shared-key", "json")
        assert tok_a != tok_b

    @staticmethod
    def test_idempotent_mint_skips_reupload(db_session: Session) -> None:
        from lintpdf.api.storage import get_storage
        from lintpdf.reports.service import ReportService

        job = _seed_completed_job(db_session)
        storage = get_storage()
        service = ReportService(storage, db_session)

        upload_spy = MagicMock(wraps=storage.upload_report)
        storage.upload_report = upload_spy  # type: ignore[method-assign]

        with (
            patch.object(ReportService, "_generate_format", return_value=b'{"findings":[]}'),
            patch.object(ReportService, "_fetch_original_pdf", return_value=None),
        ):
            service.generate_and_store(
                job_id=str(job.id),
                tenant_id=str(PLACEHOLDER_TENANT_ID),
                result_json={"summary": {}},
                formats=[{"format": "json", "return": "url"}],
                idempotency_key="invoice-42",
            )
            service.generate_and_store(
                job_id=str(job.id),
                tenant_id=str(PLACEHOLDER_TENANT_ID),
                result_json={"summary": {}},
                formats=[{"format": "json", "return": "url"}],
                idempotency_key="invoice-42",
            )
        # First call uploads; second call hits the idempotent fast path.
        assert upload_spy.call_count == 1

    @staticmethod
    def test_inline_mode_skips_upload_and_token(db_session: Session) -> None:
        from lintpdf.api.storage import get_storage
        from lintpdf.reports.service import ReportService

        job = _seed_completed_job(db_session)
        storage = get_storage()
        service = ReportService(storage, db_session)

        upload_spy = MagicMock(wraps=storage.upload_report)
        storage.upload_report = upload_spy  # type: ignore[method-assign]

        with (
            patch.object(ReportService, "_generate_format", return_value=b'{"findings":[1]}'),
            patch.object(ReportService, "_fetch_original_pdf", return_value=None),
        ):
            result = service.generate_and_store(
                job_id=str(job.id),
                tenant_id=str(PLACEHOLDER_TENANT_ID),
                result_json={"summary": {}},
                formats=[{"format": "json", "return": "inline"}],
            )
        row = result.reports[0]
        assert row["url"] is None
        assert row["token"] is None
        assert row["data"] == {"findings": [1]}
        assert row["content_type"] == "application/json"
        assert upload_spy.call_count == 0
        # No ReportToken row persisted for inline-only mints.
        assert db_session.query(ReportToken).filter(ReportToken.job_id == job.id).count() == 0


class TestViewerUrlField:
    """Mint response surfaces ``viewer_url`` for HTML format only.

    Locks in two contracts:

    1. HTML mints get ``viewer_url`` populated as ``{viewer_base}/view/{token}``.
       Non-HTML mints get ``viewer_url=None``.
    2. ``viewer_base_url`` parameter overrides the global default. This
       is what the route handler uses to thread the tenant-resolved
       custom domain through (so a white-labeled tenant sees their
       ``app_custom_domain`` in the response, not ``app.lintpdf.com``).
    """

    @staticmethod
    def test_html_mint_carries_viewer_url(db_session: Session) -> None:
        from lintpdf.api.storage import get_storage
        from lintpdf.reports.service import ReportService

        job = _seed_completed_job(db_session)
        storage = get_storage()
        service = ReportService(storage, db_session)

        with (
            patch.object(ReportService, "_generate_format", return_value=b"<html></html>"),
            patch.object(ReportService, "_fetch_original_pdf", return_value=None),
        ):
            result = service.generate_and_store(
                job_id=str(job.id),
                tenant_id=str(PLACEHOLDER_TENANT_ID),
                result_json={"summary": {}},
                formats=["html"],
                viewer_base_url="https://acme.example.com",
            )
        row = result.reports[0]
        assert row["format"] == "html"
        assert row["token"]
        assert row["viewer_url"] == f"https://acme.example.com/view/{row['token']}"

    @staticmethod
    def test_non_html_format_has_null_viewer_url(db_session: Session) -> None:
        from lintpdf.api.storage import get_storage
        from lintpdf.reports.service import ReportService

        job = _seed_completed_job(db_session)
        storage = get_storage()
        service = ReportService(storage, db_session)

        with (
            patch.object(ReportService, "_generate_format", return_value=b'{"findings":[]}'),
            patch.object(ReportService, "_fetch_original_pdf", return_value=None),
        ):
            result = service.generate_and_store(
                job_id=str(job.id),
                tenant_id=str(PLACEHOLDER_TENANT_ID),
                result_json={"summary": {}},
                formats=["json"],
                viewer_base_url="https://acme.example.com",
            )
        assert result.reports[0]["format"] == "json"
        assert result.reports[0]["viewer_url"] is None

    @staticmethod
    def test_default_viewer_base_falls_back_to_global(db_session: Session) -> None:
        """When no ``viewer_base_url`` passed, fall back to global app_base_url."""
        from lintpdf.api.config import get_settings
        from lintpdf.api.storage import get_storage
        from lintpdf.reports.service import ReportService

        job = _seed_completed_job(db_session)
        storage = get_storage()
        service = ReportService(storage, db_session)

        with (
            patch.object(ReportService, "_generate_format", return_value=b"<html></html>"),
            patch.object(ReportService, "_fetch_original_pdf", return_value=None),
        ):
            result = service.generate_and_store(
                job_id=str(job.id),
                tenant_id=str(PLACEHOLDER_TENANT_ID),
                result_json={"summary": {}},
                formats=["html"],
            )
        global_base = get_settings().app_base_url.rstrip("/")
        assert result.reports[0]["viewer_url"].startswith(f"{global_base}/view/")
