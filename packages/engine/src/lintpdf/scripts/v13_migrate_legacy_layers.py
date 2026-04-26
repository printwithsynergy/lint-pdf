"""Phase 0.7 PR-B2 — legacy-layer data migration to ConfigOverride rows.

Walks every tenant and folds the five legacy configuration tables into
unified-config :class:`ToggleOverride` rows under the categories
seeded in PR-B1:

    BrandSpec               → toggle_id='brand', scope=TENANT
    CustomProfile           → toggle_id='profile_rules', scope=TENANT
    ApprovalChainTemplate   → toggle_id='approval_template', scope=TENANT
    TenantImportMapping     → toggle_id='import_mapping', scope=TENANT
    CustomEndpoint          → Workflow row (1:1 by slug) +
                              toggle_id='endpoint_defaults', scope=WORKFLOW

**SystemProfile is intentionally skipped** — it's an admin-managed
global registry, not tenant configuration, and it has no equivalent
``ToggleScope`` value (the cascade has TENANT/WORKFLOW/CALL only).
The ``system_profiles`` table stays in place even after PR-B4 drops
the five legacy tenant-config tables.

ApprovalChain + ApprovalStep are runtime tables (per-job execution
state) and are NOT touched here. Only the *templates* fold.

The script is idempotent: re-running merges any missing per-instance
keys into existing ConfigOverride values without clobbering. Each
mutation generates exactly one :class:`ToggleAuditLog` row inside the
same SQLAlchemy transaction so the audit can never drift from the
override state.

Legacy tables are NOT modified or dropped here — that's PR-B4. This
PR only writes to the new tables; consumers still read from the
legacy tables until PR-B3 rewires them.

Usage::

    python -m lintpdf.scripts.v13_migrate_legacy_layers --dry-run
    python -m lintpdf.scripts.v13_migrate_legacy_layers
    python -m lintpdf.scripts.v13_migrate_legacy_layers --tenant-id <uuid>
"""

from __future__ import annotations

import argparse
import logging
import secrets
import sys
import uuid as uuid_mod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from lintpdf.api.models import (
    ApprovalChainTemplate,
    BrandSpec,
    CustomEndpoint,
    CustomProfile,
    Tenant,
    TenantImportMapping,
)
from lintpdf.tenants import toggle_audit
from lintpdf.tenants.toggle_models import (
    ToggleOverride,
    ToggleScope,
    Workflow,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


# Surface tag stamped onto every override + audit row written by this
# script so future debug queries can isolate v13-migrated rows from
# live API writes.
SURFACE = "v13_migration"
ACTOR = "v13_migration"


@dataclass(frozen=True)
class TenantResult:
    """Per-tenant counts so callers can surface totals."""

    tenant_id: uuid_mod.UUID
    workflows_created: int = 0
    workflows_already: int = 0
    brand_keys_added: int = 0
    profile_rules_keys_added: int = 0
    approval_template_keys_added: int = 0
    import_mapping_keys_added: int = 0
    endpoint_defaults_overrides_written: int = 0


# ---- per-category folders --------------------------------------------------


def _upsert_tenant_object_override(
    session: Session,
    *,
    tenant_id: uuid_mod.UUID,
    toggle_id: str,
    incoming_keys: dict[str, Any],
    dry_run: bool,
) -> int:
    """Merge ``incoming_keys`` into the tenant's category override.

    Returns the count of keys newly added (existing keys are left
    untouched — a re-run will not clobber a hand-edited value).
    """
    if not incoming_keys:
        return 0

    existing = session.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == toggle_id,
            ToggleOverride.scope == ToggleScope.TENANT,
            ToggleOverride.scope_id == str(tenant_id),
        )
    ).scalar_one_or_none()

    if existing is None:
        if dry_run:
            return len(incoming_keys)
        session.add(
            ToggleOverride(
                id=secrets.token_urlsafe(12),
                toggle_id=toggle_id,
                scope=ToggleScope.TENANT,
                scope_id=str(tenant_id),
                value=dict(incoming_keys),
                locked=False,
                set_by=ACTOR,
                surface=SURFACE,
            )
        )
        toggle_audit.record(
            session,
            tenant_id=tenant_id,
            toggle_id=toggle_id,
            scope=ToggleScope.TENANT,
            scope_id=str(tenant_id),
            action=toggle_audit.CREATE,
            before=None,
            after_value=dict(incoming_keys),
            after_locked=False,
            actor=ACTOR,
            surface=SURFACE,
        )
        return len(incoming_keys)

    current = dict(existing.value or {})
    new_keys = {k: v for k, v in incoming_keys.items() if k not in current}
    if not new_keys:
        return 0
    if dry_run:
        return len(new_keys)

    after_value = {**current, **new_keys}

    # ``toggle_audit.record`` reads ``before.value`` lazily. Call it
    # BEFORE mutating ``existing.value`` so the audit captures the
    # pre-mutation snapshot, not the post-mutation one.
    toggle_audit.record(
        session,
        tenant_id=tenant_id,
        toggle_id=toggle_id,
        scope=ToggleScope.TENANT,
        scope_id=str(tenant_id),
        action=toggle_audit.UPDATE,
        before=existing,
        after_value=after_value,
        after_locked=existing.locked,
        actor=ACTOR,
        surface=SURFACE,
    )

    existing.value = after_value
    existing.set_by = ACTOR
    return len(new_keys)


