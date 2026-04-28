"""Phase 0.7 PR-A — ResolvedConfigSnapshot writer tests."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from lintpdf.api.models import Base, Job, JobStatus, Tenant, TenantPlan
from lintpdf.tenants.snapshot import write_snapshot
from lintpdf.tenants.toggle_models import (
    MergeStrategy,
    ResolvedConfigSnapshot,
    Toggle,
    ToggleOverride,
    ToggleScope,
    ToggleType,
    Workflow,
)

if TYPE_CHECKING:
    from collections.abc import Generator


_TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


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
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()
    session.add(
        Tenant(
            id=_TENANT_ID,
            name="snapshot-test",
            api_key_hash="x",
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


def _seed_toggle(
    db: Session,
    *,
    toggle_id: str,
    default: object = "warn",
    type_: ToggleType = ToggleType.STRING,
    merge: MergeStrategy = MergeStrategy.REPLACE,
    lockable: bool = False,
    override_at: list[ToggleScope] | None = None,
) -> Toggle:
    t = Toggle(
        id=toggle_id,
        category=toggle_id.split(".")[0],
        human_name=toggle_id,
        type=type_,
        default_value=default,
        override_at=override_at
        or [ToggleScope.TENANT, ToggleScope.WORKFLOW, ToggleScope.CALL],
        merge_strategy=merge,
        lockable=lockable,
    )
    db.add(t)
    db.commit()
    return t


def _make_job(db: Session) -> Job:
    job = Job(
        id=uuid.uuid4(),
        tenant_id=_TENANT_ID,
        status=JobStatus.PENDING,
        profile_id="lintpdf-default",
        file_key="x/y.pdf",
        file_name="y.pdf",
        file_size=1,
    )
    db.add(job)
    db.commit()
    return job


def test_snapshot_records_default_when_no_overrides(db: Session):
    _seed_toggle(db, toggle_id="checks.F-22", default="warn")
    job = _make_job(db)

    row = write_snapshot(
        db,
        job_id=job.id,
        tenant_id=_TENANT_ID,
        workflow_id=None,
    )
    db.commit()

    assert row.resolved_payload == {"checks.F-22": "warn"}
    assert row.provenance == {"checks.F-22": "system"}
    assert row.workflow_id is None
    assert row.tenant_id == _TENANT_ID
    assert row.job_id == job.id


def test_snapshot_records_tenant_override(db: Session):
    _seed_toggle(db, toggle_id="checks.F-22", default="warn")
    db.add(
        ToggleOverride(
            id=secrets.token_urlsafe(8),
            toggle_id="checks.F-22",
            scope=ToggleScope.TENANT,
            scope_id=str(_TENANT_ID),
            value="error",
            locked=False,
            set_by="test",
            surface="test",
        )
    )
    db.commit()
    job = _make_job(db)

    row = write_snapshot(db, job_id=job.id, tenant_id=_TENANT_ID, workflow_id=None)
    db.commit()

    assert row.resolved_payload == {"checks.F-22": "error"}
    assert row.provenance == {"checks.F-22": "tenant"}


def test_snapshot_records_workflow_override(db: Session):
    _seed_toggle(db, toggle_id="checks.F-22", default="warn")
    wf = Workflow(
        id="wf-1",
        tenant_id=_TENANT_ID,
        slug="wf",
        human_name="WF",
        is_default=False,
        is_active=True,
        response_mode="async",
        server_revision=1,
    )
    db.add(wf)
    db.add(
        ToggleOverride(
            id=secrets.token_urlsafe(8),
            toggle_id="checks.F-22",
            scope=ToggleScope.WORKFLOW,
            scope_id=wf.id,
            value="error",
            locked=False,
            set_by="test",
            surface="test",
        )
    )
    db.commit()
    job = _make_job(db)

    row = write_snapshot(db, job_id=job.id, tenant_id=_TENANT_ID, workflow_id=wf.id)
    db.commit()

    assert row.resolved_payload == {"checks.F-22": "error"}
    assert row.provenance == {"checks.F-22": "workflow"}
    assert row.workflow_id == wf.id


def test_snapshot_records_call_override(db: Session):
    _seed_toggle(db, toggle_id="checks.F-22", default="warn")
    job = _make_job(db)

    row = write_snapshot(
        db,
        job_id=job.id,
        tenant_id=_TENANT_ID,
        workflow_id=None,
        call_overrides={"checks.F-22": "advisory"},
    )
    db.commit()

    assert row.resolved_payload == {"checks.F-22": "advisory"}
    assert row.provenance == {"checks.F-22": "call"}


def test_snapshot_locked_tenant_short_circuits_call(db: Session):
    _seed_toggle(db, toggle_id="checks.F-22", default="warn", lockable=True)
    db.add(
        ToggleOverride(
            id=secrets.token_urlsafe(8),
            toggle_id="checks.F-22",
            scope=ToggleScope.TENANT,
            scope_id=str(_TENANT_ID),
            value="error",
            locked=True,
            set_by="admin",
            surface="dashboard",
        )
    )
    db.commit()
    job = _make_job(db)

    row = write_snapshot(
        db,
        job_id=job.id,
        tenant_id=_TENANT_ID,
        workflow_id=None,
        call_overrides={"checks.F-22": "advisory"},  # ignored
    )
    db.commit()

    # Call value is shadowed because tenant is locked
    assert row.resolved_payload == {"checks.F-22": "error"}
    assert row.provenance == {"checks.F-22": "tenant"}


def test_snapshot_records_multiple_toggles_with_mixed_provenance(db: Session):
    _seed_toggle(db, toggle_id="checks.F-22", default="warn")
    _seed_toggle(db, toggle_id="checks.F-23", default="warn")
    _seed_toggle(db, toggle_id="checks.F-24", default="warn")

    db.add(
        ToggleOverride(
            id=secrets.token_urlsafe(8),
            toggle_id="checks.F-23",
            scope=ToggleScope.TENANT,
            scope_id=str(_TENANT_ID),
            value="error",
            locked=False,
            set_by="t",
            surface="api",
        )
    )
    db.commit()
    job = _make_job(db)

    row = write_snapshot(
        db,
        job_id=job.id,
        tenant_id=_TENANT_ID,
        workflow_id=None,
        call_overrides={"checks.F-24": "advisory"},
    )
    db.commit()

    assert row.resolved_payload == {
        "checks.F-22": "warn",
        "checks.F-23": "error",
        "checks.F-24": "advisory",
    }
    assert row.provenance == {
        "checks.F-22": "system",
        "checks.F-23": "tenant",
        "checks.F-24": "call",
    }


def test_snapshot_persists_system_default_version(db: Session):
    _seed_toggle(db, toggle_id="checks.F-22", default="warn")
    job = _make_job(db)
    row = write_snapshot(
        db,
        job_id=job.id,
        tenant_id=_TENANT_ID,
        workflow_id=None,
        system_default_version="custom-7",
    )
    db.commit()
    assert row.system_default_version == "custom-7"


def test_snapshot_round_trip_via_query(db: Session):
    _seed_toggle(db, toggle_id="checks.F-22", default="warn")
    job = _make_job(db)
    write_snapshot(db, job_id=job.id, tenant_id=_TENANT_ID, workflow_id=None)
    db.commit()

    fetched = db.get(ResolvedConfigSnapshot, job.id)
    assert fetched is not None
    assert fetched.resolved_payload == {"checks.F-22": "warn"}
    assert fetched.provenance == {"checks.F-22": "system"}
    assert isinstance(fetched.created_at, datetime)
    assert fetched.created_at.tzinfo is not None or fetched.created_at <= datetime.now(
        tz=timezone.utc
    ).replace(tzinfo=None)
