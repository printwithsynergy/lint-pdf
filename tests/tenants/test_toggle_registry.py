"""Phase 0.7 PR-B1 — toggle category registry seed tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lintpdf.api.models import Base
from lintpdf.tenants.toggle_models import (
    MergeStrategy,
    Toggle,
    ToggleScope,
    ToggleType,
)
from lintpdf.tenants.toggle_registry import (
    CATEGORY_REGISTRY,
    seed_category_toggles,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session


_EXPECTED_CATEGORY_IDS = frozenset(
    {
        "profile_rules",
        "brand",
        "approval_template",
        "import_mapping",
        "endpoint_defaults",
        "epm_thresholds",
        "ai_cost_cap",
        "response_format",
        "viewer_capabilities",
    }
)


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
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_registry_lists_all_nine_categories():
    ids = {spec.toggle_id for spec in CATEGORY_REGISTRY}
    assert ids == _EXPECTED_CATEGORY_IDS


def test_seed_creates_all_nine_rows(db: Session):
    created = seed_category_toggles(db)
    db.commit()

    assert created == 9
    rows = db.query(Toggle).all()
    assert {r.id for r in rows} == _EXPECTED_CATEGORY_IDS


def test_seed_is_idempotent(db: Session):
    first = seed_category_toggles(db)
    db.commit()
    second = seed_category_toggles(db)
    db.commit()
    third = seed_category_toggles(db)
    db.commit()

    assert first == 9
    assert second == 0
    assert third == 0
    assert db.query(Toggle).count() == 9


def test_seed_respects_existing_rows_unchanged(db: Session):
    """A pre-existing row with mutated default_value is left alone."""
    db.add(
        Toggle(
            id="profile_rules",
            category="profile_rules",
            human_name="custom",
            type=ToggleType.OBJECT,
            default_value={"already_seeded": True},
            override_at=[ToggleScope.TENANT],
            merge_strategy=MergeStrategy.REPLACE,
            lockable=True,
        )
    )
    db.commit()

    created = seed_category_toggles(db)
    db.commit()

    assert created == 8  # only the other 8 categories
    row = db.get(Toggle, "profile_rules")
    assert row is not None
    assert row.default_value == {"already_seeded": True}
    assert row.lockable is True  # untouched


def test_dry_run_does_not_insert(db: Session):
    created = seed_category_toggles(db, dry_run=True)
    assert created == 9
    assert db.query(Toggle).count() == 0


def test_lockable_categories_match_design(db: Session):
    """Q-E2 + Q-E7: epm_thresholds and ai_cost_cap are lockable."""
    seed_category_toggles(db)
    db.commit()

    epm = db.get(Toggle, "epm_thresholds")
    assert epm is not None
    assert epm.lockable is True

    cap = db.get(Toggle, "ai_cost_cap")
    assert cap is not None
    assert cap.lockable is True

    # Non-compliance categories are NOT lockable
    brand = db.get(Toggle, "brand")
    assert brand is not None
    assert brand.lockable is False


def test_epm_thresholds_default_recipe_matches_design(db: Session):
    """Q-C2 + Q-C3: rich-black 40/20/20/80 + coated TAC 320 + uncoated 240."""
    seed_category_toggles(db)
    db.commit()
    epm = db.get(Toggle, "epm_thresholds")
    assert epm is not None
    default = epm.default_value
    assert default["rich_black"] == {"c": 40, "m": 20, "y": 20, "k": 80}
    assert default["tac_limit_coated_pct"] == 320
    assert default["tac_limit_uncoated_pct"] == 240


def test_ai_cost_cap_default_off(db: Session):
    """Q-C5: opt-in cost cap; off by default."""
    seed_category_toggles(db)
    db.commit()
    cap = db.get(Toggle, "ai_cost_cap")
    assert cap is not None
    assert cap.default_value["enabled"] is False
    assert cap.default_value["monthly_cap_cents"] == 0


def test_endpoint_defaults_carries_lintpdf_default_profile(db: Session):
    seed_category_toggles(db)
    db.commit()
    row = db.get(Toggle, "endpoint_defaults")
    assert row is not None
    assert row.default_value["profile_id"] == "lintpdf-default"


def test_import_mapping_only_overrideable_at_tenant_scope(db: Session):
    """Mappings are tenant-level resources."""
    seed_category_toggles(db)
    db.commit()
    row = db.get(Toggle, "import_mapping")
    assert row is not None
    assert list(row.override_at) == [ToggleScope.TENANT]


def test_ai_cost_cap_only_overrideable_at_tenant_scope(db: Session):
    """Per Q-E7: cost caps cannot be raised by workflows or calls."""
    seed_category_toggles(db)
    db.commit()
    row = db.get(Toggle, "ai_cost_cap")
    assert row is not None
    assert list(row.override_at) == [ToggleScope.TENANT]


def test_approval_template_overrides_workflow_but_not_call(db: Session):
    """Approval routing is configured per workflow; not per individual call."""
    seed_category_toggles(db)
    db.commit()
    row = db.get(Toggle, "approval_template")
    assert row is not None
    assert ToggleScope.CALL not in (row.override_at or [])
    assert ToggleScope.WORKFLOW in (row.override_at or [])


def test_all_categories_use_merge_strategy(db: Session):
    """DQ-A1: per-category dict allows multi-instance keys to layer cleanly."""
    seed_category_toggles(db)
    db.commit()
    rows = db.query(Toggle).all()
    for row in rows:
        assert row.merge_strategy == MergeStrategy.MERGE, (
            f"category {row.id!r} should use MERGE strategy for dict keying"
        )
        assert row.type == ToggleType.OBJECT, f"category {row.id!r} should be OBJECT type"
