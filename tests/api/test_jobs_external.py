"""Integration tests for the external/minimal preflight submission flow
and the per-job brand override on ``POST /api/v1/jobs``.

These exercise the HTTP surface end-to-end (validation, persistence, and
queue dispatch) without running a real worker — Celery dispatch is stubbed
by ``conftest._mock_celery_delay``.
"""

from __future__ import annotations

import secrets
import uuid
from io import BytesIO
from types import SimpleNamespace
from typing import TYPE_CHECKING

from lintpdf.api.models import (
    BrandProfile,
    BrandProfileType,
    Job,
    JobImportedReport,
    PreflightSource,
    Tenant,
)
from lintpdf.tenants.toggle_models import ToggleOverride, ToggleScope

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

from tests.api.conftest import PLACEHOLDER_TENANT_ID

# ---------------------------------------------------------------------------
# Fixtures — raw import payloads
# ---------------------------------------------------------------------------


PITSTOP_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<PitStopReport>
  <Header>
    <Profile>PDF/X-4 Sheetfed</Profile>
    <PitStopVersion>2024.1</PitStopVersion>
  </Header>
  <Results>
    <Error>
      <CheckID>IMG_LOWRES</CheckID>
      <Description>Image resolution below 300 dpi</Description>
      <Page>2</Page>
      <BBox>72 72 216 216</BBox>
    </Error>
    <Warning>
      <CheckID>FONT_NOEMBED</CheckID>
      <Description>Font not embedded</Description>
      <Page>1</Page>
    </Warning>
  </Results>
