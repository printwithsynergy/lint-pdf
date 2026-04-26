"""Wave V V-12 — legacy ``entitlement_overrides`` migration script.

Walks every active :class:`Tenant`, reads the legacy ``entitlement_overrides``
JSON, and emits one :class:`ToggleOverride` row at TENANT scope for each
known knob. Idempotent: rerunning is a no-op when every mapped row
already exists.

Pre-seeds the :class:`Toggle` registry with the canonical entry for each
migrated knob so the resolver has a default to fall back to when the
override is later removed.

The legacy ``entitlement_overrides`` column is not modified — backward
compat for direct readers is preserved.

Usage::

    python -m lintpdf.scripts.v12_migrate_legacy --dry-run
    python -m lintpdf.scripts.v12_migrate_legacy
    python -m lintpdf.scripts.v12_migrate_legacy --tenant-id <uuid>
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

from lintpdf.api.models import Tenant
from lintpdf.tenants import toggle_audit
from lintpdf.tenants.toggle_models import (
    MergeStrategy,
    Toggle,
    ToggleOverride,
    ToggleScope,
    ToggleType,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ToggleSpec:
    """Mapping row: legacy key → toggle registry entry."""

    legacy_key: str
    toggle_id: str
    category: str
    human_name: str
    type: ToggleType
    default_value: Any
    merge_strategy: MergeStrategy = MergeStrategy.REPLACE
    description: str = ""


# Per design.md §"Knobs migrated" — only these seven keys are handled
# in v2.0. Future toggles should ship their registry entry directly via
# a seeder, not via this migration.
LEGACY_TOGGLE_MAP: tuple[_ToggleSpec, ...] = (
    _ToggleSpec(
        legacy_key="ai_features",
        toggle_id="ai_features",
        category="features",
        human_name="AI features",
        type=ToggleType.OBJECT,
        default_value=[],
        merge_strategy=MergeStrategy.UNION,
        description="Per-tenant AI feature grants. Union-merged with plan baseline.",
    ),
    _ToggleSpec(
        legacy_key="monthly_ai_credits",
        toggle_id="limits.monthly_ai_credits",
        category="limits",
        human_name="Monthly AI credit ceiling (cents)",
        type=ToggleType.NUMERIC,
        default_value=0,
        description="Per-tenant override on monthly AI credits, in integer cents.",
    ),
    _ToggleSpec(
        legacy_key="monthly_files",
        toggle_id="limits.monthly_files",
        category="limits",
        human_name="Monthly file ceiling",
        type=ToggleType.NUMERIC,
        default_value=0,
        description="Per-tenant override on monthly file count.",
    ),
    _ToggleSpec(
        legacy_key="rate_limit_daily",
        toggle_id="limits.rate_limit_daily",
        category="limits",
        human_name="Daily rate limit",
        type=ToggleType.NUMERIC,
        default_value=10,
        description="Daily request quota.",
    ),
    _ToggleSpec(
        legacy_key="max_file_size_mb",
        toggle_id="limits.max_file_size_mb",
        category="limits",
        human_name="Max file size (MB)",
        type=ToggleType.NUMERIC,
        default_value=10,
        description="Per-tenant max upload size in megabytes.",
    ),
    _ToggleSpec(
        legacy_key="default_profile_id",
        toggle_id="defaults.profile_id",
        category="defaults",
        human_name="Default preflight profile",
        type=ToggleType.STRING,
        default_value="lintpdf-default",
        description="Profile id used when a job is submitted without an explicit profile.",
    ),
    _ToggleSpec(
        legacy_key="unbranded_by_default",
        toggle_id="defaults.unbranded",
        category="defaults",
        human_name="Strip LintPDF branding by default",
        type=ToggleType.BOOLEAN,
        default_value=False,
        description="When true, viewer + reports default to the 'none' brand profile.",
    ),
)


_MIGRATION_ACTOR = "v12_migration"
_MIGRATION_SURFACE = "script"


@dataclass
class TenantStats:
    tenant_id: uuid_mod.UUID
    created: int = 0
    skipped: int = 0
    absent: int = 0


def ensure_toggles_seeded(session: Session, *, dry_run: bool = False) -> int:
    """Insert any missing :class:`Toggle` registry rows. Returns rows created."""
    created = 0
    for spec in LEGACY_TOGGLE_MAP:
        existing = session.get(Toggle, spec.toggle_id)
        if existing is not None:
            continue
        if dry_run:
            created += 1
            continue
        session.add(
            Toggle(
                id=spec.toggle_id,
                category=spec.category,
                human_name=spec.human_name,
                type=spec.type,
                default_value=spec.default_value,
                override_at=[
                    ToggleScope.TENANT,
                    ToggleScope.WORKFLOW,
                    ToggleScope.CALL,
                ],
                merge_strategy=spec.merge_strategy,
                lockable=False,
                description=spec.description,
            )
        )
        created += 1
    if not dry_run and created > 0:
        session.flush()
    return created


def migrate_tenant(
    session: Session,
    tenant: Tenant,
    *,
    dry_run: bool = False,
) -> TenantStats:
    """Migrate one tenant's ``entitlement_overrides`` to ToggleOverride rows."""
    stats = TenantStats(tenant_id=tenant.id)
    legacy = tenant.entitlement_overrides or {}
    if not legacy:
        return stats

    for spec in LEGACY_TOGGLE_MAP:
        if spec.legacy_key not in legacy:
            stats.absent += 1
            continue
        legacy_value = legacy[spec.legacy_key]

        existing = session.execute(
            select(ToggleOverride).where(
                ToggleOverride.toggle_id == spec.toggle_id,
                ToggleOverride.scope == ToggleScope.TENANT,
                ToggleOverride.scope_id == str(tenant.id),
            )
        ).scalar_one_or_none()

        if existing is not None and existing.set_by != _MIGRATION_ACTOR:
            # Manually-set row — never touch.
            stats.skipped += 1
            continue
        if existing is not None and existing.value == legacy_value:
            stats.skipped += 1
            continue

        if dry_run:
            stats.created += 1 if existing is None else 0
            stats.skipped += 1 if existing is not None else 0
            continue

        if existing is not None:
            toggle_audit.record(
                session,
                tenant_id=tenant.id,
                toggle_id=spec.toggle_id,
                scope=ToggleScope.TENANT,
                scope_id=str(tenant.id),
                action=toggle_audit.UPDATE,
                before=existing,
                after_value=legacy_value,
                after_locked=existing.locked,
                actor=_MIGRATION_ACTOR,
                surface=_MIGRATION_SURFACE,
            )
            existing.value = legacy_value
            existing.set_by = _MIGRATION_ACTOR
            stats.skipped += 1
        else:
            session.add(
                ToggleOverride(
                    id=secrets.token_urlsafe(12),
                    toggle_id=spec.toggle_id,
                    scope=ToggleScope.TENANT,
                    scope_id=str(tenant.id),
                    value=legacy_value,
                    locked=False,
                    set_by=_MIGRATION_ACTOR,
                    surface=_MIGRATION_SURFACE,
                )
            )
            toggle_audit.record(
                session,
                tenant_id=tenant.id,
                toggle_id=spec.toggle_id,
                scope=ToggleScope.TENANT,
                scope_id=str(tenant.id),
                action=toggle_audit.CREATE,
                before=None,
                after_value=legacy_value,
                after_locked=False,
                actor=_MIGRATION_ACTOR,
                surface=_MIGRATION_SURFACE,
            )
            stats.created += 1
    return stats


