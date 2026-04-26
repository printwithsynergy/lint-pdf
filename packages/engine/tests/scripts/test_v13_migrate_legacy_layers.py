"""Phase 0.7 PR-B2 — v13_migrate_legacy_layers script tests."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lintpdf.api.models import (
    ApprovalChainTemplate,
    Base,
    BrandSpec,
    CustomEndpoint,
    CustomProfile,
    Tenant,
    TenantImportMapping,
    TenantPlan,
)
from lintpdf.scripts.v13_migrate_legacy_layers import (
    SURFACE,
    migrate_all,
    migrate_tenant,
)
from lintpdf.tenants.toggle_models import (
    ToggleAuditLog,
    ToggleOverride,
    ToggleScope,
    Workflow,
)
from lintpdf.tenants.toggle_registry import seed_category_toggles

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session


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

    # Seed the 9 category toggles (PR-B1 prerequisite for the migration).
    seed_category_toggles(session)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _make_tenant(db: Session, name: str = "t") -> Tenant:
    t = Tenant(
        id=uuid.uuid4(),
        name=name,
        api_key_hash=f"hash-{name}",
        plan=TenantPlan.GROWTH,
        rate_limit_daily=1000,
        max_file_size_mb=50,
    )
    db.add(t)
    db.commit()
    return t


def _get_tenant_override(
    db: Session, *, tenant_id: uuid.UUID, toggle_id: str
) -> ToggleOverride | None:
    return db.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == toggle_id,
            ToggleOverride.scope == ToggleScope.TENANT,
            ToggleOverride.scope_id == str(tenant_id),
        )
    ).scalar_one_or_none()


# ---- BrandSpec --------------------------------------------------------------


def test_fold_brand_specs_creates_tenant_override(db: Session):
    tenant = _make_tenant(db)
    spec = BrandSpec(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Coca-Cola",
        customer_name="Coca-Cola Co",
        description="cola palette",
        colors=[{"name": "Red", "value": "#FF0000", "pantone": "485 C", "notes": None}],
        rich_black_spec={"c": 60.0, "m": 50.0, "y": 50.0, "k": 100.0},
        is_default=True,
        is_archived=False,
    )
    db.add(spec)
    db.commit()

    result = migrate_tenant(db, tenant)
    db.commit()

    assert result.brand_keys_added == 1
    ov = _get_tenant_override(db, tenant_id=tenant.id, toggle_id="brand")
    assert ov is not None
    assert ov.surface == SURFACE
    assert str(spec.id) in ov.value
    assert ov.value[str(spec.id)]["name"] == "Coca-Cola"
    assert ov.value[str(spec.id)]["customer_name"] == "Coca-Cola Co"
    assert ov.value[str(spec.id)]["is_default"] is True
    assert ov.value[str(spec.id)]["rich_black_spec"]["k"] == 100.0


def test_fold_brand_specs_skips_archived(db: Session):
    tenant = _make_tenant(db)
    db.add(
        BrandSpec(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name="Old",
            customer_name=None,
            colors=[],
            rich_black_spec=None,
            is_default=False,
            is_archived=True,  # ← skipped
        )
    )
    db.commit()

    result = migrate_tenant(db, tenant)
    db.commit()
    assert result.brand_keys_added == 0
    assert _get_tenant_override(db, tenant_id=tenant.id, toggle_id="brand") is None


# ---- CustomProfile ---------------------------------------------------------


def test_fold_custom_profiles_keys_by_profile_id(db: Session):
    tenant = _make_tenant(db)
    db.add(
        CustomProfile(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            profile_id="my-pdfx4",
            preflight_profile_json={"name": "PDF/X-4", "checks": {}},
        )
    )
    db.add(
        CustomProfile(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            profile_id="my-pdfx1a",
            preflight_profile_json={"name": "PDF/X-1a", "checks": {}},
        )
    )
    db.commit()

    result = migrate_tenant(db, tenant)
    db.commit()

    assert result.profile_rules_keys_added == 2
    ov = _get_tenant_override(db, tenant_id=tenant.id, toggle_id="profile_rules")
    assert ov is not None
    assert set(ov.value.keys()) == {"my-pdfx4", "my-pdfx1a"}
    assert ov.value["my-pdfx4"]["name"] == "PDF/X-4"


# ---- ApprovalChainTemplate -------------------------------------------------


def test_fold_approval_templates(db: Session):
    tenant = _make_tenant(db)
    template_id = uuid.uuid4()
    db.add(
        ApprovalChainTemplate(
            id=template_id,
            tenant_id=tenant.id,
            name="QA + Production",
            description="Two-step",
            is_default=True,
            steps=[
                {"step_index": 0, "approver_email": "qa@x.com"},
                {"step_index": 1, "approver_email": "prod@x.com"},
            ],
        )
    )
    db.commit()

    result = migrate_tenant(db, tenant)
    db.commit()

    assert result.approval_template_keys_added == 1
    ov = _get_tenant_override(db, tenant_id=tenant.id, toggle_id="approval_template")
    assert ov is not None
    payload = ov.value[str(template_id)]
    assert payload["name"] == "QA + Production"
    assert payload["is_default"] is True
    assert len(payload["steps"]) == 2


# ---- TenantImportMapping ---------------------------------------------------


def test_fold_import_mappings_skips_inactive(db: Session):
    tenant = _make_tenant(db)
    db.add(
        TenantImportMapping(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name="callas-custom",
            description=None,
            format="xml",
            config={"format": "xml", "item_selector": "//finding"},
            sample_payload="<x/>",
            sample_mime="application/xml",
            is_active=True,
        )
    )
    db.add(
        TenantImportMapping(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name="archived-mapping",
            description=None,
            format="json",
            config={},
            is_active=False,  # ← skipped
        )
    )
    db.commit()

    result = migrate_tenant(db, tenant)
    db.commit()
    assert result.import_mapping_keys_added == 1
    ov = _get_tenant_override(db, tenant_id=tenant.id, toggle_id="import_mapping")
    assert ov is not None
    assert "callas-custom" in ov.value
    assert "archived-mapping" not in ov.value


def test_fold_import_mappings_collision_falls_back_to_id(db: Session):
    """Two mappings with the same name resolve via id-keyed fallback."""
    tenant = _make_tenant(db)
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    db.add(
        TenantImportMapping(
            id=id1,
            tenant_id=tenant.id,
            name="dup",
            format="xml",
            config={"format": "xml", "item_selector": "//a"},
            is_active=True,
        )
    )
    db.add(
        TenantImportMapping(
            id=id2,
            tenant_id=tenant.id,
            name="dup",
            format="xml",
            config={"format": "xml", "item_selector": "//b"},
            is_active=True,
        )
    )
    db.commit()

    result = migrate_tenant(db, tenant)
    db.commit()
    assert result.import_mapping_keys_added == 2
    ov = _get_tenant_override(db, tenant_id=tenant.id, toggle_id="import_mapping")
    assert ov is not None
    # First wins on name; second falls back to id key
    assert "dup" in ov.value
    assert str(id2) in ov.value
    assert ov.value["dup"]["id"] == str(id1)
    assert ov.value[str(id2)]["id"] == str(id2)


# ---- CustomEndpoint → Workflow + endpoint_defaults -------------------------


def test_fold_custom_endpoints_creates_workflow_and_override(db: Session):
    tenant = _make_tenant(db)
    brand_id = uuid.uuid4()
    db.add(
        BrandSpec(
            id=brand_id,
            tenant_id=tenant.id,
            name="x",
            colors=[],
            is_default=False,
            is_archived=False,
        )
    )
    db.add(
        CustomEndpoint(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            slug="packaging",
            profile_id="lintpdf-default",
            description="Packaging line",
            is_active=True,
            response_mode="async",
            default_brand_spec_id=brand_id,
        )
    )
    db.commit()

    result = migrate_tenant(db, tenant)
    db.commit()

    assert result.workflows_created == 1
    assert result.endpoint_defaults_overrides_written == 1

    wf = db.execute(
        select(Workflow).where(Workflow.tenant_id == tenant.id)
    ).scalar_one()
    assert wf.slug == "packaging"
    assert wf.human_name == "Packaging line"
    assert wf.response_mode == "async"
    assert wf.is_active is True

    ov = db.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == "endpoint_defaults",
            ToggleOverride.scope == ToggleScope.WORKFLOW,
            ToggleOverride.scope_id == wf.id,
        )
    ).scalar_one()
    assert ov.value["profile_id"] == "lintpdf-default"
    assert ov.value["default_brand_spec_id"] == str(brand_id)


def test_fold_custom_endpoints_marks_one_default_per_tenant(db: Session):
    tenant = _make_tenant(db)
    db.add(
        CustomEndpoint(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            slug="a",
            profile_id="lintpdf-default",
            is_active=True,
            response_mode="async",
        )
    )
    db.add(
        CustomEndpoint(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            slug="b",
            profile_id="lintpdf-default",
            is_active=True,
            response_mode="async",
        )
    )
    db.commit()

    migrate_tenant(db, tenant)
    db.commit()

    workflows = (
        db.execute(select(Workflow).where(Workflow.tenant_id == tenant.id))
        .scalars()
        .all()
    )
    defaults = [w for w in workflows if w.is_default]
    assert len(defaults) == 1


# ---- idempotency -----------------------------------------------------------


def test_re_running_is_no_op_for_existing_keys(db: Session):
    tenant = _make_tenant(db)
    spec_id = uuid.uuid4()
    db.add(
        BrandSpec(
            id=spec_id,
            tenant_id=tenant.id,
            name="x",
            colors=[],
            is_default=False,
            is_archived=False,
        )
    )
    db.commit()

    first = migrate_tenant(db, tenant)
    db.commit()
    second = migrate_tenant(db, tenant)
    db.commit()

    assert first.brand_keys_added == 1
    assert second.brand_keys_added == 0
    ov = _get_tenant_override(db, tenant_id=tenant.id, toggle_id="brand")
    assert ov is not None
    assert len(ov.value) == 1


def test_re_running_picks_up_new_brand_specs(db: Session):
    tenant = _make_tenant(db)
    db.add(
        BrandSpec(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name="first",
            colors=[],
            is_default=False,
            is_archived=False,
        )
    )
    db.commit()
    migrate_tenant(db, tenant)
    db.commit()

    # Add one more spec after first migration
    db.add(
        BrandSpec(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name="second",
            colors=[],
            is_default=False,
            is_archived=False,
        )
    )
    db.commit()
    second = migrate_tenant(db, tenant)
    db.commit()

    assert second.brand_keys_added == 1
    ov = _get_tenant_override(db, tenant_id=tenant.id, toggle_id="brand")
    assert ov is not None
    assert len(ov.value) == 2


def test_re_running_does_not_clobber_user_edits(db: Session):
    """If a tenant edited the override post-migration, re-run leaves it alone."""
    tenant = _make_tenant(db)
    spec_id = uuid.uuid4()
    db.add(
        BrandSpec(
            id=spec_id,
            tenant_id=tenant.id,
            name="legacy-name",
            colors=[],
            is_default=False,
            is_archived=False,
        )
    )
    db.commit()
    migrate_tenant(db, tenant)
    db.commit()

    # Simulate an admin edit through the dashboard
    ov = _get_tenant_override(db, tenant_id=tenant.id, toggle_id="brand")
    assert ov is not None
    edited = dict(ov.value)
    edited[str(spec_id)] = {"name": "renamed-by-admin", "colors": []}
    ov.value = edited
    db.commit()

    # Re-run: existing key already present, untouched
    second = migrate_tenant(db, tenant)
    db.commit()

    assert second.brand_keys_added == 0
    ov_after = _get_tenant_override(db, tenant_id=tenant.id, toggle_id="brand")
    assert ov_after is not None
    assert ov_after.value[str(spec_id)]["name"] == "renamed-by-admin"


# ---- audit log -------------------------------------------------------------


def test_audit_row_written_on_create(db: Session):
    tenant = _make_tenant(db)
    db.add(
        BrandSpec(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name="x",
            colors=[],
            is_default=False,
            is_archived=False,
        )
    )
    db.commit()

    migrate_tenant(db, tenant)
    db.commit()

    rows = (
        db.execute(
            select(ToggleAuditLog).where(
                ToggleAuditLog.tenant_id == tenant.id,
                ToggleAuditLog.toggle_id == "brand",
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].action == "CREATE"
    assert rows[0].surface == SURFACE
    assert rows[0].actor == "v13_migration"
    assert rows[0].before_value is None


def test_audit_row_captures_pre_mutation_value_on_update(db: Session):
    """Regression test for the audit-record-ordering bug fixed in PR-B2."""
    tenant = _make_tenant(db)
    spec1_id = uuid.uuid4()
    db.add(
        BrandSpec(
            id=spec1_id,
            tenant_id=tenant.id,
            name="first",
            colors=[],
            is_default=False,
            is_archived=False,
        )
    )
    db.commit()
    migrate_tenant(db, tenant)
    db.commit()

    # Add a second spec; second migration produces an UPDATE audit row.
    spec2_id = uuid.uuid4()
    db.add(
        BrandSpec(
            id=spec2_id,
            tenant_id=tenant.id,
            name="second",
            colors=[],
            is_default=False,
            is_archived=False,
        )
    )
    db.commit()
    migrate_tenant(db, tenant)
    db.commit()

    update_rows = (
        db.execute(
            select(ToggleAuditLog).where(
                ToggleAuditLog.tenant_id == tenant.id,
                ToggleAuditLog.toggle_id == "brand",
                ToggleAuditLog.action == "UPDATE",
            )
        )
        .scalars()
        .all()
    )
    assert len(update_rows) == 1
    audit = update_rows[0]
    # before_value should hold ONLY spec1; after_value should hold BOTH
    assert audit.before_value is not None
    assert str(spec1_id) in audit.before_value
    assert str(spec2_id) not in audit.before_value
    assert audit.after_value is not None
    assert str(spec1_id) in audit.after_value
    assert str(spec2_id) in audit.after_value


# ---- cross-tenant isolation -----------------------------------------------


def test_two_tenants_keep_overrides_separate(db: Session):
    t1 = _make_tenant(db, "t1")
    t2 = _make_tenant(db, "t2")
    db.add(
        BrandSpec(
            id=uuid.uuid4(),
            tenant_id=t1.id,
            name="t1-brand",
            colors=[],
            is_default=False,
            is_archived=False,
        )
    )
    db.add(
        BrandSpec(
            id=uuid.uuid4(),
            tenant_id=t2.id,
            name="t2-brand",
            colors=[],
            is_default=False,
            is_archived=False,
        )
    )
    db.commit()

    migrate_all(db)

    t1_ov = _get_tenant_override(db, tenant_id=t1.id, toggle_id="brand")
    t2_ov = _get_tenant_override(db, tenant_id=t2.id, toggle_id="brand")
    assert t1_ov is not None and t2_ov is not None
    assert len(t1_ov.value) == 1
    assert len(t2_ov.value) == 1
    [t1_payload] = t1_ov.value.values()
    [t2_payload] = t2_ov.value.values()
    assert t1_payload["name"] == "t1-brand"
    assert t2_payload["name"] == "t2-brand"


# ---- dry-run --------------------------------------------------------------


def test_dry_run_writes_nothing(db: Session):
    tenant = _make_tenant(db)
    db.add(
        BrandSpec(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name="x",
            colors=[],
            is_default=False,
            is_archived=False,
        )
    )
    db.commit()

    results = migrate_all(db, dry_run=True)
    assert len(results) == 1
    assert results[0].brand_keys_added == 1

    # Nothing actually written
    ov = _get_tenant_override(db, tenant_id=tenant.id, toggle_id="brand")
    assert ov is None
    audit_rows = db.execute(select(ToggleAuditLog)).scalars().all()
    assert audit_rows == []


def test_migrate_all_filters_by_tenant_id(db: Session):
    t1 = _make_tenant(db, "t1")
    t2 = _make_tenant(db, "t2")
    for tenant in (t1, t2):
        db.add(
            BrandSpec(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                name=f"{tenant.name}-brand",
                colors=[],
                is_default=False,
                is_archived=False,
            )
        )
    db.commit()

    results = migrate_all(db, tenant_ids=[t1.id])
    assert len(results) == 1
    assert results[0].tenant_id == t1.id

    assert _get_tenant_override(db, tenant_id=t1.id, toggle_id="brand") is not None
    assert _get_tenant_override(db, tenant_id=t2.id, toggle_id="brand") is None
