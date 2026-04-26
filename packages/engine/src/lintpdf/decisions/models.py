"""Wave V V-05 — Decision SQLAlchemy ORM model.

Backs the ``lintpdf_decisions`` table created by alembic 048. Captures
operator decisions on jobs and findings with full provenance + soft
revocation.
"""

from __future__ import annotations

import uuid
from datetime import datetime  # noqa: TC003
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from lintpdf.api.models import Base

_JSONB = JSONB(astext_type=Text()).with_variant(JSON(), "sqlite")


class Decision(Base):
    """Per-document/per-finding/per-operator decision audit row.

    ``finding_id`` is nullable: a NULL row records a job-level decision
    (e.g. "this entire document is approved"); a non-NULL row records a
    finding-level decision ("waive this F-22 advisory").

    Decisions are append-only — revocation marks ``revoked_at`` /
    ``revoked_by_user_id`` / ``revoked_reason`` rather than deleting,
    so audit replays stay correct after operators change their minds.
    """

    __tablename__ = "lintpdf_decisions"
    __table_args__ = (
        Index("ix_lintpdf_decisions_tenant_job", "tenant_id", "job_id"),
        Index(
            "ix_lintpdf_decisions_tenant_finding",
            "tenant_id",
            "finding_id",
        ),
        Index(
            "ix_lintpdf_decisions_tenant_actor",
            "tenant_id",
            "decided_by_user_id",
        ),
        Index(
            "ix_lintpdf_decisions_tenant_recent",
            "tenant_id",
            "decided_at",
        ),
        CheckConstraint(
            "source IN ('dashboard','api','plugin','sdk','share_link',"
            "'approval_chain','desktop','system','migration')",
            name="ck_lintpdf_decisions_source",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    finding_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("job_findings.id", ondelete="CASCADE"),
        nullable=True,
    )
    decision_type: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        _JSONB,
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decided_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_by_user_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def is_active(self) -> bool:
        """True iff the decision has not been revoked."""
        return self.revoked_at is None


__all__ = ["Decision"]