def run(
    session: Session,
    *,
    tenant_id: uuid_mod.UUID | None = None,
    dry_run: bool = False,
) -> tuple[list[TenantStats], int]:
    """Execute the migration. Returns (per-tenant stats, registry rows created)."""
    registry_created = ensure_toggles_seeded(session, dry_run=dry_run)

    stmt = select(Tenant).where(Tenant.is_active.is_(True))
    if tenant_id is not None:
        stmt = stmt.where(Tenant.id == tenant_id)
    tenants: Iterable[Tenant] = session.execute(stmt).scalars().all()

    all_stats = [migrate_tenant(session, t, dry_run=dry_run) for t in tenants]

    if not dry_run:
        session.commit()
    return all_stats, registry_created


# ---- CLI -----------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="v12_migrate_legacy",
        description="Migrate legacy Tenant.entitlement_overrides to ToggleOverride rows.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing to the database.",
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        default=None,
        help="Only migrate one tenant (uuid).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)

    from lintpdf.api.database import get_db

    tid = uuid_mod.UUID(args.tenant_id) if args.tenant_id else None

    session = next(get_db())
    try:
        all_stats, registry_created = run(session, tenant_id=tid, dry_run=args.dry_run)
    finally:
        session.close()

    total_created = sum(s.created for s in all_stats)
    for s in all_stats:
        logger.info(
            "tenant %s: created %d, skipped %d, absent %d",
            s.tenant_id,
            s.created,
            s.skipped,
            s.absent,
        )
    logger.info(
        "done — %d overrides %s across %d tenants (registry rows %s: %d)",
        total_created,
        "would be created" if args.dry_run else "created",
        len(all_stats),
        "would be created" if args.dry_run else "created",
        registry_created,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
