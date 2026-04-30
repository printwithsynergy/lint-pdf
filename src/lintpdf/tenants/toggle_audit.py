"""Wave V V-08 — toggle audit log helper.

Single ``record()`` function called by V-07 mutation handlers (PUT and
DELETE on ``/api/v1/tenant/toggles/{id}``) before commit. Writes one
:class:`ToggleAuditLog` row per mutation.

Use synchronously, inside the same SQLAlchemy session as the override
write. The session commit then atomically persists both rows; if the
override write fails the audit row is rolled back too.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from lintpdf.tenants.toggle_models import (
    ToggleAuditLog,
    ToggleOverride,
    ToggleScope,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


CREATE = "CREATE"
UPDATE = "UPDATE"
DELETE = "DELETE"


def record(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    toggle_id: str,
    scope: ToggleScope,
    scope_id: str,
    action: str,
    before: ToggleOverride | None,
    after_value: Any = None,
    after_locked: bool | None = None,
    actor: str,
    surface: str,
) -> ToggleAuditLog:
    """Write a single audit row. Returns the row for the caller to inspect.

    Args:
        before: the existing ToggleOverride row before mutation, or None
            if this is a CREATE.
        after_value: the new value (None for DELETE).
        after_locked: the new locked flag (None for DELETE).
    """
    if action not in (CREATE, UPDATE, DELETE):
        raise ValueError(f"unknown action: {action!r}")
    entry = ToggleAuditLog(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        toggle_id=toggle_id,
        scope=scope,
        scope_id=scope_id,
        action=action,
        before_value=before.value if before is not None else None,
        after_value=after_value,
        before_locked=before.locked if before is not None else None,
        after_locked=after_locked,
        actor=actor,
        surface=surface,
    )
    session.add(entry)
    return entry


__all__ = ["CREATE", "DELETE", "UPDATE", "record"]
