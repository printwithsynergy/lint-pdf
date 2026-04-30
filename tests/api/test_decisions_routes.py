"""Tests for /api/v1/jobs/{id}/decisions HTTP routes (Wave V V-05)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

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


def _make_finding(db, *, job_id, inspection_id="LPDF_TST_001"):
    from siftpdf.api.models import JobFinding

    f = JobFinding(
        id=uuid.uuid4(),
        job_id=job_id,
        inspection_id=inspection_id,
        severity="warning",
        message="message",
    )
    db.add(f)
    db.commit()
    return f


def _record_payload(**overrides):
    base = {
        "decision_type": "approve",
        "decided_by_user_id": "user-1",
        "source": "dashboard",
    }
    base.update(overrides)
    return base


# ---- list (GET) ---------------------------------------------------------


def test_list_empty_for_clean_job(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    resp = client.get(f"/api/v1/jobs/{job.id}/decisions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["decisions"] == []


def test_list_returns_recorded_decisions(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    client.post(
        f"/api/v1/jobs/{job.id}/decisions",
        json=_record_payload(decision_type="approve"),
    )
    client.post(
        f"/api/v1/jobs/{job.id}/decisions",
        json=_record_payload(decision_type="waive"),
    )
    resp = client.get(f"/api/v1/jobs/{job.id}/decisions")
    body = resp.json()
    assert resp.status_code == 200
    assert body["count"] == 2
    types = {d["decision_type"] for d in body["decisions"]}
    assert types == {"approve", "waive"}


def test_list_excludes_revoked_by_default(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    create = client.post(
        f"/api/v1/jobs/{job.id}/decisions",
        json=_record_payload(decision_type="approve"),
    )
    decision_id = create.json()["id"]
    client.post(
        f"/api/v1/jobs/{job.id}/decisions/{decision_id}/revoke",
        json={"revoked_by_user_id": "user-1"},
    )
    resp = client.get(f"/api/v1/jobs/{job.id}/decisions")
    assert resp.json()["count"] == 0
    resp_all = client.get(f"/api/v1/jobs/{job.id}/decisions?include_revoked=true")
    assert resp_all.json()["count"] == 1


# ---- record (POST) -------------------------------------------------------


def test_record_job_decision_returns_201(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    resp = client.post(
        f"/api/v1/jobs/{job.id}/decisions",
        json=_record_payload(decision_type="approve", notes="LGTM"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["decision_type"] == "approve"
    assert body["notes"] == "LGTM"
    assert body["finding_id"] is None
    assert body["is_active"] is True


def test_record_finding_decision_links_finding(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    finding = _make_finding(db_session, job_id=job.id)
    resp = client.post(
        f"/api/v1/jobs/{job.id}/findings/{finding.id}/decisions",
        json=_record_payload(decision_type="waive"),
    )
    assert resp.status_code == 201
    assert resp.json()["finding_id"] == str(finding.id)


def test_record_propagates_request_id_header(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    resp = client.post(
        f"/api/v1/jobs/{job.id}/decisions",
        json=_record_payload(),
        headers={"X-Request-ID": "req-abc-123"},
    )
    assert resp.status_code == 201
    db_session.expire_all()
    from siftpdf.decisions.models import Decision

    row = db_session.query(Decision).first()
    assert row is not None
    assert row.request_id == "req-abc-123"


def test_record_invalid_source_returns_422(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    resp = client.post(
        f"/api/v1/jobs/{job.id}/decisions",
        json=_record_payload(source="not-a-real-source"),
    )
    assert resp.status_code == 422


def test_record_missing_field_returns_422(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    resp = client.post(
        f"/api/v1/jobs/{job.id}/decisions",
        json={"decision_type": "approve"},  # missing required fields
    )
    assert resp.status_code == 422


# ---- revoke (POST .../revoke) -------------------------------------------


def test_revoke_marks_decision_inactive(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    create = client.post(
        f"/api/v1/jobs/{job.id}/decisions",
        json=_record_payload(),
    )
    decision_id = create.json()["id"]
    resp = client.post(
        f"/api/v1/jobs/{job.id}/decisions/{decision_id}/revoke",
        json={"revoked_by_user_id": "rev-user", "revoked_reason": "mistake"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_active"] is False
    assert body["revoked_by_user_id"] == "rev-user"
    assert body["revoked_reason"] == "mistake"
    assert body["revoked_at"] is not None


def test_revoke_is_idempotent(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    create = client.post(
        f"/api/v1/jobs/{job.id}/decisions",
        json=_record_payload(),
    )
    decision_id = create.json()["id"]
    first = client.post(
        f"/api/v1/jobs/{job.id}/decisions/{decision_id}/revoke",
        json={"revoked_by_user_id": "u1"},
    )
    second = client.post(
        f"/api/v1/jobs/{job.id}/decisions/{decision_id}/revoke",
        json={"revoked_by_user_id": "u2"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    # First revoker wins; second call is a no-op.
    assert second.json()["revoked_by_user_id"] == "u1"


def test_revoke_unknown_decision_404s(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    resp = client.post(
        f"/api/v1/jobs/{job.id}/decisions/{uuid.uuid4()}/revoke",
        json={"revoked_by_user_id": "u1"},
    )
    assert resp.status_code == 404


# ---- 404 / cross-tenant isolation ---------------------------------------


def test_list_unknown_job_returns_404(client: TestClient):
    resp = client.get(f"/api/v1/jobs/{uuid.uuid4()}/decisions")
    assert resp.status_code == 404


def test_record_unknown_job_returns_404(client: TestClient):
    resp = client.post(
        f"/api/v1/jobs/{uuid.uuid4()}/decisions",
        json=_record_payload(),
    )
    assert resp.status_code == 404


def test_invalid_uuid_returns_404(client: TestClient):
    resp = client.get("/api/v1/jobs/not-a-uuid/decisions")
    assert resp.status_code == 404


def test_cross_tenant_job_404s(client: TestClient, db_session: Session):
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
    foreign_job = _make_job(db_session, tenant_id=foreign_id)
    resp = client.get(f"/api/v1/jobs/{foreign_job.id}/decisions")
    assert resp.status_code == 404


def test_finding_decision_unknown_finding_404s(client: TestClient, db_session: Session):
    job = _make_job(db_session)
    resp = client.post(
        f"/api/v1/jobs/{job.id}/findings/{uuid.uuid4()}/decisions",
        json=_record_payload(),
    )
    assert resp.status_code == 404
