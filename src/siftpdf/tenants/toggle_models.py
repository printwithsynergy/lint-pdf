"""SQLAlchemy ORM models for Wave V V-07 toggle resolver.

Three tables backing the configuration cascade:

* ``Workflow`` — first-class named scope above per-call overrides.
* ``Toggle``   — the registry of every configurable knob (dot-notation IDs).
* ``ToggleOverride`` — stored per-scope override values keyed by
  ``(toggle_id, scope, scope_id)`` where ``scope_id`` is a tenant uuid,
  workflow id, or call id.

These tables are co-managed by Prisma (app dashboard CRUD) and SQLAlchemy
(engine resolver + write-through API). Both layers reference the same
physical Postgres tables created by Alembic migration ``042``.

Tenant scope_id is a Postgres uuid to match ``tenants.id``. Workflow
scope_id is a VARCHAR(64) cuid (Prisma-managed). Call scope_id is an
opaque request nonce (also VARCHAR).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime  # noqa: TC003

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from siftpdf.api.models import Base


class ToggleType(enum.StrEnum):
    BOOLEAN = "BOOLEAN"
    NUMERIC = "NUMERIC"
    ENUM = "ENUM"
    STRING = "STRING"
    OBJECT = "OBJECT"


class ToggleScope(enum.StrEnum):
    TENANT = "TENANT"
    WORKFLOW = "WORKFLOW"
    CALL = "CALL"


class MergeStrategy(enum.StrEnum):
    REPLACE = "REPLACE"
    MERGE = "MERGE"
    UNION = "UNION"


_TOGGLE_TYPE_COL = Enum(
    ToggleType,
    name="toggle_type",
    values_callable=lambda e: [m.value for m in e],
    native_enum=True,
)
_TOGGLE_SCOPE_COL = Enum(
    ToggleScope,
    name="toggle_scope",
    values_callable=lambda e: [m.value for m in e],
    native_enum=True,
)
_MERGE_STRATEGY_COL = Enum(
    MergeStrategy,
    name="merge_strategy",
    values_callable=lambda e: [m.value for m in e],
    native_enum=True,
)

_TOGGLE_SCOPE_ARRAY = PG_ARRAY(_TOGGLE_SCOPE_COL).with_variant(JSON(), "sqlite")
_JSONB = JSONB(astext_type=Text()).with_variant(JSON(), "sqlite")


class Workflow(Base):
    """Named tenant-scoped workflow (e.g. ``"Packaging — Folding Carton"``)."""

    __tablename__ = "workflows"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_workflows_tenant_slug"),
        Index("ix_workflows_tenant_id", "tenant_id"),
        CheckConstraint(
            "response_mode IN ('async', 'sync')",
            name="ck_workflows_response_mode",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    human_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    response_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="async")
    server_revision: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_by_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Toggle(Base):
    """Registry row for a configurable knob (dot-notation id).

    ``override_at`` controls which scopes may override the value.
    ``lockable`` enables the locked-tenant-override feature (only the
    TENANT scope can lock per Phase 1 Q4 approved defaults).
    """

    __tablename__ = "toggles"
    __table_args__ = (Index("ix_toggles_category", "category"),)

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    human_name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[ToggleType] = mapped_column(_TOGGLE_TYPE_COL, nullable=False)
    default_value: Mapped[object] = mapped_column(_JSONB, nullable=False)
    allowed_range: Mapped[object | None] = mapped_column(_JSONB, nullable=True)
    override_at: Mapped[list[ToggleScope]] = mapped_column(_TOGGLE_SCOPE_ARRAY, nullable=False)
    lockable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    merge_strategy: Mapped[MergeStrategy] = mapped_column(
        _MERGE_STRATEGY_COL, nullable=False, default=MergeStrategy.REPLACE
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    overrides: Mapped[list[ToggleOverride]] = relationship(
        "ToggleOverride", back_populates="toggle", cascade="all, delete-orphan"
    )


class ToggleOverride(Base):
    """A stored override at a specific scope.

    ``scope_id`` is opaque text — its meaning depends on ``scope``:

    * TENANT  → ``tenants.id`` UUID (stored as text representation here)
    * WORKFLOW → ``workflows.id`` cuid
    * CALL    → request nonce assigned at submit time

    ``locked = True`` is only honored when ``scope == TENANT``.
    """

    __tablename__ = "toggle_overrides"
    __table_args__ = (
        UniqueConstraint("toggle_id", "scope", "scope_id", name="uq_toggle_overrides_scope"),
        Index("ix_toggle_overrides_scope_lookup", "scope", "scope_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    toggle_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("toggles.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope: Mapped[ToggleScope] = mapped_column(_TOGGLE_SCOPE_COL, nullable=False)
    scope_id: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[object] = mapped_column(_JSONB, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    set_by: Mapped[str] = mapped_column(String(128), nullable=False)
    set_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    surface: Mapped[str] = mapped_column(String(32), nullable=False)

    toggle: Mapped[Toggle] = relationship("Toggle", back_populates="overrides")


class ResolvedConfigSnapshot(Base):
    """Per-job durable record of the resolved configuration cascade.

    Written once per job at submit time after the cascade resolves. The
    ``resolved_payload`` is the merged dict of every toggle that fed
    that job; ``provenance`` is a parallel dict mapping each toggle id
    to the scope (``system`` / ``tenant`` / ``workflow`` / ``call``)
    that supplied the value.

    Audit views replay from these snapshots, not from live override
    state, so "what config drove this job's findings" stays answerable
    even after the workflow has been edited.
    """

    __tablename__ = "resolved_config_snapshots"
    __table_args__ = (
        Index(
            "ix_resolved_config_snapshots_tenant_recent",
            "tenant_id",
            "created_at",
        ),
        Index(
            "ix_resolved_config_snapshots_workflow_recent",
            "workflow_id",
            "created_at",
        ),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_payload: Mapped[object] = mapped_column(_JSONB, nullable=False)
    provenance: Mapped[object] = mapped_column(_JSONB, nullable=False)
    system_default_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ToggleAuditLog(Base):
    """Append-only audit log of every ToggleOverride mutation (V-08).

    Written synchronously inside the same DB transaction as the override
    write so the log can never drift from the override state.
    """

    __tablename__ = "toggle_audit_log"
    __table_args__ = (
        Index("ix_toggle_audit_tenant_toggle", "tenant_id", "toggle_id"),
        Index("ix_toggle_audit_tenant_recent", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    toggle_id: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[ToggleScope] = mapped_column(_TOGGLE_SCOPE_COL, nullable=False)
    scope_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    before_value: Mapped[object | None] = mapped_column(_JSONB, nullable=True)
    after_value: Mapped[object | None] = mapped_column(_JSONB, nullable=True)
    before_locked: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    after_locked: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    surface: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


__all__ = [
    "MergeStrategy",
    "ResolvedConfigSnapshot",
    "Toggle",
    "ToggleAuditLog",
    "ToggleOverride",
    "ToggleScope",
    "ToggleType",
    "Workflow",
]
