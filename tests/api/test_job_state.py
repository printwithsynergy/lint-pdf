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
    Job,
    JobStatus,
    ReportToken,
    Tenant,
    TenantPlan,
    ViewerAnnotation,
    ViewerAnnotationComment,
)
from lintpdf.api.schemas import JobStateApprovalChain, JobStateApprovalStep
from lintpdf.services.approvals import set_approvals_service
from tests.api.conftest import PLACEHOLDER_TENANT_ID


# In-memory ledger of (chain_dict, [step_dicts]) keyed by (job_id, tenant_id).
# The OSS engine no longer ships ``ApprovalChain`` / ``ApprovalStep`` ORM
# models (W6c-5f); the test fixture uses plain Python objects to drive the
# ``ApprovalsService`` Protocol contract.
_APPROVAL_LEDGER: list[dict] = []


class _StubApprovalChain:
    """Attribute-bag stub. Tests construct one to seed the ledger."""

    def __init__(self, **kw):  # type: ignore[no-untyped-def]
        for k, v in kw.items():
            setattr(self, k, v)
        # Default the steps list so callers don't need to pass it.
        if not hasattr(self, "_steps"):
            self._steps: list[_StubApprovalStep] = []


class _StubApprovalStep:
    """Attribute-bag stub for an ApprovalStep row."""

    def __init__(self, **kw):  # type: ignore[no-untyped-def]
        for k, v in kw.items():
            setattr(self, k, v)


# Aliases the test asserts directly construct.
ApprovalChain = _StubApprovalChain
ApprovalStep = _StubApprovalStep


def _seed_chain(db_session, chain: _StubApprovalChain) -> None:  # type: ignore[no-untyped-def]
    _APPROVAL_LEDGER.append(
        {
            "chain": chain,
            "steps": chain._steps,
            "job_id": chain.job_id,
            "tenant_id": chain.tenant_id,
        }
    )


class _LedgerApprovalsService:
    """Test-side service backed by ``_APPROVAL_LEDGER``.

    No real ORM queries — the test seeds via ``_seed_chain`` instead of
    ``db.add(...)``. Mirrors the JobStateApprovalChain assembly the
    previous in-tree block ran.
    """

    def get_approval_chain_state(self, job_id, tenant_id, db):  # type: ignore[no-untyped-def]
        for entry in _APPROVAL_LEDGER:
            if entry["job_id"] == job_id and entry["tenant_id"] == tenant_id:
                chain = entry["chain"]
                steps = entry["steps"]
                return JobStateApprovalChain(
                    id=str(chain.id),
                    template_id=str(chain.template_id) if chain.template_id else None,
                    status=chain.status,
                    current_step=chain.current_step,
                    step_history=[
                        JobStateApprovalStep(
                            step_index=s.step_index,
                            step_name=s.step_name,
                            approver_email=s.approver_email,
                            decision=s.decision,
                            notes=s.notes,
                            decided_at=s.decided_at,
                        )
                        for s in steps
                    ],
                    created_at=getattr(chain, "created_at", None) or datetime.now(timezone.utc),
                    completed_at=getattr(chain, "completed_at", None),
                )
        return None

    def process_timeouts(self, db):  # type: ignore[no-untyped-def]
        return {}


@pytest.fixture(autouse=True)
def _install_approvals_service():  # type: ignore[no-untyped-def]
    _APPROVAL_LEDGER.clear()
    set_approvals_service(_LedgerApprovalsService())
    yield
    _APPROVAL_LEDGER.clear()
    set_approvals_service(None)


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

    # Approval chain with one decided step carrying notes — seeded via
    # the in-memory ledger (no ORM since W6c-5f extracted these models).
    chain = ApprovalChain(
        id=uuid.uuid4(),
        job_id=job.id,
        tenant_id=job.tenant_id,
        template_id=None,
        status="approved",
        current_step=0,
        completed_at=None,
    )
    chain._steps = [
        ApprovalStep(
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
    ]
    _seed_chain(db_session, chain)

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
