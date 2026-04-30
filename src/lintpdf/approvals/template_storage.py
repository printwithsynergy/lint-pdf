"""Phase 0.7 PR-B3c — approval-template storage adapter.

Mirrors :mod:`lintpdf.brand_specs.storage`. Hides the dict-keyed
``ToggleOverride(toggle_id='approval_template', scope=TENANT)`` shape
behind a small set of helpers so the route, service, and runtime
chain-attach path don't each have to re-implement the upsert / lookup
plumbing.

The on-disk shape (per-tenant value) is::

    {
        "<template uuid str>": {
            "id": str,
            "name": str,
            "description": str | None,
            "is_default": bool,
            "steps": list[dict],
            "created_at": ISO8601 str,
            "updated_at": ISO8601 str,
        },
        ...
    }

ApprovalChainTemplate has no soft-delete flag — DELETE removes the
entry. PR-B4 also drops the ``approval_chain_templates`` table; the
runtime ``approval_chains`` + ``approval_steps`` tables stay (per-job
execution state, not config).

Every mutation flows through :func:`mutate_templates` which calls
:mod:`lintpdf.tenants.toggle_audit` BEFORE mutating the row so the
audit trail captures the pre-state.
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


_TOGGLE_ID = "approval_template"


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def load_templates(db: Session, tenant_id: uuid_mod.UUID) -> dict[str, Any]:
    """Return the tenant's approval-template dict (or {} when no override)."""
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


def get_template(
    db: Session, tenant_id: uuid_mod.UUID, template_id: uuid_mod.UUID
) -> dict[str, Any] | None:
    """Return one template by id, or None if not present."""
    return load_templates(db, tenant_id).get(str(template_id))


def get_default(db: Session, tenant_id: uuid_mod.UUID) -> dict[str, Any] | None:
    """Return the tenant's default template, or None."""
    for value in load_templates(db, tenant_id).values():
        if value.get("is_default"):
            return value
    return None


def mutate_templates(
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


def clear_default(templates: dict[str, Any], *, except_id: str | None = None) -> None:
    """Demote every is_default template in-place. Pure-function helper."""
    for key, value in templates.items():
        if key == except_id:
            continue
        if value.get("is_default"):
            value["is_default"] = False
            value["updated_at"] = now_iso()


__all__ = [
    "clear_default",
    "get_default",
    "get_template",
    "load_templates",
    "mutate_templates",
    "now_iso",
]
