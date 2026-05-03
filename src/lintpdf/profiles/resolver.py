"""Tenant-aware profile resolver.

Replaces the bundled-only ``ProfileRegistry`` for every code path that
answers "does this tenant have access to profile_id X?" or "show me
the profiles this tenant can see". The bundled in-memory registry is
kept alive for the seed path (``lintpdf.profiles.seed``) + unit test
isolation; nothing in the request path calls it directly anymore.
"""

from __future__ import annotations

import uuid as uuid_mod
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, or_

from lintpdf.api.models import SystemProfile
from lintpdf.tenants.models import TenantPlan

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from lintpdf.services.tenant_context import TenantContext

# Cheapest possible implementation of "is tenant.plan >= min_plan". Explicit
# order keeps the list a one-liner to audit, and decouples the visibility
# filter from any accidental re-ordering of ``TenantPlan`` enum members.
_PLAN_ORDER: list[TenantPlan] = [
    TenantPlan.FREE,
    TenantPlan.VIEWER,
    TenantPlan.STARTER,
    TenantPlan.GROWTH,
    TenantPlan.SCALE,
    TenantPlan.ENTERPRISE,
]


def _plans_at_or_above(min_plan: str) -> list[str]:
    """Return every plan slug whose tier is ``>= min_plan``.

    Unknown / unmapped ``min_plan`` values fall through to "nobody
    qualifies" rather than "everybody qualifies" — safer default for
    a visibility filter.
    """
    try:
        idx = next(i for i, p in enumerate(_PLAN_ORDER) if p.value == min_plan)
    except StopIteration:
        return []
    return [p.value for p in _PLAN_ORDER[idx:]]


def _tenant_qualifies(sp: SystemProfile, tenant: TenantContext) -> bool:
    """Reapplies the visibility filter against an already-fetched row.

    Used by point lookups (``get_visible_system_profile``) to avoid a
    second SQL round-trip.
    """
    # PR B Slot 2B: admin-only profiles are never visible to a tenant
    # request — only the parallel admin endpoint
    # (POST /api/v1/admin/jobs/test-system-profile, X-Admin-Key) can
    # resolve them. Filter here so list-view and point-lookup both
    # stay consistent.
    profile_json = sp.preflight_profile_json or {}
    if profile_json.get("is_admin_only"):
        return False
    if sp.visibility_mode == "all":
        return True
    plan_ok = sp.min_plan is None or (str(tenant.plan) in _plans_at_or_above(sp.min_plan))
    allow_list_ok = sp.visible_tenant_ids is not None and tenant.id in sp.visible_tenant_ids
    if sp.visibility_mode == "plan":
        return plan_ok
    if sp.visibility_mode == "tenants":
        return allow_list_ok
    if sp.visibility_mode == "plan_and_tenants":
        return plan_ok and allow_list_ok
    # Unknown mode → fail closed.
    return False


def list_visible_system_profiles(db: Session, tenant: TenantContext) -> list[SystemProfile]:
    """Return every :class:`SystemProfile` this tenant can see.

    The visible-tenant-list filter is applied in Python so the query
    stays portable between Postgres (where ``visible_tenant_ids`` is a
    ``UUID[]`` column and ``ANY()`` works natively) and SQLite (where
    the column degrades to JSON and ``ANY()`` is unsupported). The
    SQL pre-filter pulls ``all`` and ``plan`` rows plus any row whose
    visibility_mode hints at a tenant-list check; the Python pass
    then narrows the latter to rows that actually include this
    tenant's id.
    """
    tenant_plan = str(tenant.plan)
    # Plans that qualify for ``plan`` / ``plan_and_tenants`` visibility
    # when ``min_plan`` is ``tenant.plan`` or lower.
    plans_at_or_above_tenant = (
        [p.value for p in _PLAN_ORDER[: _PLAN_ORDER.index(TenantPlan(tenant_plan)) + 1]]
        if tenant_plan in [p.value for p in _PLAN_ORDER]
        else []
    )

    candidates = (
        db.query(SystemProfile)
        .filter(
            or_(
                SystemProfile.visibility_mode == "all",
                and_(
                    SystemProfile.visibility_mode == "plan",
                    SystemProfile.min_plan.in_(plans_at_or_above_tenant),
                ),
                SystemProfile.visibility_mode.in_(("tenants", "plan_and_tenants")),
            )
        )
        .order_by(SystemProfile.profile_id)
        .all()
    )

    visible: list[SystemProfile] = []
    for sp in candidates:
        mode = sp.visibility_mode
        if mode in ("all", "plan"):
            visible.append(sp)
        elif mode == "tenants":
            if sp.visible_tenant_ids and tenant.id in sp.visible_tenant_ids:
                visible.append(sp)
        elif mode == "plan_and_tenants" and (
            sp.min_plan in plans_at_or_above_tenant
            and sp.visible_tenant_ids
            and tenant.id in sp.visible_tenant_ids
        ):
            visible.append(sp)
    return visible


