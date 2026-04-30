"""Tests for ``PATCH /api/v1/admin/findings/{id}/audit`` — manual verdict override.

The admin CLI path lets ops overwrite an AI-produced verdict when the
auditor got one wrong. Writes ``audit_model`` as ``manual:<admin>``
so the viewer chip can distinguish human from machine verdicts, and
``status=null`` clears the row back to "not audited".
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from siftpdf.api.models import Job, JobFinding, JobStatus, Tenant

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

ADMIN_KEY = "test-manual-admin-key"
HEADERS = {"X-Admin-Key": ADMIN_KEY}


def _seed_finding(db: Session, *, status: str | None = "confirmed") -> uuid.UUID:
    tenant = db.query(Tenant).first()
    assert tenant is not None
    job_id = uuid.uuid4()
    finding_id = uuid.uuid4()
    db.add(
        Job(
            id=job_id,
            tenant_id=tenant.id,
            status=JobStatus.COMPLETE,
            profile_id="lintpdf-default",
            file_key=f"{tenant.id}/{job_id}/in.pdf",
            file_name="manual.pdf",
            file_size=256,
        )
    )
    db.add(
        JobFinding(
            id=finding_id,
            job_id=job_id,
            inspection_id="LPDF_MANUAL_TEST",
            severity="warning",
            message="AI-produced verdict we're about to override",
            page_num=1,
            source="engine",
            audit_status=status,
            audit_model="modal:qwen2-vl-7b" if status else None,
            audit_rationale="AI says so." if status else None,
        )
    )
    db.commit()
    return finding_id


class TestManualAuditOverride:
    @staticmethod
    def test_rejects_missing_admin_key(client: TestClient, db_session: Session) -> None:
        fid = _seed_finding(db_session)
        resp = client.patch(
            f"/api/v1/admin/findings/{fid}/audit",
            json={"status": "disputed"},
        )
        assert resp.status_code == 401

    @staticmethod
    def test_rejects_invalid_uuid(client: TestClient, monkeypatch) -> None:
        monkeypatch.setenv("LINTPDF_ADMIN_API_KEY", ADMIN_KEY)
        resp = client.patch(
            "/api/v1/admin/findings/not-a-uuid/audit",
            headers=HEADERS,
            json={"status": "confirmed"},
        )
        assert resp.status_code == 422

    @staticmethod
    def test_rejects_unknown_status(client: TestClient, db_session: Session, monkeypatch) -> None:
        monkeypatch.setenv("LINTPDF_ADMIN_API_KEY", ADMIN_KEY)
        fid = _seed_finding(db_session)
        resp = client.patch(
            f"/api/v1/admin/findings/{fid}/audit",
            headers=HEADERS,
            json={"status": "sparkle"},
        )
        assert resp.status_code == 422

    @staticmethod
    def test_404_on_missing_finding(client: TestClient, monkeypatch) -> None:
        monkeypatch.setenv("LINTPDF_ADMIN_API_KEY", ADMIN_KEY)
        resp = client.patch(
            f"/api/v1/admin/findings/{uuid.uuid4()}/audit",
            headers=HEADERS,
            json={"status": "confirmed"},
        )
        assert resp.status_code == 404

    @staticmethod
    def test_override_sets_manual_model_tag(
        client: TestClient, db_session: Session, monkeypatch
    ) -> None:
        monkeypatch.setenv("LINTPDF_ADMIN_API_KEY", ADMIN_KEY)
        fid = _seed_finding(db_session, status="disputed")

        resp = client.patch(
            f"/api/v1/admin/findings/{fid}/audit",
            headers=HEADERS,
            json={
                "status": "confirmed",
                "rationale": "Engine is right; AI misread the overprint.",
                "admin_email": "ops@lintpdf.com",
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["audit_status"] == "confirmed"
        assert body["audit_model"] == "manual:ops@lintpdf.com"
        assert "misread" in body["audit_rationale"]

        finding = db_session.query(JobFinding).filter(JobFinding.id == fid).first()
        assert finding is not None
        assert finding.audit_status == "confirmed"
        assert finding.audit_model == "manual:ops@lintpdf.com"

    @staticmethod
    def test_null_status_clears_verdict(
        client: TestClient, db_session: Session, monkeypatch
    ) -> None:
        monkeypatch.setenv("LINTPDF_ADMIN_API_KEY", ADMIN_KEY)
        fid = _seed_finding(db_session, status="confirmed")

        resp = client.patch(
            f"/api/v1/admin/findings/{fid}/audit",
            headers=HEADERS,
            json={"status": None},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["audit_status"] is None
        assert body["audit_model"] is None
        assert body["audit_rationale"] is None

    @staticmethod
    def test_default_admin_tag_when_email_omitted(
        client: TestClient, db_session: Session, monkeypatch
    ) -> None:
        monkeypatch.setenv("LINTPDF_ADMIN_API_KEY", ADMIN_KEY)
        fid = _seed_finding(db_session, status="confirmed")

        resp = client.patch(
            f"/api/v1/admin/findings/{fid}/audit",
            headers=HEADERS,
            json={"status": "disputed", "rationale": "by hand"},
        )
        assert resp.status_code == 200
        assert resp.json()["audit_model"] == "manual:super-admin"
