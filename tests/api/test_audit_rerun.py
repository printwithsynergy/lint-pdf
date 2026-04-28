"""Tests for ``POST /api/v1/jobs/{job_id}/audit:rerun``.

Fakes the Claude auditor so the endpoint is exercised end-to-end
without a live Anthropic call. The rerun endpoint bypasses the
``ai_audit_enabled`` entitlement gate (so pilots + back-catalogue
refreshes work) but still requires ``ANTHROPIC_API_KEY`` in the
env — both paths covered below.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from lintpdf.api.models import Job, JobFinding, JobStatus, Tenant

if TYPE_CHECKING:
    import pytest
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


def _seed_complete_job(
    db_session: Session,
    tenant_id: uuid.UUID,
    *,
    finding_count: int = 3,
) -> uuid.UUID:
    job_id = uuid.uuid4()
    db_session.add(
        Job(
            id=job_id,
            tenant_id=tenant_id,
            status=JobStatus.COMPLETE,
            profile_id="lintpdf-default",
            file_key=f"{tenant_id}/{job_id}/input.pdf",
            file_name="rerun-test.pdf",
            file_size=1024,
            result_json={"summary": {"total_findings": finding_count}},
        )
    )
    for i in range(finding_count):
        db_session.add(
            JobFinding(
                id=uuid.uuid4(),
                job_id=job_id,
                inspection_id=f"LPDF_TEST_{i:03}",
                severity="advisory",
                message=f"Finding {i}",
                page_num=1,
                source="engine",
            )
        )
    db_session.commit()
    return job_id


class TestAuditRerun:
    @staticmethod
    def test_returns_404_for_unknown_job(client: TestClient) -> None:
        resp = client.post(
            f"/api/v1/jobs/{uuid.uuid4()}/audit:rerun",
        )
        assert resp.status_code == 404

    @staticmethod
    def test_rejects_non_complete_job(client: TestClient, db_session: Session) -> None:
        tenant = db_session.query(Tenant).first()
        assert tenant is not None
        job_id = uuid.uuid4()
        db_session.add(
            Job(
                id=job_id,
                tenant_id=tenant.id,
                status=JobStatus.PROCESSING,
                profile_id="lintpdf-default",
                file_key=f"{tenant.id}/{job_id}/input.pdf",
                file_name="still-running.pdf",
                file_size=512,
            )
        )
        db_session.commit()
        resp = client.post(f"/api/v1/jobs/{job_id}/audit:rerun")
        assert resp.status_code == 409
        assert "can only re-audit complete" in resp.json().get("detail", "")

    @staticmethod
    def test_rejects_bad_uuid(client: TestClient) -> None:
        resp = client.post("/api/v1/jobs/not-a-uuid/audit:rerun")
        assert resp.status_code == 422

    @staticmethod
    def test_happy_path_writes_verdicts(
        client: TestClient,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Endpoint bypasses entitlement gate and calls the auditor."""
        tenant = db_session.query(Tenant).first()
        assert tenant is not None
        # Keep entitlements OFF — the endpoint must force-run anyway.
        tenant.entitlement_overrides = {"ai_audit_enabled": False}
        db_session.commit()

        job_id = _seed_complete_job(db_session, tenant.id, finding_count=2)

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-stub")
        from lintpdf.queue import tasks as tasks_mod

        def fake_run_customer_audit(
            db,
            job,
            jid,
            *,
            force=False,
        ):
            # Simulate the auditor writing verdicts.
            assert force is True
            findings = db.query(JobFinding).filter(JobFinding.job_id == job.id).all()
            from datetime import UTC, datetime

            for f in findings:
                f.audit_status = "confirmed"
                f.audit_rationale = "Forced rerun smoke."
                f.audit_model = "claude-haiku-4-5"
                f.audit_at = datetime.now(UTC)
            db.commit()
            return len(findings)

        monkeypatch.setattr(
            tasks_mod,
            "run_customer_audit",
            fake_run_customer_audit,
        )

        resp = client.post(f"/api/v1/jobs/{job_id}/audit:rerun")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["findings_updated"] == 2
        assert body["model"] == "claude-haiku-4-5"
        assert body["job_id"] == str(job_id)

        # Verdicts actually landed in the DB.
        findings = db_session.query(JobFinding).filter(JobFinding.job_id == job_id).all()
        assert all(f.audit_status == "confirmed" for f in findings)

    @staticmethod
    def test_auditor_exception_maps_to_502(
        client: TestClient,
        db_session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Unexpected auditor failures surface as 502 rather than 500."""
        tenant = db_session.query(Tenant).first()
        assert tenant is not None
        job_id = _seed_complete_job(db_session, tenant.id, finding_count=1)

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-stub")
        from lintpdf.queue import tasks as tasks_mod

        monkeypatch.setattr(
            tasks_mod,
            "run_customer_audit",
            MagicMock(side_effect=RuntimeError("claude is napping")),
        )

        resp = client.post(f"/api/v1/jobs/{job_id}/audit:rerun")
        assert resp.status_code == 502
        assert "claude is napping" in resp.json().get("detail", "")
