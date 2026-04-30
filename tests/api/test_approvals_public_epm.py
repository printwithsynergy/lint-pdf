"""Tests for the public approval-info endpoint surfacing EPM verdict.

The mobile share-link approve flow is token-only auth and can't hit
the tenant-scoped /api/v1/jobs/{id}/epm endpoint. The public
approval-info payload now carries the EPM verdict inline so anonymous
approvers see the tier badge without an API key.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from siftpdf.epm import codes
from tests.api.conftest import PLACEHOLDER_TENANT_ID

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


def _create_chain_with_token(db: Session, *, fired_epm_codes: list[str] | None = None) -> str:
    """Create a job + approval chain + step. Returns the access token."""
    from siftpdf.api.models import (
        ApprovalChain,
        ApprovalStep,
        Job,
        JobFinding,
        JobStatus,
    )

    job = Job(
        id=uuid.uuid4(),
        tenant_id=PLACEHOLDER_TENANT_ID,
        status=JobStatus.COMPLETE,
        profile_id="lintpdf-default",
        file_key="approvals-epm/x.pdf",
        file_name="x.pdf",
        file_size=1,
        result_json={
            "summary": {
                "total_findings": 0,
                "error_count": 0,
                "warning_count": 0,
                "advisory_count": 0,
                "passed": True,
                "page_count": 1,
            }
        },
    )
    db.add(job)
    db.commit()

    for code in fired_epm_codes or []:
        db.add(
            JobFinding(
                id=uuid.uuid4(),
                job_id=job.id,
                inspection_id=code,
                severity="warning",
                message=code,
            )
        )

    chain = ApprovalChain(
        id=uuid.uuid4(),
        tenant_id=PLACEHOLDER_TENANT_ID,
        job_id=job.id,
        status="pending",
        current_step=0,
        steps=[{"name": "Producer review"}],
    )
    db.add(chain)
    db.commit()

    step = ApprovalStep(
        id=uuid.uuid4(),
        chain_id=chain.id,
        step_index=0,
        step_name="Producer review",
        approver_email="approver@example.com",
        access_token="test-token-" + uuid.uuid4().hex[:8],
        decision="pending",
    )
    db.add(step)
    db.commit()
    return step.access_token


def test_public_approval_info_includes_epm_verdict_when_clean(
    client: TestClient, db_session: Session
) -> None:
    token = _create_chain_with_token(db_session)
    resp = client.get(f"/api/v1/approvals/info/{token}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["epm_verdict"] is not None
    assert body["epm_verdict"]["tier"] == "pass"
    assert body["epm_verdict"]["epm_findings_count"] == 0


def test_public_approval_info_surfaces_epm_drivers(client: TestClient, db_session: Session) -> None:
    """Two B-tier findings → reject; both drivers surfaced to mobile."""
    token = _create_chain_with_token(
        db_session,
        fired_epm_codes=[
            codes.EPM_BLEED_BELOW_MIN,
            codes.EPM_PROCESS_COLOR_COUNT,
        ],
    )
    resp = client.get(f"/api/v1/approvals/info/{token}")
    body = resp.json()
    epm = body["epm_verdict"]
    assert epm is not None
    assert epm["tier"] == "reject"
    assert codes.EPM_BLEED_BELOW_MIN in epm["rejection_drivers"]
    assert codes.EPM_PROCESS_COLOR_COUNT in epm["rejection_drivers"]
    assert epm["epm_findings_count"] == 2


def test_public_approval_info_404_for_unknown_token(
    client: TestClient,
) -> None:
    resp = client.get("/api/v1/approvals/info/does-not-exist")
    assert resp.status_code == 404