def get_visible_system_profile(
    db: Session, tenant: TenantContext, profile_id: str
) -> SystemProfile | None:
    """Fetch a single :class:`SystemProfile` iff ``tenant`` can see it.

    Returns ``None`` if the row doesn't exist OR is not visible to
    ``tenant``. Point-lookup twin of
    :func:`list_visible_system_profiles`.
    """
    row: SystemProfile | None = (
        db.query(SystemProfile).filter(SystemProfile.profile_id == profile_id).first()
    )
    if row is None:
        return None
    return row if _tenant_qualifies(row, tenant) else None


def get_custom_profile(db: Session, tenant: TenantContext, profile_id: str):
    """Return the tenant's custom profile entry for ``profile_id`` or None.

    Phase 0.7 PR-B3e — reads from
    ``ToggleOverride(toggle_id='profile_rules', scope=TENANT)`` instead
    of the legacy ``custom_profiles`` table. Returns a
    :class:`types.SimpleNamespace` carrying the same attributes
    callers expect (``profile_id``, ``preflight_profile_json``) so
    the function signature stays drop-in compatible with the previous
    SQLAlchemy-row return type.
    """
    from types import SimpleNamespace

    from lintpdf.profiles import storage as _profile_storage

    value = _profile_storage.get_profile(db, tenant.id, profile_id)
    if value is None:
        return None
    return SimpleNamespace(
        id=value.get("id"),
        profile_id=value.get("profile_id", profile_id),
        preflight_profile_json=value.get("preflight_profile_json") or {},
    )


def profile_exists_for_tenant(db: Session, tenant: TenantContext, profile_id: str) -> bool:
    """Checks whether ``tenant`` can submit a job against ``profile_id``.

    Precedence mirrors the tenant-facing list endpoint: a tenant's
    custom profile with the same ``profile_id`` as a system one wins
    inside that tenant's view. Used by the jobs + endpoints submission
    guards to avoid the pre-existing bug where a tenant's valid
    ``custom_profiles`` row 404'd because the old check only hit the
    bundled registry.
    """
    if get_custom_profile(db, tenant, profile_id) is not None:
        return True
    return get_visible_system_profile(db, tenant, profile_id) is not None


def resolve_profile_json(
    db: Session, tenant: TenantContext, profile_id: str
) -> dict[str, Any] | None:
    """Return the raw :class:`PreflightProfile` JSON for ``profile_id``
    as visible to ``tenant``. Custom wins over system on collision."""
    custom = get_custom_profile(db, tenant, profile_id)
    if custom is not None:
        return dict(custom.preflight_profile_json)
    sys_row = get_visible_system_profile(db, tenant, profile_id)
    if sys_row is not None:
        return dict(sys_row.preflight_profile_json)
    return None


def resolve_effective_profile_id(db: Session, tenant: TenantContext, requested: str | None) -> str:
    """Pick the profile_id to use for a job submission.

    Precedence:

    1. The caller's explicit ``profile_id`` (validated separately
       elsewhere — this helper is only called when it's either
       ``None`` or already known-visible).
    2. ``tenant.default_profile_id`` if it's still visible.
    3. The bundled ``lintpdf-default`` fallback.
    """
    if requested and profile_exists_for_tenant(db, tenant, requested):
        return requested
    default = getattr(tenant, "default_profile_id", None)
    if default and profile_exists_for_tenant(db, tenant, default):
        return default
    return "lintpdf-default"


def uuid_from_any(value: Any) -> uuid_mod.UUID | None:
    """Coerce ``value`` to :class:`uuid.UUID`, returning ``None`` on
    failure. Convenience for routes that accept string tenant IDs."""
    if isinstance(value, uuid_mod.UUID):
        return value
    try:
        return uuid_mod.UUID(str(value))
    except (ValueError, TypeError):
        return None
