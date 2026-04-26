"""Q-E7 — LLM cost-cap enforcement tests."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lintpdf.ai.cost_cap import (
    CAP_TOGGLE_ID,
    CostCapExceededError,
    _month_window,
    alert_threshold_pct,
    check_cap_or_raise,
    is_cap_enabled,
    monthly_cap_cents,
    monthly_usage_cents,
    remaining_cents,
)
from lintpdf.api.models import (
    AIUsageLog,
    Base,
    Tenant,
    TenantPlan,
)
from lintpdf.tenants.toggle_models import (
    MergeStrategy,
    Toggle,
    ToggleOverride,
    ToggleScope,
    ToggleType,
)
from lintpdf.tenants.toggle_registry import seed_category_toggles

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session


_TENANT_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TENANT_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):  # type: ignore[no-untyped-def]
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = factory()
    seed_category_toggles(session)

    for tid, name in ((_TENANT_A, "tenant-a"), (_TENANT_B, "tenant-b")):
        session.add(
            Tenant(
                id=tid,
                name=name,
                api_key_hash=f"hash-{name}",
                plan=TenantPlan.GROWTH,
                rate_limit_daily=1000,
                max_file_size_mb=10,
            )
        )
    session.commit()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def _set_cap_override(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    enabled: bool,
    monthly_cap_cents: int = 0,
    alert_pct: int = 80,
) -> None:
    db.add(
        ToggleOverride(
            id=secrets.token_urlsafe(8),
            toggle_id=CAP_TOGGLE_ID,
            scope=ToggleScope.TENANT,
            scope_id=str(tenant_id),
            value={
                "enabled": enabled,
                "monthly_cap_cents": monthly_cap_cents,
                "alert_threshold_pct": alert_pct,
            },
            locked=False,
            set_by="test",
            surface="test",
        )
    )
    db.commit()


def _add_usage(
    db: Session,
    tenant_id: uuid.UUID,
    cost_cents: int,
    *,
    when: datetime | None = None,
    feature: str = "audit",
) -> None:
    log = AIUsageLog(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=None,
        category=feature,
        feature=feature,
        credits_consumed=cost_cents,
        cost=cost_cents / 100.0,
        processing_time_ms=0,
        cost_cents=cost_cents,
    )
    if when is not None:
        log.created_at = when
    db.add(log)
    db.commit()


# ---- registry default behaviour ------------------------------------------


def test_cap_off_by_default(db: Session):
    """The PR-B1 registry default has enabled=False."""
    assert is_cap_enabled(db, _TENANT_A) is False
    assert monthly_cap_cents(db, _TENANT_A) is None
    # check_cap_or_raise is a no-op
    check_cap_or_raise(db, _TENANT_A, projected_cost_cents=10_000)


def test_cap_off_when_no_registry_row_either(db: Session):
    """Pure-empty DB: no toggle registered + no override → fail-open."""
    db.query(Toggle).filter(Toggle.id == CAP_TOGGLE_ID).delete()
    db.commit()
    assert is_cap_enabled(db, _TENANT_A) is False
    check_cap_or_raise(db, _TENANT_A, projected_cost_cents=99_000)


# ---- enabled cap ---------------------------------------------------------


def test_cap_enabled_under_budget_passes(db: Session):
    _set_cap_override(db, _TENANT_A, enabled=True, monthly_cap_cents=10_000)
    _add_usage(db, _TENANT_A, 1_500)
    assert is_cap_enabled(db, _TENANT_A) is True
    assert monthly_cap_cents(db, _TENANT_A) == 10_000
    assert monthly_usage_cents(db, _TENANT_A) == 1_500
    assert remaining_cents(db, _TENANT_A) == 8_500
    # No raise — well under cap
    check_cap_or_raise(db, _TENANT_A, projected_cost_cents=500)


def test_cap_enabled_at_budget_raises(db: Session):
    _set_cap_override(db, _TENANT_A, enabled=True, monthly_cap_cents=1_000)
    _add_usage(db, _TENANT_A, 1_000)
    with pytest.raises(CostCapExceededError) as exc:
        check_cap_or_raise(db, _TENANT_A)
    assert exc.value.cap_cents == 1_000
    assert exc.value.used_cents == 1_000


def test_cap_enabled_projected_would_exceed_raises(db: Session):
    _set_cap_override(db, _TENANT_A, enabled=True, monthly_cap_cents=1_000)
    _add_usage(db, _TENANT_A, 600)
    # Used 600, projected 500 → 1100 > 1000
    with pytest.raises(CostCapExceededError) as exc:
        check_cap_or_raise(db, _TENANT_A, projected_cost_cents=500)
    assert exc.value.used_cents == 600
    assert exc.value.projected_cents == 500


def test_cap_enabled_with_zero_cap_treated_as_disabled(db: Session):
    """A zero/negative cap value is treated as not configured (fail-open)."""
    _set_cap_override(db, _TENANT_A, enabled=True, monthly_cap_cents=0)
    assert monthly_cap_cents(db, _TENANT_A) is None
    check_cap_or_raise(db, _TENANT_A, projected_cost_cents=10_000)


# ---- monthly window ------------------------------------------------------


def test_month_window_aligned_to_utc():
    moment = datetime(2026, 4, 15, 12, 30, 0, tzinfo=timezone.utc)
    start, end = _month_window(now=moment)
    assert start == datetime(2026, 4, 1, tzinfo=timezone.utc)
    assert end == datetime(2026, 5, 1, tzinfo=timezone.utc)


def test_month_window_year_boundary():
    moment = datetime(2026, 12, 27, tzinfo=timezone.utc)
    start, end = _month_window(now=moment)
    assert start == datetime(2026, 12, 1, tzinfo=timezone.utc)
    assert end == datetime(2027, 1, 1, tzinfo=timezone.utc)


def test_monthly_usage_excludes_prior_month(db: Session):
    """Usage logged before the month boundary doesn't count."""
    _set_cap_override(db, _TENANT_A, enabled=True, monthly_cap_cents=1_000)
    now = datetime(2026, 4, 15, tzinfo=timezone.utc)
    last_month = datetime(2026, 3, 15, tzinfo=timezone.utc)
    _add_usage(db, _TENANT_A, 999, when=last_month)
    _add_usage(db, _TENANT_A, 100, when=now)
    used = monthly_usage_cents(db, _TENANT_A, now=now)
    assert used == 100  # last month's 999 excluded
    check_cap_or_raise(db, _TENANT_A, projected_cost_cents=500, now=now)


