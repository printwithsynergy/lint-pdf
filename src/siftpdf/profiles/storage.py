"""Phase 0.7 PR-B3e — custom-profile storage adapter.

Mirrors :mod:`siftpdf.brand_specs.storage`. Hides the dict-keyed
``ToggleOverride(toggle_id='profile_rules', scope=TENANT)`` shape
behind helpers so the route + resolver + worker hot path don't each
re-implement the upsert / lookup plumbing.

The on-disk shape (per-tenant value) is::

    {
        "<profile_id>": {        # the string profile_id, e.g. ``my-pdfx4``
            "id": str,           # uuid string of the legacy CustomProfile row
            "profile_id": str,
            "preflight_profile_json": {...},  # PreflightProfile shape
            "created_at": ISO8601 str,
            "updated_at": ISO8601 str,
        },
        ...
    }

Note that profiles key by **string** ``profile_id`` (e.g. ``my-pdfx4``)
not by uuid — the profile_id is what callers pass to
``POST /api/v1/jobs?profile_id=...`` and is the natural lookup key.

Only ``custom_profiles`` (tenant-owned) folds into this category.
``system_profiles`` is an admin-managed global registry and stays in
its own table even after PR-B4 — it has no equivalent ``ToggleScope``.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from siftpdf.tenants import toggle_audit
from siftpdf.tenants.config_resolver import ConfigResolver
from siftpdf.tenants.toggle_models import ToggleOverride, ToggleScope

if TYPE_CHECKING:
    import uuid as uuid_mod
    from collections.abc import Callable

    from sqlalchemy.orm import Session


_TOGGLE_ID = "profile_rules"


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def load_profiles(db: Session, tenant_id: uuid_mod.UUID) -> dict[str, Any]:
    """Return the tenant's profile_rules dict (or {} when no override)."""
    row = db.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == _TOGGLE_ID,
            ToggleOverride.scope == ToggleScope.TENANT,
            ToggleOverride.scope_id == str(tenant_id),
        )
    ).scalar_one_or_none()
    if row is None:
        return {}
    return dict(row.value or {})


def get_profile(
    db: Session, tenant_id: uuid_mod.UUID, profile_id: str
) -> dict[str, Any] | None:
    """Return one profile entry by string profile_id, or None."""
    return load_profiles(db, tenant_id).get(profile_id)


def count_profiles(db: Session, tenant_id: uuid_mod.UUID) -> int:
    """Number of custom profiles for this tenant."""
    return len(load_profiles(db, tenant_id))


def mutate_profiles(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    mutator: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Read → mutate → write atomically with audit + cache invalidation."""
    existing = db.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == _TOGGLE_ID,
            ToggleOverride.scope == ToggleScope.TENANT,
            ToggleOverride.scope_id == str(tenant_id),
        )
    ).scalar_one_or_none()
    current = dict((existing.value if existing else None) or {})
    new_value = mutator(dict(current))

    if existing is None:
        db.add(
            ToggleOverride(
                id=secrets.token_urlsafe(12),
                toggle_id=_TOGGLE_ID,
                scope=ToggleScope.TENANT,
                scope_id=str(tenant_id),
                value=new_value,
                locked=False,
                set_by="api",
                surface="api",
            )
        )
        toggle_audit.record(
            db,
            tenant_id=tenant_id,
            toggle_id=_TOGGLE_ID,
            scope=ToggleScope.TENANT,
            scope_id=str(tenant_id),
            action=toggle_audit.CREATE,
            before=None,
            after_value=new_value,
            after_locked=False,
            actor="api",
            surface="api",
        )
    else:
        toggle_audit.record(
            db,
            tenant_id=tenant_id,
            toggle_id=_TOGGLE_ID,
            scope=ToggleScope.TENANT,
            scope_id=str(tenant_id),
            action=toggle_audit.UPDATE,
            before=existing,
            after_value=new_value,
            after_locked=existing.locked,
            actor="api",
            surface="api",
        )
        existing.value = new_value
        existing.set_by = "api"

    db.commit()
    ConfigResolver(db).invalidate(tenant_id=tenant_id)
    return new_value


__all__ = [
    "count_profiles",
    "get_profile",
    "load_profiles",
    "mutate_profiles",
    "now_iso",
]
