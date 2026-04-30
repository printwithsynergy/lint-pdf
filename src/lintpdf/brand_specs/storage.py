"""Phase 0.7 PR-B3b — brand-spec storage adapter.

Hides the dict-keyed ``ToggleOverride(toggle_id='brand', scope=TENANT)``
shape behind a small set of helpers so the route, resolver, and job
submit path don't each have to re-implement the upsert / lookup
plumbing.

The on-disk shape (per-tenant value) is::

    {
        "<spec uuid str>": {
            "id": str,
            "name": str,
            "customer_name": str | None,
            "description": str | None,
            "colors": list[dict],
            "rich_black_spec": dict | None,
            "is_default": bool,
            "is_archived": bool,
            "created_at": ISO8601 str,
            "updated_at": ISO8601 str,
        },
        ...
    }

Soft-delete is captured by ``is_archived = True`` in the value (the
key stays so historical jobs that reference it can still resolve).

Every mutation flows through :func:`mutate_specs` which captures the
pre-mutation value, calls :mod:`lintpdf.tenants.toggle_audit` BEFORE
mutating the row (so the audit trail captures the pre-state, not the
post-state), then commits + invalidates the resolver cache.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from lintpdf.tenants import toggle_audit
from lintpdf.tenants.config_resolver import ConfigResolver
from lintpdf.tenants.toggle_models import ToggleOverride, ToggleScope

if TYPE_CHECKING:
    import uuid as uuid_mod
    from collections.abc import Callable

    from sqlalchemy.orm import Session


_TOGGLE_ID = "brand"


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def load_specs(db: Session, tenant_id: uuid_mod.UUID) -> dict[str, Any]:
    """Return the tenant's brand-spec dict (or empty when no override)."""
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


def get_spec(
    db: Session, tenant_id: uuid_mod.UUID, spec_id: uuid_mod.UUID
) -> dict[str, Any] | None:
    """Return one spec by id, or None if not present."""
    return load_specs(db, tenant_id).get(str(spec_id))


def get_default(db: Session, tenant_id: uuid_mod.UUID) -> dict[str, Any] | None:
    """Return the tenant's non-archived default spec, or None."""
    for value in load_specs(db, tenant_id).values():
        if value.get("is_default") and not value.get("is_archived"):
            return value
    return None


def mutate_specs(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    mutator: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Read → mutate → write atomically with audit + cache invalidation.

    ``mutator`` receives a fresh copy of the current dict and returns
    the new dict. The caller never has to touch ToggleOverride or the
    audit log directly.

    Returns the new dict so callers can pull out the resulting value
    after the write.
    """
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
        # Audit BEFORE mutation so before.value is the pre-state.
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


def clear_default(specs: dict[str, Any], *, except_id: str | None = None) -> None:
    """Demote every is_default spec in-place. Pure-function helper."""
    for key, value in specs.items():
        if key == except_id:
            continue
        if value.get("is_default"):
            value["is_default"] = False
            value["updated_at"] = now_iso()
