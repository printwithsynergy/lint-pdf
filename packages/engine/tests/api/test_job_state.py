"""Tests for ``GET /api/v1/jobs/{id}/state`` + ``?include=comments`` on annotations.

Covers:

- Empty job (no approvals, no annotations, no reports) -- every optional
  section returns the expected empty/null shape.
- Full job -- approval chain + annotations with comments + report tokens
  are stitched correctly into one response.
- ``?include=`` filter -- passing a subset returns only those keys; unknown
  keys 422.
- 404 on unknown job / cross-tenant access.
- Annotations ``?include=comments`` returns the richer shape with
  ``comments: []`` embedded per annotation, and back-compat shape is
  unchanged when the param is absent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest

from lintpdf.api.models import (
    ApprovalChain,
    ApprovalStep,
    Job,
    JobStatus,
    ReportToken,
    Tenant,
    TenantPlan,
    ViewerAnnotation,
    ViewerAnnotationComment,
)
from tests.api.conftest import PLACEHOLDER_TENANT_ID

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session


def _seed_complete_job(db: Session, *, tenant_id: uuid.UUID = PLACEHOLDER_TENANT_ID) -> Job:
    """Create a COMPLETE job with a minimal result_json so /state can read verdict + summary."""
    job = Job(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        profile_id="lintpdf-default",
        file_name="sample.pdf",
        file_size=1234,
        file_key=f"tenants/{tenant_id}/jobs/dummy.pdf",
        status=JobStatus.COMPLETE,
        result_json={
            "summary": {
                "total_findings": 2,
                "error_count": 0,
                "warning_count": 1,
                "advisory_count": 1,
                "passed": True,
                "page_count": 1,
                "file_size_bytes": 1234,
            },
            "metadata": {},
            "findings": [],
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_state_empty_job(client: TestClient, db_session: Session) -> None:
    """Brand-new complete job — no approvals, no annotations, no reports."""
    job = _seed_complete_job(db_session)

    resp = client.get(f"/api/v1/jobs/{job.id}/state")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["job"]["job_id"] == str(job.id)
    assert body["reports"] == []
    assert body["approval_chain"] is None
    assert body["verdict"]["verdict"] is None
    assert body["verdict"]["auto_passed"] is True
    assert body["annotations"]["total"] == 0
    assert body["annotations"]["items"] == []


def test_state_stitches_every_section(client: TestClient, db_session: Session) -> None:
    """Seed a fully-populated job (approvals + annotations + reports) and verify stitching."""
    job = _seed_complete_job(db_session)

    # Approval chain with one decided step carrying notes
    chain = ApprovalChain(
        id=uuid.uuid4(),
        job_id=job.id,
        tenant_id=job.tenant_id,
        template_id=None,
        steps=[{"name": "Print ops", "approvers": [{"email": "ops@example.com"}]}],
        status="approved",
        current_step=0,
    )
    db_session.add(chain)
    db_session.flush()
    step = ApprovalStep(
        id=uuid.uuid4(),
        chain_id=chain.id,
        step_index=0,
        step_name="Print ops",
        approver_email="ops@example.com",
        decision="approved",
        notes="Looks great, ship it.",
        decided_at=datetime.now(timezone.utc),
        access_token=uuid.uuid4().hex,
    )
    db_session.add(step)

    # One annotation + one comment
    ann = ViewerAnnotation(
        id=uuid.uuid4(),
        job_id=job.id,
        tenant_id=job.tenant_id,
        share_token=None,
        page_num=1,
        kind="rect",
        geometry_json={"x": 10, "y": 10, "w": 100, "h": 50},
        color="#dc2626",
        text="Fix the bleed",
        author_email="reviewer@example.com",
    )
    db_session.add(ann)
    db_session.flush()
    comment = ViewerAnnotationComment(
        id=uuid.uuid4(),
        annotation_id=ann.id,
        tenant_id=job.tenant_id,
        share_token=None,
        author_email="reviewer@example.com",
        body="Will do by EOD.",
    )
    db_session.add(comment)

    # One report token so /state.reports is non-empty
    tok = ReportToken(
        id=uuid.uuid4(),
        job_id=job.id,
        tenant_id=job.tenant_id,
        token="test-token-abc",
        format="pdf",
        allow_annotations=False,
        require_visitor_email=None,
    )
    db_session.add(tok)
    db_session.commit()

    resp = client.get(f"/api/v1/jobs/{job.id}/state")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Reports
    assert len(body["reports"]) == 1
    assert body["reports"][0]["format"] == "pdf"
    assert body["reports"][0]["token"] == "test-token-abc"
    assert body["reports"][0]["allow_annotations"] is False

    # Approval chain
    assert body["approval_chain"] is not None
    assert body["approval_chain"]["status"] == "approved"
    hist = body["approval_chain"]["step_history"]
    assert len(hist) == 1
    assert hist[0]["notes"] == "Looks great, ship it."
    assert hist[0]["decision"] == "approved"

    # Annotations — comment embedded inline (no N+1 from the client)
    assert body["annotations"]["total"] == 1
    assert body["annotations"]["by_page"] == {"1": 1}
    items = body["annotations"]["items"]
    assert len(items) == 1
    assert items[0]["kind"] == "rect"
    assert items[0]["comments"][0]["body"] == "Will do by EOD."


def test_state_include_filter_trims_payload(client: TestClient, db_session: Session) -> None:
    """``?include=verdict`` returns only the verdict section, no reports/annotations/chain."""
    job = _seed_complete_job(db_session)

    resp = client.get(f"/api/v1/jobs/{job.id}/state", params={"include": "verdict"})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["verdict"]["auto_passed"] is True
    assert body["reports"] is None
    assert body["approval_chain"] is None
    assert body["annotations"] is None


def test_state_include_rejects_unknown_key(client: TestClient, db_session: Session) -> None:
    job = _seed_complete_job(db_session)
    resp = client.get(f"/api/v1/jobs/{job.id}/state", params={"include": "not-a-section"})
    assert resp.status_code == 422
    assert "not-a-section" in resp.text


def test_state_404_on_unknown_job(client: TestClient) -> None:
    missing = uuid.uuid4()
    resp = client.get(f"/api/v1/jobs/{missing}/state")
    assert resp.status_code == 404


def test_state_404_on_cross_tenant_job(client: TestClient, db_session: Session) -> None:
    """A job belonging to another tenant must not leak via /state."""
    other_tenant = Tenant(
        id=uuid.uuid4(),
        name="Other Tenant",
        api_key_hash="other_hash",
        plan=TenantPlan.GROWTH,
        rate_limit_daily=5000,
        max_file_size_mb=500,
    )
    db_session.add(other_tenant)
    db_session.commit()
    job = _seed_complete_job(db_session, tenant_id=other_tenant.id)

    resp = client.get(f"/api/v1/jobs/{job.id}/state")
    assert resp.status_code == 404


def test_annotations_include_comments_embeds_thread(
    client: TestClient, db_session: Session
) -> None:
    """``?include=comments`` on list_annotations_auth embeds the thread inline."""
    job = _seed_complete_job(db_session)

    ann = ViewerAnnotation(
        id=uuid.uuid4(),
        job_id=job.id,
        tenant_id=job.tenant_id,
        share_token=None,
        page_num=2,
        kind="note",
        geometry_json={"x": 50, "y": 50},
        color="#ff0000",
        text=None,
        author_email="r@example.com",
    )
    db_session.add(ann)
    db_session.flush()
    for body in ("first", "second"):
        db_session.add(
            ViewerAnnotationComment(
                id=uuid.uuid4(),
                annotation_id=ann.id,
                tenant_id=job.tenant_id,
                share_token=None,
                author_email="r@example.com",
                body=body,
            )
        )
    db_session.commit()

    # Back-compat: no include -> flat shape (no comments key)
    resp = client.get(f"/api/v1/viewer/jobs/{job.id}/annotations")
    assert resp.status_code == 200, resp.text
    bare = resp.json()
    assert len(bare) == 1
    assert "comments" not in bare[0]

    # include=comments -> nested shape
    resp = client.get(
        f"/api/v1/viewer/jobs/{job.id}/annotations",
        params={"include": "comments"},
    )
    assert resp.status_code == 200, resp.text
    rich = resp.json()
    assert len(rich) == 1
    assert len(rich[0]["comments"]) == 2
    assert [c["body"] for c in rich[0]["comments"]] == ["first", "second"]


def test_annotations_include_rejects_unknown_key(client: TestClient, db_session: Session) -> None:
    job = _seed_complete_job(db_session)
    resp = client.get(
        f"/api/v1/viewer/jobs/{job.id}/annotations",
        params={"include": "comment"},  # typo
    )
    assert resp.status_code == 422


@pytest.mark.parametrize("include", ["", None])
def test_annotations_blank_include_is_back_compat(
    client: TestClient, db_session: Session, include: str | None
) -> None:
    job = _seed_complete_job(db_session)
    params = {} if include is None else {"include": include}
    resp = client.get(f"/api/v1/viewer/jobs/{job.id}/annotations", params=params)
    assert resp.status_code == 200
    assert resp.json() == []