def test_monthly_usage_excludes_next_month_pre_run(db: Session):
    """A clock-skewed row from the future gets excluded too."""
    _set_cap_override(db, _TENANT_A, enabled=True, monthly_cap_cents=1_000)
    now = datetime(2026, 4, 15, tzinfo=timezone.utc)
    next_month = datetime(2026, 5, 1, tzinfo=timezone.utc)
    _add_usage(db, _TENANT_A, 9_999, when=next_month)
    used = monthly_usage_cents(db, _TENANT_A, now=now)
    assert used == 0


# ---- cross-tenant --------------------------------------------------------


def test_caps_are_tenant_isolated(db: Session):
    _set_cap_override(db, _TENANT_A, enabled=True, monthly_cap_cents=1_000)
    # Tenant A spent everything; Tenant B has no cap configured
    _add_usage(db, _TENANT_A, 1_000)
    _add_usage(db, _TENANT_B, 500)
    with pytest.raises(CostCapExceededError):
        check_cap_or_raise(db, _TENANT_A)
    # Tenant B is unaffected (no cap)
    check_cap_or_raise(db, _TENANT_B, projected_cost_cents=10_000)


# ---- alert threshold -----------------------------------------------------


def test_alert_threshold_default_80(db: Session):
    """No override → falls back to 80."""
    assert alert_threshold_pct(db, _TENANT_A) == 80


def test_alert_threshold_clamps_to_0_100(db: Session):
    _set_cap_override(
        db, _TENANT_A, enabled=True, monthly_cap_cents=100, alert_pct=150
    )
    assert alert_threshold_pct(db, _TENANT_A) == 100
    _set_cap_override(
        db, _TENANT_B, enabled=True, monthly_cap_cents=100, alert_pct=-5
    )
    assert alert_threshold_pct(db, _TENANT_B) == 0


# ---- malformed override --------------------------------------------------


def test_malformed_override_value_does_not_crash(db: Session):
    """A non-dict value (e.g. accidentally written as int) is ignored."""
    db.add(
        ToggleOverride(
            id=secrets.token_urlsafe(8),
            toggle_id=CAP_TOGGLE_ID,
            scope=ToggleScope.TENANT,
            scope_id=str(_TENANT_A),
            value=42,  # garbage shape
            locked=False,
            set_by="test",
            surface="test",
        )
    )
    db.commit()
    # Should fall back to registry default (enabled=False)
    assert is_cap_enabled(db, _TENANT_A) is False
    check_cap_or_raise(db, _TENANT_A, projected_cost_cents=999_999)


def test_remaining_cents_when_over_cap_goes_negative(db: Session):
    """Negative remaining means tenant has overspent — UI clamps to zero."""
    _set_cap_override(db, _TENANT_A, enabled=True, monthly_cap_cents=100)
    _add_usage(db, _TENANT_A, 250)
    assert remaining_cents(db, _TENANT_A) == -150


def test_remaining_cents_returns_none_when_cap_off(db: Session):
    assert remaining_cents(db, _TENANT_A) is None


# ---- projected_cost defaults ---------------------------------------------


def test_projected_cost_defaults_to_zero(db: Session):
    _set_cap_override(db, _TENANT_A, enabled=True, monthly_cap_cents=1_000)
    _add_usage(db, _TENANT_A, 999)
    # Used + projected(0) = 999 < 1000 → passes
    check_cap_or_raise(db, _TENANT_A)


def test_negative_projected_cost_treated_as_zero(db: Session):
    _set_cap_override(db, _TENANT_A, enabled=True, monthly_cap_cents=1_000)
    _add_usage(db, _TENANT_A, 999)
    # Negative projected gets max(0, x) -> 0; should not exceed
    check_cap_or_raise(db, _TENANT_A, projected_cost_cents=-50)


def test_unrelated_seeded_toggle_does_not_alter_cap(db: Session):
    """Other category toggles in the registry are ignored by the cap reader."""
    # Add a hostile-shaped toggle under a *different* id with the same
    # ``enabled``/``monthly_cap_cents`` keys as the cap. The cost-cap
    # reader must filter strictly by ``CAP_TOGGLE_ID`` and not be misled
    # by lookalike rows.
    db.add(
        Toggle(
            id="some_other_feature",
            category="other",
            human_name="other",
            type=ToggleType.OBJECT,
            default_value={"enabled": True, "monthly_cap_cents": 1},
            override_at=[ToggleScope.TENANT],
            merge_strategy=MergeStrategy.MERGE,
            lockable=False,
        )
    )
    db.commit()
    # ai_cost_cap registry default still has enabled=False
    assert is_cap_enabled(db, _TENANT_A) is False
