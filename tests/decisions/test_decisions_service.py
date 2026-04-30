"""Wave V V-05 — decisions service tests."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lintpdf.api.models import (
    Base,
    Job,
    JobFinding,
    JobStatus,
    Tenant,
    TenantPlan,
)
from lintpdf.decisions import service
from lintpdf.decisions.models import Decision

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session


_TENANT_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
_TENANT_B = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = factory()

    for tid, name in ((_TENANT_A, "tenant-a"), (_TENANT_B, "tenant-b")):
        session.add(
            Tenant(
                id=tid,
                name=name,
                api_key_hash=f"hash-{name}",
                plan=TenantPlan.GROWTH,
                rate_limit_daily=1000,
                max_file_size_mb=50,
            )
        )
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _make_job(db: Session, tenant_id: uuid.UUID) -> Job:
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


def _make_finding(db: Session, job: Job) -> JobFinding:
    f = JobFinding(
        id=uuid.uuid4(),
        job_id=job.id,
        inspection_id="LPDF_F-22",
        severity="warning",
        message="Image below 300 dpi",
    )
    db.add(f)
    db.commit()
    return f


# ---- record_decision ------------------------------------------------------


def test_record_job_level_decision(db: Session):
    job = _make_job(db, _TENANT_A)
    decision = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.APPROVE,
        decided_by_user_id="user_42",
        source="dashboard",
        notes="Looks good for press.",
    )
    db.commit()

    assert decision.id is not None
    assert decision.tenant_id == _TENANT_A
    assert decision.job_id == job.id
    assert decision.finding_id is None
    assert decision.decision_type == "approve"
    assert decision.decided_by_user_id == "user_42"
    assert decision.source == "dashboard"
    assert decision.is_active is True


def test_record_finding_level_decision_with_metadata(db: Session):
    job = _make_job(db, _TENANT_A)
    finding = _make_finding(db, job)

    decision = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        finding_id=finding.id,
        decision_type=service.WAIVE,
        decision_value="press_will_compensate",
        metadata={"approver": "qa@example.com", "channel": "email"},
        decided_by_user_id="user_42",
        decided_by_email="qa@example.com",
        source="dashboard",
        request_id="req_abc123",
    )
    db.commit()

    assert decision.finding_id == finding.id
    assert decision.decision_value == "press_will_compensate"
    assert decision.decision_metadata == {
        "approver": "qa@example.com",
        "channel": "email",
    }
    assert decision.request_id == "req_abc123"


def test_record_decision_rejects_unknown_source(db: Session):
    job = _make_job(db, _TENANT_A)
    with pytest.raises(service.InvalidDecisionError, match="unknown decision source"):
        service.record_decision(
            db,
            tenant_id=_TENANT_A,
            job_id=job.id,
            decision_type=service.APPROVE,
            decided_by_user_id="user_42",
            source="bogus_surface",
        )


def test_record_decision_rejects_empty_actor(db: Session):
    job = _make_job(db, _TENANT_A)
    with pytest.raises(service.InvalidDecisionError, match="decided_by_user_id"):
        service.record_decision(
            db,
            tenant_id=_TENANT_A,
            job_id=job.id,
            decision_type=service.APPROVE,
            decided_by_user_id="",
            source="dashboard",
        )


def test_record_decision_rejects_empty_decision_type(db: Session):
    job = _make_job(db, _TENANT_A)
    with pytest.raises(service.InvalidDecisionError, match="decision_type"):
        service.record_decision(
            db,
            tenant_id=_TENANT_A,
            job_id=job.id,
            decision_type="",
            decided_by_user_id="user_42",
            source="dashboard",
        )


# ---- queries --------------------------------------------------------------


def test_list_for_job_returns_newest_first(db: Session):
    job = _make_job(db, _TENANT_A)
    first = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.ANNOTATE,
        decided_by_user_id="u1",
        source="api",
    )
    db.commit()
    second = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.APPROVE,
        decided_by_user_id="u1",
        source="api",
    )
    db.commit()

    rows = service.list_for_job(db, tenant_id=_TENANT_A, job_id=job.id)
    assert [r.id for r in rows] == [second.id, first.id]


def test_list_for_finding_filters_to_finding(db: Session):
    job = _make_job(db, _TENANT_A)
    finding_a = _make_finding(db, job)
    finding_b = _make_finding(db, job)
    service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        finding_id=finding_a.id,
        decision_type=service.WAIVE,
        decided_by_user_id="u1",
        source="api",
    )
    service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        finding_id=finding_b.id,
        decision_type=service.WAIVE,
        decided_by_user_id="u1",
        source="api",
    )
    db.commit()

    rows_a = service.list_for_finding(db, tenant_id=_TENANT_A, finding_id=finding_a.id)
    assert len(rows_a) == 1
    assert rows_a[0].finding_id == finding_a.id


def test_list_for_actor(db: Session):
    job = _make_job(db, _TENANT_A)
    service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.APPROVE,
        decided_by_user_id="alice",
        source="api",
    )
    service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.APPROVE,
        decided_by_user_id="bob",
        source="api",
    )
    db.commit()
    alice_rows = service.list_for_actor(db, tenant_id=_TENANT_A, actor_user_id="alice")
    assert len(alice_rows) == 1
    assert alice_rows[0].decided_by_user_id == "alice"


def test_cross_tenant_isolation(db: Session):
    job_a = _make_job(db, _TENANT_A)
    job_b = _make_job(db, _TENANT_B)
    service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job_a.id,
        decision_type=service.APPROVE,
        decided_by_user_id="u1",
        source="api",
    )
    service.record_decision(
        db,
        tenant_id=_TENANT_B,
        job_id=job_b.id,
        decision_type=service.REJECT,
        decided_by_user_id="u2",
        source="api",
    )
    db.commit()

    a_rows = service.list_for_job(db, tenant_id=_TENANT_A, job_id=job_a.id)
    b_rows = service.list_for_job(db, tenant_id=_TENANT_B, job_id=job_b.id)
    assert len(a_rows) == 1 and a_rows[0].decision_type == "approve"
    assert len(b_rows) == 1 and b_rows[0].decision_type == "reject"
    # Cross-query: A can't see B's job decisions even if it knew the id
    cross = service.list_for_job(db, tenant_id=_TENANT_A, job_id=job_b.id)
    assert cross == []


# ---- revocation -----------------------------------------------------------


def test_revoke_marks_revoked_at_and_actor(db: Session):
    job = _make_job(db, _TENANT_A)
    decision = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.APPROVE,
        decided_by_user_id="alice",
        source="dashboard",
    )
    db.commit()

    revoked = service.revoke_decision(
        db,
        tenant_id=_TENANT_A,
        decision_id=decision.id,
        revoked_by_user_id="bob",
        revoked_reason="found a press issue post-approval",
    )
    db.commit()
    assert revoked is not None
    assert revoked.revoked_at is not None
    assert revoked.revoked_by_user_id == "bob"
    assert revoked.revoked_reason == "found a press issue post-approval"
    assert revoked.is_active is False


def test_revoke_unknown_returns_none(db: Session):
    result = service.revoke_decision(
        db,
        tenant_id=_TENANT_A,
        decision_id=uuid.uuid4(),
        revoked_by_user_id="alice",
    )
    assert result is None


def test_revoke_cross_tenant_returns_none(db: Session):
    job_a = _make_job(db, _TENANT_A)
    decision_a = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job_a.id,
        decision_type=service.APPROVE,
        decided_by_user_id="alice",
        source="dashboard",
    )
    db.commit()
    # tenant B tries to revoke tenant A's decision
    result = service.revoke_decision(
        db,
        tenant_id=_TENANT_B,
        decision_id=decision_a.id,
        revoked_by_user_id="evilbob",
    )
    assert result is None
    # original is untouched
    refreshed = db.get(Decision, decision_a.id)
    assert refreshed is not None
    assert refreshed.revoked_at is None


def test_revoke_idempotent_keeps_first_revocation_stamp(db: Session):
    job = _make_job(db, _TENANT_A)
    decision = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.APPROVE,
        decided_by_user_id="alice",
        source="dashboard",
    )
    db.commit()

    first = service.revoke_decision(
        db,
        tenant_id=_TENANT_A,
        decision_id=decision.id,
        revoked_by_user_id="bob",
        revoked_reason="reason A",
    )
    db.commit()
    assert first is not None
    first_revoked_at = first.revoked_at
    assert first_revoked_at is not None

    second = service.revoke_decision(
        db,
        tenant_id=_TENANT_A,
        decision_id=decision.id,
        revoked_by_user_id="charlie",
        revoked_reason="reason B",
    )
    db.commit()
    assert second is not None
    # Original revocation stamp preserved.
    assert second.revoked_by_user_id == "bob"
    assert second.revoked_reason == "reason A"
    assert second.revoked_at == first_revoked_at


def test_list_excludes_revoked_by_default(db: Session):
    job = _make_job(db, _TENANT_A)
    keep = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.ANNOTATE,
        decided_by_user_id="alice",
        source="api",
    )
    drop = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.APPROVE,
        decided_by_user_id="alice",
        source="api",
    )
    db.commit()
    service.revoke_decision(
        db,
        tenant_id=_TENANT_A,
        decision_id=drop.id,
        revoked_by_user_id="alice",
    )
    db.commit()

    active = service.list_for_job(db, tenant_id=_TENANT_A, job_id=job.id)
    assert [r.id for r in active] == [keep.id]
    everything = service.list_for_job(db, tenant_id=_TENANT_A, job_id=job.id, include_revoked=True)
    assert {r.id for r in everything} == {keep.id, drop.id}


# ---- latest_active_for_finding -------------------------------------------


def test_latest_active_for_finding(db: Session):
    job = _make_job(db, _TENANT_A)
    finding = _make_finding(db, job)
    older = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        finding_id=finding.id,
        decision_type=service.WAIVE,
        decided_by_user_id="u1",
        source="api",
    )
    newer = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        finding_id=finding.id,
        decision_type=service.SUPPRESS,
        decided_by_user_id="u1",
        source="api",
    )
    db.commit()

    latest = service.latest_active_for_finding(db, tenant_id=_TENANT_A, finding_id=finding.id)
    assert latest is not None
    assert latest.id == newer.id

    # Revoke the newer; older becomes the latest active
    service.revoke_decision(
        db,
        tenant_id=_TENANT_A,
        decision_id=newer.id,
        revoked_by_user_id="u1",
    )
    db.commit()
    latest = service.latest_active_for_finding(db, tenant_id=_TENANT_A, finding_id=finding.id)
    assert latest is not None
    assert latest.id == older.id


# ---- summary --------------------------------------------------------------


def test_summarise_job_decisions_counts_active_only(db: Session):
    job = _make_job(db, _TENANT_A)
    service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.WAIVE,
        decided_by_user_id="u1",
        source="api",
    )
    service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.WAIVE,
        decided_by_user_id="u1",
        source="api",
    )
    revoked = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.WAIVE,
        decided_by_user_id="u1",
        source="api",
    )
    service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.APPROVE,
        decided_by_user_id="u1",
        source="api",
    )
    db.commit()
    service.revoke_decision(
        db,
        tenant_id=_TENANT_A,
        decision_id=revoked.id,
        revoked_by_user_id="u1",
    )
    db.commit()

    rows = service.list_for_job(db, tenant_id=_TENANT_A, job_id=job.id, include_revoked=True)
    counts = service.summarise_job_decisions(rows)
    assert counts == {"waive": 2, "approve": 1}


def test_finding_fk_cascade_on_finding_delete(db: Session):
    """Deleting the parent finding cascades the decision row away."""
    job = _make_job(db, _TENANT_A)
    finding = _make_finding(db, job)
    decision = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        finding_id=finding.id,
        decision_type=service.WAIVE,
        decided_by_user_id="u1",
        source="api",
    )
    db.commit()
    decision_id = decision.id  # capture before cascade detaches the instance

    db.delete(finding)
    db.commit()
    db.expire_all()

    refreshed = db.get(Decision, decision_id)
    assert refreshed is None


def test_job_fk_cascade_on_job_delete(db: Session):
    job = _make_job(db, _TENANT_A)
    decision = service.record_decision(
        db,
        tenant_id=_TENANT_A,
        job_id=job.id,
        decision_type=service.APPROVE,
        decided_by_user_id="u1",
        source="api",
    )
    db.commit()
    decision_id = decision.id

    db.delete(job)
    db.commit()
    db.expire_all()

    refreshed = db.get(Decision, decision_id)
    assert refreshed is None
