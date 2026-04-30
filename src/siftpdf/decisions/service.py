"""Wave V V-05 — decision-recording service.

Thin helpers for recording, querying, and revoking decisions in the
``lintpdf_decisions`` audit table. Routes / Celery tasks call these
instead of touching the ORM directly so the call sites stay short and
the audit semantics (append-only, soft revoke, request_id propagation)
live in one place.
"""

from __future__ import annotations

import uuid as uuid_mod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from siftpdf.decisions.models import Decision

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.orm import Session


# Decision type vocabulary. Keep narrow — analytics queries assume a
# closed enum; future additions need explicit dashboard + report
# updates so the surface doesn't drift silently.
APPROVE = "approve"
REJECT = "reject"
WAIVE = "waive"
SUPPRESS = "suppress"
ANNOTATE = "annotate"
ESCALATE = "escalate"

_VALID_SOURCES = frozenset(
    {
        "dashboard",
        "api",
        "plugin",
        "sdk",
        "share_link",
        "approval_chain",
        "desktop",
        "system",
        "migration",
    }
)


class InvalidDecisionError(ValueError):
    """Raised when a caller hands a malformed decision payload."""


def record_decision(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    job_id: uuid_mod.UUID,
    decision_type: str,
    decided_by_user_id: str,
    source: str,
    finding_id: uuid_mod.UUID | None = None,
    decision_value: str | None = None,
    metadata: dict[str, Any] | None = None,
    notes: str | None = None,
    decided_by_email: str | None = None,
    request_id: str | None = None,
) -> Decision:
    """Append a new decision row + return it.

    Caller controls transaction boundaries — this helper flushes but
    does not commit. Callers wrapping a decision in a wider transaction
    (e.g. recording the decision alongside a webhook delivery) keep
    atomicity.
    """
    if source not in _VALID_SOURCES:
        raise InvalidDecisionError(
            f"unknown decision source {source!r}; "
            f"expected one of {sorted(_VALID_SOURCES)}"
        )
    if not decision_type or len(decision_type) > 32:
        raise InvalidDecisionError(
            "decision_type must be 1-32 chars (e.g. 'approve', 'waive')"
        )
    if not decided_by_user_id:
        raise InvalidDecisionError("decided_by_user_id must be non-empty")

    row = Decision(
        id=uuid_mod.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        finding_id=finding_id,
        decision_type=decision_type,
        decision_value=decision_value,
        decision_metadata=dict(metadata) if metadata else None,
        notes=notes,
        decided_by_user_id=decided_by_user_id,
        decided_by_email=decided_by_email,
        source=source,
        request_id=request_id,
    )
    db.add(row)
    db.flush()
    return row


def revoke_decision(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    decision_id: uuid_mod.UUID,
    revoked_by_user_id: str,
    revoked_reason: str | None = None,
) -> Decision | None:
    """Soft-revoke a decision row. Returns the row or None if not found.

    Cross-tenant access returns None (does not leak existence). Already
    revoked decisions are a no-op — the original revocation stamp wins.
    """
    if not revoked_by_user_id:
        raise InvalidDecisionError("revoked_by_user_id must be non-empty")

    row = db.execute(
        select(Decision).where(
            Decision.id == decision_id,
            Decision.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    if row.revoked_at is not None:
        return row
    row.revoked_at = datetime.now(tz=timezone.utc)
    row.revoked_by_user_id = revoked_by_user_id
    row.revoked_reason = revoked_reason
    db.flush()
    return row


def list_for_job(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    job_id: uuid_mod.UUID,
    include_revoked: bool = False,
    limit: int = 200,
) -> list[Decision]:
    """List decisions on a job, newest first."""
    stmt = select(Decision).where(
        Decision.tenant_id == tenant_id,
        Decision.job_id == job_id,
    )
    if not include_revoked:
        stmt = stmt.where(Decision.revoked_at.is_(None))
    stmt = stmt.order_by(Decision.decided_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def list_for_finding(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    finding_id: uuid_mod.UUID,
    include_revoked: bool = False,
    limit: int = 200,
) -> list[Decision]:
    """List decisions on a finding, newest first."""
    stmt = select(Decision).where(
        Decision.tenant_id == tenant_id,
        Decision.finding_id == finding_id,
    )
    if not include_revoked:
        stmt = stmt.where(Decision.revoked_at.is_(None))
    stmt = stmt.order_by(Decision.decided_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def list_for_actor(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    actor_user_id: str,
    include_revoked: bool = False,
    limit: int = 200,
) -> list[Decision]:
    """List every decision an actor made for a tenant, newest first."""
    stmt = select(Decision).where(
        Decision.tenant_id == tenant_id,
        Decision.decided_by_user_id == actor_user_id,
    )
    if not include_revoked:
        stmt = stmt.where(Decision.revoked_at.is_(None))
    stmt = stmt.order_by(Decision.decided_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def latest_active_for_finding(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    finding_id: uuid_mod.UUID,
) -> Decision | None:
    """Return the most recent non-revoked decision on a finding.

    Useful for "is this finding currently waived?" — the most recent
    active decision is the effective verdict.
    """
    stmt = (
        select(Decision)
        .where(
            Decision.tenant_id == tenant_id,
            Decision.finding_id == finding_id,
            Decision.revoked_at.is_(None),
        )
        .order_by(Decision.decided_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def summarise_job_decisions(
    decisions: Iterable[Decision],
) -> dict[str, int]:
    """Count active decisions by ``decision_type`` for a job summary card."""
    counts: dict[str, int] = {}
    for d in decisions:
        if d.revoked_at is not None:
            continue
        counts[d.decision_type] = counts.get(d.decision_type, 0) + 1
    return counts


__all__ = [
    "ANNOTATE",
    "APPROVE",
    "ESCALATE",
    "REJECT",
    "SUPPRESS",
    "WAIVE",
    "InvalidDecisionError",
    "latest_active_for_finding",
    "list_for_actor",
    "list_for_finding",
    "list_for_job",
    "record_decision",
    "revoke_decision",
    "summarise_job_decisions",
]