def _fold_brand_specs(
    session: Session,
    tenant_id: uuid_mod.UUID,
    *,
    dry_run: bool,
) -> int:
    rows = (
        session.execute(
            select(BrandSpec).where(
                BrandSpec.tenant_id == tenant_id,
                BrandSpec.is_archived.is_(False),
            )
        )
        .scalars()
        .all()
    )
    incoming: dict[str, Any] = {}
    for row in rows:
        incoming[str(row.id)] = {
            "name": row.name,
            "customer_name": row.customer_name,
            "description": row.description,
            "colors": list(row.colors or []),
            "rich_black_spec": row.rich_black_spec,
            "is_default": bool(row.is_default),
        }
    return _upsert_tenant_object_override(
        session,
        tenant_id=tenant_id,
        toggle_id="brand",
        incoming_keys=incoming,
        dry_run=dry_run,
    )


def _fold_custom_profiles(
    session: Session,
    tenant_id: uuid_mod.UUID,
    *,
    dry_run: bool,
) -> int:
    rows = (
        session.execute(
            select(CustomProfile).where(CustomProfile.tenant_id == tenant_id)
        )
        .scalars()
        .all()
    )
    incoming: dict[str, Any] = {}
    for row in rows:
        # Profiles are uniquely keyed by (tenant_id, profile_id) — the
        # string profile_id is what callers reference, so it's the
        # natural per-instance key.
        incoming[row.profile_id] = dict(row.preflight_profile_json or {})
    return _upsert_tenant_object_override(
        session,
        tenant_id=tenant_id,
        toggle_id="profile_rules",
        incoming_keys=incoming,
        dry_run=dry_run,
    )


def _fold_approval_templates(
    session: Session,
    tenant_id: uuid_mod.UUID,
    *,
    dry_run: bool,
) -> int:
    rows = (
        session.execute(
            select(ApprovalChainTemplate).where(
                ApprovalChainTemplate.tenant_id == tenant_id
            )
        )
        .scalars()
        .all()
    )
    incoming: dict[str, Any] = {}
    for row in rows:
        incoming[str(row.id)] = {
            "name": row.name,
            "description": row.description,
            "is_default": bool(row.is_default),
            "steps": list(row.steps or []),
        }
    return _upsert_tenant_object_override(
        session,
        tenant_id=tenant_id,
        toggle_id="approval_template",
        incoming_keys=incoming,
        dry_run=dry_run,
    )


def _fold_import_mappings(
    session: Session,
    tenant_id: uuid_mod.UUID,
    *,
    dry_run: bool,
) -> int:
    rows = (
        session.execute(
            select(TenantImportMapping).where(
                TenantImportMapping.tenant_id == tenant_id,
                TenantImportMapping.is_active.is_(True),
            )
        )
        .scalars()
        .all()
    )
    incoming: dict[str, Any] = {}
    for row in rows:
        # Mapping name is the human key but two mappings could share
        # a name in legacy data — fall back to id when collision.
        key = row.name if row.name not in incoming else str(row.id)
        incoming[key] = {
            "id": str(row.id),
            "name": row.name,
            "description": row.description,
            "format": row.format,
            "config": dict(row.config or {}),
            "sample_payload": row.sample_payload,
            "sample_mime": row.sample_mime,
        }
    return _upsert_tenant_object_override(
        session,
        tenant_id=tenant_id,
        toggle_id="import_mapping",
        incoming_keys=incoming,
        dry_run=dry_run,
    )