</PitStopReport>
"""


# ---------------------------------------------------------------------------
# preflight_source=external
# ---------------------------------------------------------------------------


class TestExternalImportSubmission:
    """Uploading a PDF + third-party report marks the job external."""

    @staticmethod
    def test_pitstop_xml_import_persists_job_and_report(
        client: TestClient, minimal_pdf_bytes: bytes, db_session: Session
    ) -> None:
        resp = client.post(
            "/api/v1/jobs",
            files={
                "file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf"),
                "external_report": (
                    "report.xml",
                    BytesIO(PITSTOP_XML),
                    "application/xml",
                ),
            },
            data={
                "profile_id": "lintpdf-default",
                "preflight_source": "external",
            },
        )
        assert resp.status_code == 202, resp.text
        job_id = uuid.UUID(resp.json()["job_id"])

        job = db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None
        assert job.preflight_source == PreflightSource.EXTERNAL
        # Auto-detect should resolve to pitstop_xml.
        assert job.external_format == "pitstop_xml"

        imported = (
            db_session.query(JobImportedReport).filter(JobImportedReport.job_id == job_id).first()
        )
        assert imported is not None
        assert imported.format == "pitstop_xml"
        assert imported.raw_size_bytes == len(PITSTOP_XML)
        assert imported.raw_blob_key.endswith("external-report.dat")

    @staticmethod
    def test_external_requires_report_file(client: TestClient, minimal_pdf_bytes: bytes) -> None:
        resp = client.post(
            "/api/v1/jobs",
            files={"file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
            data={
                "profile_id": "lintpdf-default",
                "preflight_source": "external",
            },
        )
        assert resp.status_code == 422
        assert "external_report" in resp.json()["detail"].lower()

    @staticmethod
    def test_non_external_source_rejects_report_file(
        client: TestClient, minimal_pdf_bytes: bytes
    ) -> None:
        resp = client.post(
            "/api/v1/jobs",
            files={
                "file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf"),
                "external_report": ("r.xml", BytesIO(PITSTOP_XML), "application/xml"),
            },
            data={
                "profile_id": "lintpdf-default",
                "preflight_source": "engine",
            },
        )
        assert resp.status_code == 422
        assert "external_report" in resp.json()["detail"].lower()

    @staticmethod
    def test_empty_report_rejected(client: TestClient, minimal_pdf_bytes: bytes) -> None:
        resp = client.post(
            "/api/v1/jobs",
            files={
                "file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf"),
                "external_report": ("r.xml", BytesIO(b""), "application/xml"),
            },
            data={
                "profile_id": "lintpdf-default",
                "preflight_source": "external",
            },
        )
        assert resp.status_code == 422
        assert "empty" in resp.json()["detail"].lower()

    @staticmethod
    def test_invalid_preflight_source_rejected(
        client: TestClient, minimal_pdf_bytes: bytes
    ) -> None:
        resp = client.post(
            "/api/v1/jobs",
            files={"file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
            data={
                "profile_id": "lintpdf-default",
                "preflight_source": "totally-bogus",
            },
        )
        assert resp.status_code == 422
        assert "preflight_source" in resp.json()["detail"].lower()

    @staticmethod
    def test_unknown_explicit_external_format_rejected(
        client: TestClient, minimal_pdf_bytes: bytes
    ) -> None:
        resp = client.post(
            "/api/v1/jobs",
            files={
                "file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf"),
                "external_report": ("r.xml", BytesIO(PITSTOP_XML), "application/xml"),
            },
            data={
                "profile_id": "lintpdf-default",
                "preflight_source": "external",
                "external_format": "sorcery_xml",
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# preflight_source=minimal
# ---------------------------------------------------------------------------


class TestMinimalSubmission:
    """Minimal mode records the job without an external report."""

    @staticmethod
    def test_minimal_submission_persists_job(
        client: TestClient, minimal_pdf_bytes: bytes, db_session: Session
    ) -> None:
        resp = client.post(
            "/api/v1/jobs",
            files={"file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
            data={
                "profile_id": "lintpdf-default",
                "preflight_source": "minimal",
            },
        )
        assert resp.status_code == 202, resp.text
        job_id = uuid.UUID(resp.json()["job_id"])

        job = db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None
        assert job.preflight_source == PreflightSource.MINIMAL
        assert job.external_format is None
        # No JobImportedReport row for minimal jobs.
        reports = (
            db_session.query(JobImportedReport).filter(JobImportedReport.job_id == job_id).all()
        )
        assert reports == []


# ---------------------------------------------------------------------------
# brand override
# ---------------------------------------------------------------------------


class TestBrandOverrideOnSubmit:
    """The ``brand`` and ``unbranded`` form fields persist on the Job row."""

    @staticmethod
    def test_brand_anonymous_persists_unbranded_override(
        client: TestClient, minimal_pdf_bytes: bytes, db_session: Session
    ) -> None:
        resp = client.post(
            "/api/v1/jobs",
            files={"file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
            data={"profile_id": "lintpdf-default", "brand": "anonymous"},
        )
        assert resp.status_code == 202
        job_id = uuid.UUID(resp.json()["job_id"])
        job = db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None
        assert job.unbranded_override is True
        assert job.brand_profile_id_override is None

    @staticmethod
    def test_unbranded_alias_behaves_like_brand_anonymous(
        client: TestClient, minimal_pdf_bytes: bytes, db_session: Session
    ) -> None:
        resp = client.post(
            "/api/v1/jobs",
            files={"file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
            data={"profile_id": "lintpdf-default", "unbranded": "true"},
        )
        assert resp.status_code == 202
        job_id = uuid.UUID(resp.json()["job_id"])
        job = db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None
        assert job.unbranded_override is True

    @staticmethod
    def test_brand_profile_owned_by_tenant_persists_override(
        client: TestClient, minimal_pdf_bytes: bytes, db_session: Session
    ) -> None:
        profile = BrandProfile(
            id=uuid.uuid4(),
            tenant_id=PLACEHOLDER_TENANT_ID,
            name="House Style",
            profile_type=BrandProfileType.CUSTOM,
            brand_name="House",
            primary_color="#112233",
        )
        db_session.add(profile)
        db_session.commit()

        resp = client.post(
            "/api/v1/jobs",
            files={"file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
            data={"profile_id": "lintpdf-default", "brand": str(profile.id)},
        )
        assert resp.status_code == 202
        job_id = uuid.UUID(resp.json()["job_id"])
        job = db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None
        assert job.brand_profile_id_override == profile.id
        assert job.unbranded_override is False

    @staticmethod
    def test_brand_profile_unknown_uuid_returns_403(
        client: TestClient, minimal_pdf_bytes: bytes
    ) -> None:
        # Random UUID — not owned by the placeholder tenant.
        resp = client.post(
            "/api/v1/jobs",
            files={"file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
            data={"profile_id": "lintpdf-default", "brand": str(uuid.uuid4())},
        )
        assert resp.status_code == 403
        assert "not found" in resp.json()["detail"].lower() or (
            "not owned" in resp.json()["detail"].lower()
        )

    @staticmethod
    def test_brand_malformed_value_returns_422(
        client: TestClient, minimal_pdf_bytes: bytes
    ) -> None:
        resp = client.post(
            "/api/v1/jobs",
            files={"file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
            data={"profile_id": "lintpdf-default", "brand": "not-a-uuid-or-keyword"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# mapping_id (tenant-defined custom mapping)
# ---------------------------------------------------------------------------


CUSTOM_XML = b"""<?xml version="1.0"?>
<PreflightLog><Issues>
  <Issue level="HIGH" page="2"><Description>Custom finding</Description></Issue>
