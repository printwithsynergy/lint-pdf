"""EPM candidacy summary endpoint tests."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from siftpdf.epm import codes
from tests.api.conftest import PLACEHOLDER_TENANT_ID

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


def _make_job(db, *, tenant_id=PLACEHOLDER_TENANT_ID):
    from siftpdf.api.models import Job, JobStatus

    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        status=JobStatus.PENDING,
        profile_id="lintpdf-default",
        file_key=f"{tenant_id}/x.pdf",
        file_name="x.pdf",
        file_size=1,
    )
    db.add(job)
    db.commit()
    return job


def _add_finding(db, *, job_id, inspection_id, severity="warning"):
    from siftpdf.api.models import JobFinding

    f = JobFinding(
        id=uuid.uuid4(),
        job_id=job_id,
        inspection_id=inspection_id,
        severity=severity,
        message=f"{inspection_id} message",
    )
    db.add(f)
    db.commit()
    return f


# ---- happy paths ---------------------------------------------------------


def test_clean_job_passes(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    resp = client.get(f"/api/v1/jobs/{job.id}/epm")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == str(job.id)
    assert body["tier"] == "pass"
    assert body["rejection_drivers"] == []
    assert body["advisories"] == []
    assert body["recommends_indichrome"] is False
    assert body["legacy_codes_fired"] == []
    assert body["epm_findings_count"] == 0


def test_advisory_only_passes_with_advisory(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    _add_finding(
        db_session,
        job_id=job.id,
        inspection_id=codes.EPM_TRAPPING_DISABLED,
        severity="advisory",
    )
    resp = client.get(f"/api/v1/jobs/{job.id}/epm")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "pass_with_advisory"
    assert codes.EPM_TRAPPING_DISABLED in body["advisories"]
    assert body["epm_findings_count"] == 1


def test_single_b_finding_marginal(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    _add_finding(
        db_session,
        job_id=job.id,
        inspection_id=codes.EPM_BLEED_BELOW_MIN,
    )
    resp = client.get(f"/api/v1/jobs/{job.id}/epm")
    body = resp.json()
    assert body["tier"] == "marginal"
    assert body["rejection_drivers"] == [codes.EPM_BLEED_BELOW_MIN]


def test_two_b_findings_reject(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    _add_finding(db_session, job_id=job.id, inspection_id=codes.EPM_BLEED_BELOW_MIN)
    _add_finding(db_session, job_id=job.id, inspection_id=codes.EPM_PROCESS_COLOR_COUNT)
    resp = client.get(f"/api/v1/jobs/{job.id}/epm")
    body = resp.json()
    assert body["tier"] == "reject"
    assert codes.EPM_BLEED_BELOW_MIN in body["rejection_drivers"]
    assert codes.EPM_PROCESS_COLOR_COUNT in body["rejection_drivers"]


def test_a_tier_finding_rejects_outright(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    _add_finding(
        db_session,
        job_id=job.id,
        inspection_id=codes.EPM_GAMUT_OUT_OF_REACH,
        severity="error",
    )
    resp = client.get(f"/api/v1/jobs/{job.id}/epm")
    body = resp.json()
    assert body["tier"] == "reject"
    assert codes.EPM_GAMUT_OUT_OF_REACH in body["rejection_drivers"]
    assert body["recommends_indichrome"] is True


def test_legacy_a_code_recognized(client: TestClient, db_session: Session):
    """Legacy LPDF_EPM_001 (K-channel usage) is treated as A-tier reject."""
    job = _make_job(db_session)
    _add_finding(db_session, job_id=job.id, inspection_id="LPDF_EPM_001")
    resp = client.get(f"/api/v1/jobs/{job.id}/epm")
    body = resp.json()
    assert body["tier"] == "reject"
    assert "LPDF_EPM_001" in body["rejection_drivers"]
    assert "LPDF_EPM_001" in body["legacy_codes_fired"]


def test_non_epm_findings_are_ignored(client: TestClient, db_session: Session):
    """A heap of LPDF_IMG_* findings shouldn't bias the EPM verdict."""
    job = _make_job(db_session)
    for _ in range(20):
        _add_finding(
            db_session,
            job_id=job.id,
            inspection_id="LPDF_IMG_001",
            severity="warning",
        )
    resp = client.get(f"/api/v1/jobs/{job.id}/epm")
    body = resp.json()
    assert body["tier"] == "pass"
    assert body["epm_findings_count"] == 0


def test_indichrome_hint_when_spot_drives_b_pair(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    _add_finding(db_session, job_id=job.id, inspection_id="LPDF_EPM_005")
    _add_finding(db_session, job_id=job.id, inspection_id=codes.EPM_BLEED_BELOW_MIN)
    resp = client.get(f"/api/v1/jobs/{job.id}/epm")
    body = resp.json()
    assert body["tier"] == "reject"
    assert body["recommends_indichrome"] is True


# ---- 404 cases -----------------------------------------------------------


def test_404_for_invalid_uuid(client: TestClient):
    resp = client.get("/api/v1/jobs/not-a-uuid/epm")
    assert resp.status_code == 404


def test_404_for_unknown_job(client: TestClient):
    resp = client.get(f"/api/v1/jobs/{uuid.uuid4()}/epm")
    assert resp.status_code == 404


def test_404_for_cross_tenant_job(client: TestClient, db_session: Session):
    """Foreign tenant's job must 404 (no leakage)."""
    from siftpdf.api.models import Tenant, TenantPlan

    foreign_id = uuid.uuid4()
    db_session.add(
        Tenant(
            id=foreign_id,
            name="other",
            api_key_hash="other-hash",
            plan=TenantPlan.GROWTH,
            rate_limit_daily=1000,
            max_file_size_mb=10,
        )
    )
    db_session.commit()
    job = _make_job(db_session, tenant_id=foreign_id)

    resp = client.get(f"/api/v1/jobs/{job.id}/epm")
    assert resp.status_code == 404


# ---- response shape ------------------------------------------------------


def test_response_includes_all_documented_fields(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    _add_finding(
        db_session,
        job_id=job.id,
        inspection_id=codes.EPM_TRAPPING_DISABLED,
    )
    resp = client.get(f"/api/v1/jobs/{job.id}/epm")
    body = resp.json()
    assert set(body.keys()) == {
        "job_id",
        "tier",
        "rejection_drivers",
        "advisories",
        "recommends_indichrome",
        "legacy_codes_fired",
        "epm_findings_count",
    }