def _fold_custom_endpoints(
    session: Session,
    tenant_id: uuid_mod.UUID,
    *,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Custom endpoints become Workflow rows + endpoint_defaults overrides.

    Returns ``(workflows_created, workflows_already_exist,
    endpoint_defaults_overrides_written)``.
    """
    endpoints = (
        session.execute(
            select(CustomEndpoint).where(CustomEndpoint.tenant_id == tenant_id)
        )
        .scalars()
        .all()
    )

    workflows_created = 0
    workflows_already = 0
    overrides_written = 0

    for ep in endpoints:
        # 1:1 mapping by slug. Idempotent: skip if a Workflow with this
        # tenant + slug already exists.
        wf = session.execute(
            select(Workflow).where(
                Workflow.tenant_id == tenant_id,
                Workflow.slug == ep.slug,
            )
        ).scalar_one_or_none()
        if wf is None:
            if dry_run:
                workflows_created += 1
            else:
                wf = Workflow(
                    id=secrets.token_urlsafe(16),
                    tenant_id=tenant_id,
                    slug=ep.slug,
                    human_name=ep.description or ep.slug,
                    description=ep.description or None,
                    is_default=False,
                    is_active=ep.is_active,
                    response_mode=ep.response_mode,
                    server_revision=1,
                )
                session.add(wf)
                session.flush()
                workflows_created += 1
        else:
            workflows_already += 1

        # Endpoint defaults — captured per-workflow.
        endpoint_defaults_value = {
            "profile_id": ep.profile_id,
            "default_brand_spec_id": (
                str(ep.default_brand_spec_id)
                if ep.default_brand_spec_id is not None
                else None
            ),
        }
        if dry_run:
            overrides_written += 1
            continue

        assert wf is not None
        existing_override = session.execute(
            select(ToggleOverride).where(
                ToggleOverride.toggle_id == "endpoint_defaults",
                ToggleOverride.scope == ToggleScope.WORKFLOW,
                ToggleOverride.scope_id == wf.id,
            )
        ).scalar_one_or_none()

        if existing_override is None:
            session.add(
                ToggleOverride(
                    id=secrets.token_urlsafe(12),
                    toggle_id="endpoint_defaults",
                    scope=ToggleScope.WORKFLOW,
                    scope_id=wf.id,
                    value=endpoint_defaults_value,
                    locked=False,
                    set_by=ACTOR,
                    surface=SURFACE,
                )
            )
            toggle_audit.record(
                session,
                tenant_id=tenant_id,
                toggle_id="endpoint_defaults",
                scope=ToggleScope.WORKFLOW,
                scope_id=wf.id,
                action=toggle_audit.CREATE,
                before=None,
                after_value=endpoint_defaults_value,
                after_locked=False,
                actor=ACTOR,
                surface=SURFACE,
            )
            overrides_written += 1

    # Mark one workflow per tenant as is_default if none flagged yet.
    if not dry_run and endpoints:
        any_default = session.execute(
            select(Workflow).where(
                Workflow.tenant_id == tenant_id,
                Workflow.is_default.is_(True),
            )
        ).scalar_one_or_none()
        if any_default is None:
            first = session.execute(
                select(Workflow)
                .where(Workflow.tenant_id == tenant_id)
                .order_by(Workflow.created_at)
                .limit(1)
            ).scalar_one_or_none()
            if first is not None:
                first.is_default = True

    return workflows_created, workflows_already, overrides_written


# ---- per-tenant orchestration ---------------------------------------------


def migrate_tenant(
    session: Session,
    tenant: Tenant,
    *,
    dry_run: bool = False,
) -> TenantResult:
    """Fold all five legacy tables for one tenant in a single transaction."""
    workflows_created, workflows_already, overrides_written = _fold_custom_endpoints(
        session, tenant.id, dry_run=dry_run
    )
    brand_added = _fold_brand_specs(session, tenant.id, dry_run=dry_run)
    profile_added = _fold_custom_profiles(session, tenant.id, dry_run=dry_run)
    approval_added = _fold_approval_templates(session, tenant.id, dry_run=dry_run)
    mapping_added = _fold_import_mappings(session, tenant.id, dry_run=dry_run)

    return TenantResult(
        tenant_id=tenant.id,
        workflows_created=workflows_created,
        workflows_already=workflows_already,
        brand_keys_added=brand_added,
        profile_rules_keys_added=profile_added,
        approval_template_keys_added=approval_added,
        import_mapping_keys_added=mapping_added,
        endpoint_defaults_overrides_written=overrides_written,
    )


def migrate_all(
    session: Session,
    *,
    dry_run: bool = False,
    tenant_ids: Iterable[uuid_mod.UUID] | None = None,
) -> list[TenantResult]:
    """Migrate every tenant (or a filtered subset)."""
    stmt = select(Tenant)
    if tenant_ids is not None:
        stmt = stmt.where(Tenant.id.in_(list(tenant_ids)))
    tenants = session.execute(stmt).scalars().all()

    results: list[TenantResult] = []
    for tenant in tenants:
        result = migrate_tenant(session, tenant, dry_run=dry_run)
        results.append(result)

    if not dry_run:
        session.commit()
    else:
        session.rollback()
    return results


# ---- CLI entry point -------------------------------------------------------


def _summary_line(result: TenantResult) -> str:
    parts = [
        f"tenant={result.tenant_id}",
        f"workflows=+{result.workflows_created}/={result.workflows_already}",
        f"endpoint_defaults=+{result.endpoint_defaults_overrides_written}",
        f"brand=+{result.brand_keys_added}",
        f"profile_rules=+{result.profile_rules_keys_added}",
        f"approval_template=+{result.approval_template_keys_added}",
        f"import_mapping=+{result.import_mapping_keys_added}",
    ]
    return " ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute counts without writing rows.",
    )
    parser.add_argument(
        "--tenant-id",
        action="append",
        default=None,
        help="Restrict to one or more tenant uuids. May be repeated.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    from lintpdf.api.database import get_db_session

    session = get_db_session()
    try:
        ids = (
            [uuid_mod.UUID(t) for t in args.tenant_id]
            if args.tenant_id
            else None
        )
        results = migrate_all(session, dry_run=args.dry_run, tenant_ids=ids)
    finally:
        session.close()

    for result in results:
        logger.info(_summary_line(result))
    if args.dry_run:
        logger.info("DRY RUN — nothing committed (%d tenant(s) inspected)", len(results))
    else:
        logger.info("DONE — %d tenant(s) migrated", len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
