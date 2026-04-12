"""Tests for the broker-forwarding "anonymous" branding flow.

Covers the pure helpers in :mod:`lintpdf.reports.service` and the public
``/r/{token}.pdf`` share-link endpoint's filename/metadata sanitization.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import TYPE_CHECKING

from lintpdf.api.models import Job, JobStatus, ReportToken
from lintpdf.api.storage import get_storage
from lintpdf.reports.service import (
    BrandingContext,
    BrandMode,
    build_anonymous_filename,
    parse_brand_param,
    sanitize_pdf_metadata_for_anonymous,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

from tests.api.conftest import PLACEHOLDER_TENANT_ID


# ---------------------------------------------------------------------------
# parse_brand_param
# ---------------------------------------------------------------------------


class TestParseBrandParam:
    @staticmethod
    def test_none_returns_nones() -> None:
        assert parse_brand_param(None) == (None, None)
        assert parse_brand_param("") == (None, None)
        assert parse_brand_param("   ") == (None, None)

    @staticmethod
    def test_anonymous_aliases() -> None:
        for raw in ("anonymous", "Anonymous", "  NONE  ", "unbranded"):
            mode, pid = parse_brand_param(raw)
            assert mode is BrandMode.ANONYMOUS
            assert pid is None

    @staticmethod
    def test_lintpdf_aliases() -> None:
        for raw in ("lintpdf", "LintPDF", "default"):
            mode, pid = parse_brand_param(raw)
            assert mode is BrandMode.LINTPDF
            assert pid is None

    @staticmethod
    def test_uuid_is_treated_as_profile() -> None:
        raw = str(uuid.uuid4())
        mode, pid = parse_brand_param(raw)
        assert mode is BrandMode.PROFILE
        assert pid == raw


# ---------------------------------------------------------------------------
# Anonymous helpers
# ---------------------------------------------------------------------------


class TestAnonymousHelpers:
    @staticmethod
    def test_anonymous_context_has_no_identifying_fields() -> None:
        ctx = BrandingContext.anonymous_context()
        assert ctx.anonymous is True
        assert ctx.logo_url is None
        # Footer must not reference LintPDF or the tenant.
        assert ctx.footer_text is None or "lintpdf" not in ctx.footer_text.lower()

    @staticmethod
    def test_build_anonymous_filename_uses_short_id() -> None:
        job_id = "a1b2c3d4-e5f6-7890-abcd-ef0123456789"
        assert build_anonymous_filename(job_id) == "preflight-a1b2c3d4.pdf"
        assert build_anonymous_filename(job_id, extension="html") == (
            "preflight-a1b2c3d4.html"
        )

    @staticmethod
    def test_build_anonymous_filename_handles_short_input() -> None:
        # Shouldn't crash on odd inputs.
        assert build_anonymous_filename("").endswith(".pdf")
        assert build_anonymous_filename("xyz").startswith("preflight-")

    @staticmethod
    def test_sanitize_pdf_metadata_rewrites_info_dict() -> None:
        # Build a tiny branded PDF with pikepdf so we can verify rewrites.
        pikepdf = _import_pikepdf_or_skip()
        if pikepdf is None:
            return

        out = BytesIO()
        with pikepdf.Pdf.new() as pdf:
            pdf.add_blank_page(page_size=(612, 792))
            info = pdf.docinfo
            info["/Author"] = "Acme Broker"
            info["/Creator"] = "Acme Preflight Pro"
            info["/Producer"] = "LintPDF / WeasyPrint"
            info["/Title"] = "Brochure — internal review"
            pdf.save(out)
        original = out.getvalue()

        scrubbed = sanitize_pdf_metadata_for_anonymous(original)

        with pikepdf.open(BytesIO(scrubbed)) as pdf:
            info = pdf.docinfo
            assert str(info.get("/Author", "")) == ""
            assert str(info.get("/Creator", "")) == "Preflight"
            assert str(info.get("/Producer", "")) == "Preflight"
            assert str(info.get("/Title", "")) == "Preflight Report"


def _import_pikepdf_or_skip():
    try:
        import pikepdf  # type: ignore

        return pikepdf
    except ImportError:  # pragma: no cover
        import pytest

        pytest.skip("pikepdf not installed")
        return None


# ---------------------------------------------------------------------------
# Share-link PDF download — filename swap on anonymous tokens
# ---------------------------------------------------------------------------


def _seed_completed_job(db: Session) -> Job:
    job = Job(
        id=uuid.uuid4(),
        tenant_id=PLACEHOLDER_TENANT_ID,
        status=JobStatus.COMPLETE,
        profile_id="lintpdf-default",
        file_key="seed/file.pdf",
        file_name="seed.pdf",
        file_size=1024,
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class TestSharePdfFilenameAnonymity:
    """The public ``/r/{token}.pdf`` route swaps the filename for anonymous
    tokens so the download landing in the distributor's inbox carries no
    broker or LintPDF hint."""

    @staticmethod
    def test_anonymous_token_returns_preflight_filename(
        client: TestClient, db_session: Session
    ) -> None:
        job = _seed_completed_job(db_session)

        # Minimum PDF bytes — we're not inspecting contents here, only the
        # Content-Disposition header the route produces.
        pdf = b"%PDF-1.4\n%%EOF\n"
        storage = get_storage()
        storage.upload_report(str(PLACEHOLDER_TENANT_ID), str(job.id), "pdf", pdf)

        token = ReportToken(
            id=uuid.uuid4(),
            job_id=job.id,
            tenant_id=PLACEHOLDER_TENANT_ID,
            token="anon-broker-token-001",
            format="pdf",
            brand_mode="anonymous",
        )
        db_session.add(token)
        db_session.commit()

        resp = client.get(f"/r/{token.token}.pdf")
        assert resp.status_code == 200
        disposition = resp.headers.get("content-disposition", "")
        short = str(job.id).split("-", 1)[0][:8]
        assert f'filename="preflight-{short}.pdf"' in disposition

    @staticmethod
    def test_non_anonymous_token_uses_default_filename(
        client: TestClient, db_session: Session
    ) -> None:
        job = _seed_completed_job(db_session)
        pdf = b"%PDF-1.4\n%%EOF\n"
        storage = get_storage()
        storage.upload_report(str(PLACEHOLDER_TENANT_ID), str(job.id), "pdf", pdf)

        token = ReportToken(
            id=uuid.uuid4(),
            job_id=job.id,
            tenant_id=PLACEHOLDER_TENANT_ID,
            token="branded-token-001",
            format="pdf",
            brand_mode="lintpdf",
        )
        db_session.add(token)
        db_session.commit()

        resp = client.get(f"/r/{token.token}.pdf")
        assert resp.status_code == 200
        disposition = resp.headers.get("content-disposition", "")
        assert 'filename="report.pdf"' in disposition
