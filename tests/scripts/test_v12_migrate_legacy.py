"""Tests for V-12 legacy settings migration script."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lintpdf.api.models import Base, Tenant, TenantPlan
from lintpdf.scripts.v12_migrate_legacy import (
    LEGACY_TOGGLE_MAP,
    ensure_toggles_seeded,
    migrate_tenant,
    run,
)
from lintpdf.tenants.toggle_models import (
    Toggle,
    ToggleAuditLog,
    ToggleOverride,
    ToggleScope,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fks(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _add_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID | None = None,
    overrides: dict | None = None,
    is_active: bool = True,
) -> Tenant:
    tid = tenant_id or uuid.uuid4()
    t = Tenant(
        id=tid,
        name=f"Tenant {tid.hex[:6]}",
        api_key_hash=f"hash_{tid.hex[:12]}",
        plan=TenantPlan.GROWTH,
        rate_limit_daily=10,
        max_file_size_mb=10,
        is_active=is_active,
        entitlement_overrides=overrides,
    )
    session.add(t)
    session.commit()
    return t


# ---- registry seeding -------------------------------------------------


def test_ensure_toggles_seeded_inserts_all_specs(db_session: Session):
    created = ensure_toggles_seeded(db_session)
    assert created == len(LEGACY_TOGGLE_MAP)
    db_session.commit()
    rows = db_session.execute(select(Toggle)).scalars().all()
    assert {r.id for r in rows} == {spec.toggle_id for spec in LEGACY_TOGGLE_MAP}


def test_ensure_toggles_seeded_is_idempotent(db_session: Session):
    ensure_toggles_seeded(db_session)
    db_session.commit()
    second = ensure_toggles_seeded(db_session)
    assert second == 0


def test_ensure_toggles_seeded_dry_run_writes_nothing(db_session: Session):
    pretended = ensure_toggles_seeded(db_session, dry_run=True)
    assert pretended == len(LEGACY_TOGGLE_MAP)
    db_session.commit()
    assert db_session.execute(select(Toggle)).scalars().all() == []


# ---- per-tenant migration --------------------------------------------


def test_migrate_tenant_creates_overrides_for_present_keys(db_session: Session):
    ensure_toggles_seeded(db_session)
    db_session.commit()
    tenant = _add_tenant(
        db_session,
        overrides={
            "ai_features": ["audit", "ocr"],
            "monthly_files": 5000,
            "default_profile_id": "custom-profile",
        },
    )
    stats = migrate_tenant(db_session, tenant)
    db_session.commit()
    assert stats.created == 3
    assert stats.skipped == 0
    assert stats.absent == len(LEGACY_TOGGLE_MAP) - 3

    rows = (
        db_session.execute(select(ToggleOverride).where(ToggleOverride.scope_id == str(tenant.id)))
        .scalars()
        .all()
    )
    by_id = {r.toggle_id: r for r in rows}
    assert by_id["ai_features"].value == ["audit", "ocr"]
    assert by_id["limits.monthly_files"].value == 5000
    assert by_id["defaults.profile_id"].value == "custom-profile"


def test_migrate_tenant_idempotent_when_value_unchanged(db_session: Session):
    ensure_toggles_seeded(db_session)
    db_session.commit()
    tenant = _add_tenant(
        db_session,
        overrides={"monthly_files": 5000},
    )
    migrate_tenant(db_session, tenant)
    db_session.commit()

    stats = migrate_tenant(db_session, tenant)
    db_session.commit()
    assert stats.created == 0
    assert stats.skipped == 1


def test_migrate_tenant_updates_existing_v12_row_on_value_change(
    db_session: Session,
):
    ensure_toggles_seeded(db_session)
    db_session.commit()
    tenant = _add_tenant(
        db_session,
        overrides={"monthly_files": 5000},
    )
    migrate_tenant(db_session, tenant)
    db_session.commit()

    tenant.entitlement_overrides = {"monthly_files": 9999}
    db_session.commit()
    stats = migrate_tenant(db_session, tenant)
    db_session.commit()
    assert stats.created == 0
    assert stats.skipped == 1
    row = db_session.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == "limits.monthly_files",
            ToggleOverride.scope_id == str(tenant.id),
        )
    ).scalar_one()
    assert row.value == 9999


def test_migrate_tenant_does_not_touch_manually_set_overrides(
    db_session: Session,
):
    ensure_toggles_seeded(db_session)
    db_session.commit()
    tenant = _add_tenant(
        db_session,
        overrides={"monthly_files": 5000},
    )
    db_session.add(
        ToggleOverride(
            id="manual_row",
            toggle_id="limits.monthly_files",
            scope=ToggleScope.TENANT,
            scope_id=str(tenant.id),
            value=42,
            locked=False,
            set_by="ops_admin",
            surface="api",
        )
    )
    db_session.commit()

    migrate_tenant(db_session, tenant)
    db_session.commit()
    row = db_session.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == "limits.monthly_files",
            ToggleOverride.scope_id == str(tenant.id),
        )
    ).scalar_one()
    assert row.value == 42  # untouched
    assert row.set_by == "ops_admin"


def test_migrate_tenant_no_overrides_returns_zero(db_session: Session):
    ensure_toggles_seeded(db_session)
    db_session.commit()
    tenant = _add_tenant(db_session, overrides=None)
    stats = migrate_tenant(db_session, tenant)
    assert stats.created == 0
    assert stats.skipped == 0
    assert stats.absent == 0


def test_migrate_tenant_dry_run_no_db_writes(db_session: Session):
    ensure_toggles_seeded(db_session)
    db_session.commit()
    tenant = _add_tenant(
        db_session,
        overrides={"monthly_files": 5000},
    )
    stats = migrate_tenant(db_session, tenant, dry_run=True)
    db_session.rollback()
    assert stats.created == 1
    assert (
        db_session.execute(select(ToggleOverride).where(ToggleOverride.scope_id == str(tenant.id)))
        .scalars()
        .all()
        == []
    )


# ---- run() orchestration --------------------------------------------


def test_run_skips_inactive_tenants(db_session: Session):
    active = _add_tenant(db_session, overrides={"monthly_files": 100})
    inactive = _add_tenant(db_session, overrides={"monthly_files": 100}, is_active=False)
    all_stats, _ = run(db_session)
    tenant_ids = {s.tenant_id for s in all_stats}
    assert active.id in tenant_ids
    assert inactive.id not in tenant_ids


def test_run_filters_by_tenant_id(db_session: Session):
    a = _add_tenant(db_session, overrides={"monthly_files": 100})
    _b = _add_tenant(db_session, overrides={"monthly_files": 200})
    all_stats, _ = run(db_session, tenant_id=a.id)
    assert len(all_stats) == 1
    assert all_stats[0].tenant_id == a.id


def test_run_writes_audit_rows(db_session: Session):
    tenant = _add_tenant(db_session, overrides={"ai_features": ["audit"]})
    run(db_session)
    audit_rows = (
        db_session.execute(select(ToggleAuditLog).where(ToggleAuditLog.tenant_id == tenant.id))
        .scalars()
        .all()
    )
    assert len(audit_rows) == 1
    assert audit_rows[0].action == "CREATE"
    assert audit_rows[0].actor == "v12_migration"
    assert audit_rows[0].surface == "script"
    assert audit_rows[0].after_value == ["audit"]


def test_run_dry_run_writes_nothing(db_session: Session):
    tenant = _add_tenant(db_session, overrides={"monthly_files": 100})
    run(db_session, dry_run=True)
    assert (
        db_session.execute(select(ToggleOverride).where(ToggleOverride.scope_id == str(tenant.id)))
        .scalars()
        .all()
        == []
    )
    assert db_session.execute(select(ToggleAuditLog)).scalars().all() == []