</Issues></PreflightLog>
"""


def _seed_mapping(db_session: Session, *, tenant_id=None, is_active: bool = True):
    """Phase 0.7 PR-B4-final — seed the mapping into the unified-config
    substrate (``ToggleOverride(toggle_id='import_mapping', scope=TENANT)``).
    Returns a SimpleNamespace with ``.id`` so legacy callers reading
    that attr keep working.
    """
    tid = tenant_id or PLACEHOLDER_TENANT_ID
    new_id = uuid.uuid4()
    entry = {
        "id": str(new_id),
        "name": "Acme PitStop-lite",
        "description": None,
        "format": "xml",
        "config": {
            "format": "xml",
            "item_selector": "Issues/Issue",
            "fields": {
                "severity": "@level",
                "message": "Description",
                "page": "@page",
            },
            "severity_map": {"high": "error"},
        },
        "sample_payload": None,
        "sample_mime": None,
        "is_active": is_active,
    }

    existing = (
        db_session.query(ToggleOverride)
        .filter(
            ToggleOverride.toggle_id == "import_mapping",
            ToggleOverride.scope == ToggleScope.TENANT,
            ToggleOverride.scope_id == str(tid),
        )
        .first()
    )
    if existing is None:
        db_session.add(
            ToggleOverride(
                id=secrets.token_urlsafe(12),
                toggle_id="import_mapping",
                scope=ToggleScope.TENANT,
                scope_id=str(tid),
                value={str(new_id): entry},
                locked=False,
                set_by="test",
                surface="test",
            )
        )
    else:
        value = dict(existing.value or {})
        value[str(new_id)] = entry
        existing.value = value
    db_session.commit()
    return SimpleNamespace(id=new_id)


class TestMappingIdSubmission:
    """Uploading a PDF + custom XML parsed by a tenant-owned mapping."""

    @staticmethod
    def test_custom_mapping_marks_job_external_custom(
        client: TestClient, minimal_pdf_bytes: bytes, db_session: Session
    ) -> None:
        mapping = _seed_mapping(db_session)
        resp = client.post(
            "/api/v1/jobs",
            files={
                "file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf"),
                "external_report": (
                    "r.xml",
                    BytesIO(CUSTOM_XML),
                    "application/xml",
                ),
            },
            data={
                "profile_id": "lintpdf-default",
                "preflight_source": "external",
                "mapping_id": str(mapping.id),
            },
        )
        assert resp.status_code == 202, resp.text
        job_id = uuid.UUID(resp.json()["job_id"])

        job = db_session.query(Job).filter(Job.id == job_id).first()
        assert job is not None
        assert job.preflight_source == PreflightSource.EXTERNAL
        assert job.external_format == "custom"

        imported = (
            db_session.query(JobImportedReport).filter(JobImportedReport.job_id == job_id).first()
        )
        assert imported is not None
        assert imported.format == "custom"
        assert (imported.source_metadata or {}).get("mapping_id") == str(mapping.id)

    @staticmethod
    def test_unknown_mapping_id_rejected_403(client: TestClient, minimal_pdf_bytes: bytes) -> None:
        resp = client.post(
            "/api/v1/jobs",
            files={
                "file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf"),
                "external_report": ("r.xml", BytesIO(CUSTOM_XML), "application/xml"),
            },
            data={
                "profile_id": "lintpdf-default",
                "preflight_source": "external",
                "mapping_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code == 403

    @staticmethod
    def test_foreign_tenant_mapping_rejected_403(
        client: TestClient, minimal_pdf_bytes: bytes, db_session: Session
    ) -> None:
        foreign_tenant_id = uuid.uuid4()
        db_session.add(
            Tenant(
                id=foreign_tenant_id,
                name="Other",
                api_key_hash="foreign",
            )
        )
        db_session.commit()
        mapping = _seed_mapping(db_session, tenant_id=foreign_tenant_id)

        resp = client.post(
            "/api/v1/jobs",
            files={
                "file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf"),
                "external_report": ("r.xml", BytesIO(CUSTOM_XML), "application/xml"),
            },
            data={
                "profile_id": "lintpdf-default",
                "preflight_source": "external",
                "mapping_id": str(mapping.id),
            },
        )
        assert resp.status_code == 403

    @staticmethod
    def test_inactive_mapping_rejected_422(
        client: TestClient, minimal_pdf_bytes: bytes, db_session: Session
    ) -> None:
        mapping = _seed_mapping(db_session, is_active=False)
        resp = client.post(
            "/api/v1/jobs",
            files={
                "file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf"),
                "external_report": ("r.xml", BytesIO(CUSTOM_XML), "application/xml"),
            },
            data={
                "profile_id": "lintpdf-default",
                "preflight_source": "external",
                "mapping_id": str(mapping.id),
            },
        )
        assert resp.status_code == 422
        assert "inactive" in resp.json()["detail"].lower()

    @staticmethod
    def test_malformed_mapping_id_rejected_422(
        client: TestClient, minimal_pdf_bytes: bytes
    ) -> None:
        resp = client.post(
            "/api/v1/jobs",
            files={
                "file": ("input.pdf", BytesIO(minimal_pdf_bytes), "application/pdf"),
                "external_report": ("r.xml", BytesIO(CUSTOM_XML), "application/xml"),
            },
            data={
                "profile_id": "lintpdf-default",
                "preflight_source": "external",
                "mapping_id": "not-a-uuid",
            },
        )
        assert resp.status_code == 422
