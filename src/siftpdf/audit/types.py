"""Shared types for the AI accuracy auditor surfaces.

Both the internal Opus pass and the customer Modal pass return
:class:`AuditResult` rows aligned 1-to-1 with the input findings.
A ``None`` status means "not audited" — the caller leaves the DB
columns NULL and the viewer renders no chip.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import datetime

AuditStatus = Literal["confirmed", "disputed", "needs_context", "error"]


@dataclass(frozen=True)
class AuditResult:
    """Per-finding verdict produced by an auditor.

    Kept as a plain dataclass (not a Pydantic model) so auditor
    modules can stay free of pydantic in ``packages/inference`` /
    Modal sandboxes where only stdlib + the inference deps are
    available. The caller converts to Pydantic ``AuditVerdict`` at
    the API boundary.
    """

    status: AuditStatus
    rationale: str | None
    model: str
    at: datetime

    def as_kwargs(self) -> dict[str, object]:
        """Spread into ``JobFinding.audit_*`` column assignments."""
        return {
            "audit_status": self.status,
            "audit_rationale": self.rationale,
            "audit_model": self.model,
            "audit_at": self.at,
        }
