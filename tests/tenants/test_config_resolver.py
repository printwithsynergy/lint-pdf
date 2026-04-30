"""Tests for the V-07 ConfigResolver (Wave V, Phase 2)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from siftpdf.api.models import Base, Tenant, TenantPlan
from siftpdf.tenants.config_resolver import ConfigResolver
from siftpdf.tenants.toggle_models import (
    MergeStrategy,
    Toggle,
    ToggleOverride,
    ToggleScope,
    ToggleType,
    Workflow,
)

if TYPE_CHECKING:
    from collections.abc import Generator

TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


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

    session.add(
        Tenant(
            id=TENANT_ID,
            name="Test Tenant",
            api_key_hash="hash_v07_test",
            plan=TenantPlan.GROWTH,
            rate_limit_daily=5000,
            max_file_size_mb=500,
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _add_toggle(
    session: Session,
    *,
    toggle_id: str,
    type_: ToggleType,
    default: object,
    merge: MergeStrategy = MergeStrategy.REPLACE,
    lockable: bool = False,
) -> Toggle:
    t = Toggle(
        id=toggle_id,
        category=toggle_id.split(".")[0],
        human_name=toggle_id,
        type=type_,
        default_value=default,
        override_at=[ToggleScope.TENANT, ToggleScope.WORKFLOW, ToggleScope.CALL],
        merge_strategy=merge,
        lockable=lockable,
    )
    session.add(t)
    session.commit()
    return t


def _add_override(
    session: Session,
    *,
    toggle_id: str,
    scope: ToggleScope,
    scope_id: str,
    value: object,
    locked: bool = False,
) -> None:
    session.add(
        ToggleOverride(
            id=f"ov_{toggle_id}_{scope.value}_{scope_id[:6]}",
            toggle_id=toggle_id,
            scope=scope,
            scope_id=scope_id,
            value=value,
            locked=locked,
            set_by="test",
            surface="api",
        )
    )
    session.commit()


# ---- cascade ordering -----------------------------------------------


def test_default_returned_when_no_overrides(db_session):
    _add_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    resolver = ConfigResolver(db_session, cache_ttl_s=0)
    assert resolver.resolve("checks.F-22", tenant_id=TENANT_ID) == "warn"


def test_tenant_overrides_default(db_session):
    _add_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    _add_override(
        db_session,
        toggle_id="checks.F-22",
        scope=ToggleScope.TENANT,
        scope_id=str(TENANT_ID),
        value="error",
    )
    resolver = ConfigResolver(db_session, cache_ttl_s=0)
    assert resolver.resolve("checks.F-22", tenant_id=TENANT_ID) == "error"


def test_workflow_overrides_tenant(db_session):
    _add_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    _add_override(
        db_session,
        toggle_id="checks.F-22",
        scope=ToggleScope.TENANT,
        scope_id=str(TENANT_ID),
        value="error",
    )
    db_session.add(
        Workflow(
            id="wf_pkg",
            tenant_id=TENANT_ID,
            slug="packaging",
            human_name="Packaging",
        )
    )
    db_session.commit()
    _add_override(
        db_session,
        toggle_id="checks.F-22",
        scope=ToggleScope.WORKFLOW,
        scope_id="wf_pkg",
        value="off",
    )
    resolver = ConfigResolver(db_session, cache_ttl_s=0)
    assert resolver.resolve("checks.F-22", tenant_id=TENANT_ID, workflow_id="wf_pkg") == "off"


def test_call_override_wins(db_session):
    _add_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    _add_override(
        db_session,
        toggle_id="checks.F-22",
        scope=ToggleScope.TENANT,
        scope_id=str(TENANT_ID),
        value="error",
    )
    resolver = ConfigResolver(db_session, cache_ttl_s=0)
    result = resolver.resolve(
        "checks.F-22",
        tenant_id=TENANT_ID,
        call_overrides={"checks.F-22": "info"},
    )
    assert result == "info"


# ---- locked tenant override -----------------------------------------


def test_locked_tenant_override_ignores_call(db_session):
    _add_toggle(
        db_session,
        toggle_id="checks.F-22",
        type_=ToggleType.STRING,
        default="warn",
        lockable=True,
    )
    _add_override(
        db_session,
        toggle_id="checks.F-22",
        scope=ToggleScope.TENANT,
        scope_id=str(TENANT_ID),
        value="error",
        locked=True,
    )
    resolver = ConfigResolver(db_session, cache_ttl_s=0)
    result = resolver.resolve(
        "checks.F-22",
        tenant_id=TENANT_ID,
        call_overrides={"checks.F-22": "off"},
    )
    assert result == "error"  # locked tenant value wins


def test_locked_tenant_override_ignores_workflow(db_session):
    _add_toggle(
        db_session,
        toggle_id="checks.F-22",
        type_=ToggleType.STRING,
        default="warn",
        lockable=True,
    )
    _add_override(
        db_session,
        toggle_id="checks.F-22",
        scope=ToggleScope.TENANT,
        scope_id=str(TENANT_ID),
        value="error",
        locked=True,
    )
    db_session.add(Workflow(id="wf1", tenant_id=TENANT_ID, slug="w", human_name="W"))
    db_session.commit()
    _add_override(
        db_session,
        toggle_id="checks.F-22",
        scope=ToggleScope.WORKFLOW,
        scope_id="wf1",
        value="off",
    )
    resolver = ConfigResolver(db_session, cache_ttl_s=0)
    result = resolver.resolve("checks.F-22", tenant_id=TENANT_ID, workflow_id="wf1")
    assert result == "error"


# ---- merge strategies -----------------------------------------------


def test_merge_strategy_object_per_key(db_session):
    _add_toggle(
        db_session,
        toggle_id="epm_thresholds.rich_black_recipe",
        type_=ToggleType.OBJECT,
        default={"C": 60, "M": 40, "Y": 40, "K": 100},
        merge=MergeStrategy.MERGE,
    )
    _add_override(
        db_session,
        toggle_id="epm_thresholds.rich_black_recipe",
        scope=ToggleScope.TENANT,
        scope_id=str(TENANT_ID),
        value={"K": 90},
    )
    resolver = ConfigResolver(db_session, cache_ttl_s=0)
    result = resolver.resolve("epm_thresholds.rich_black_recipe", tenant_id=TENANT_ID)
    assert result == {"C": 60, "M": 40, "Y": 40, "K": 90}


def test_merge_strategy_union_arrays(db_session):
    _add_toggle(
        db_session,
        toggle_id="ai_features",
        type_=ToggleType.OBJECT,
        default=["audit"],
        merge=MergeStrategy.UNION,
    )
    _add_override(
        db_session,
        toggle_id="ai_features",
        scope=ToggleScope.TENANT,
        scope_id=str(TENANT_ID),
        value=["ocr", "dieline"],
    )
    resolver = ConfigResolver(db_session, cache_ttl_s=0)
    result = resolver.resolve(
        "ai_features",
        tenant_id=TENANT_ID,
        call_overrides={"ai_features": ["audit", "legend"]},
    )
    # union of all three layers, dedup, original order preserved
    assert result == ["audit", "ocr", "dieline", "legend"]


# ---- batch resolve --------------------------------------------------


def test_resolve_many_returns_dict(db_session):
    _add_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    _add_toggle(db_session, toggle_id="checks.F-23", type_=ToggleType.BOOLEAN, default=True)
    resolver = ConfigResolver(db_session, cache_ttl_s=0)
    out = resolver.resolve_many(["checks.F-22", "checks.F-23"], tenant_id=TENANT_ID)
    assert out == {"checks.F-22": "warn", "checks.F-23": True}


def test_resolve_many_skips_unknown_toggles(db_session):
    _add_toggle(db_session, toggle_id="checks.F-22", type_=ToggleType.STRING, default="warn")
    resolver = ConfigResolver(db_session, cache_ttl_s=0)
    out = resolver.resolve_many(["checks.F-22", "checks.NEVER"], tenant_id=TENANT_ID)
    assert out == {"checks.F-22": "warn"}


def test_resolve_unknown_toggle_raises(db_session):
    resolver = ConfigResolver(db_session, cache_ttl_s=0)
    with pytest.raises(KeyError, match=r"checks\.GHOST"):
        resolver.resolve("checks.GHOST", tenant_id=TENANT_ID)


# ---- cache + invalidation ------------------------------------------


def test_cache_returns_same_snapshot_within_ttl(db_session):
    _add_toggle(db_session, toggle_id="x", type_=ToggleType.STRING, default="default")
    resolver = ConfigResolver(db_session, cache_ttl_s=60)
    first = resolver.resolve("x", tenant_id=TENANT_ID)

    _add_override(
        db_session,
        toggle_id="x",
        scope=ToggleScope.TENANT,
        scope_id=str(TENANT_ID),
        value="overridden",
    )
    second = resolver.resolve("x", tenant_id=TENANT_ID)
    assert first == "default"
    assert second == "default"  # cache hit — does NOT see override


def test_invalidate_picks_up_new_override(db_session):
    _add_toggle(db_session, toggle_id="x", type_=ToggleType.STRING, default="default")
    resolver = ConfigResolver(db_session, cache_ttl_s=60)
    resolver.resolve("x", tenant_id=TENANT_ID)
    _add_override(
        db_session,
        toggle_id="x",
        scope=ToggleScope.TENANT,
        scope_id=str(TENANT_ID),
        value="overridden",
    )
    resolver.invalidate(tenant_id=TENANT_ID)
    assert resolver.resolve("x", tenant_id=TENANT_ID) == "overridden"


def test_invalidate_all_clears_every_tenant(db_session):
    _add_toggle(db_session, toggle_id="x", type_=ToggleType.STRING, default="d")
    resolver = ConfigResolver(db_session, cache_ttl_s=60)
    resolver.resolve("x", tenant_id=TENANT_ID)
    resolver.invalidate()
    assert resolver._cache == {}
