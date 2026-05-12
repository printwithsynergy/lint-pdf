"""Wave V V-08 — toggle audit log.

Append-only log of every ToggleOverride mutation. Each PUT or DELETE on
the V-07 override endpoints writes exactly one row inside the same
transaction so the log can never drift from the override state.

Indexed for the two common audit views:

* ``(tenant_id, toggle_id)`` — "show me every change to checks.F-22"
* ``(tenant_id, created_at DESC)`` — "show recent changes for tenant X"

Retention is indefinite; a future revision may archive rows older
than 2 years to cold storage.

Revision ID: 043
Revises: 042
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "toggle_audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("toggle_id", sa.String(length=255), nullable=False),
        sa.Column(
            "scope",
            postgresql.ENUM(
                "TENANT",
                "WORKFLOW",
                "CALL",
                name="toggle_scope",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("scope_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column(
            "before_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "after_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("before_locked", sa.Boolean(), nullable=True),
        sa.Column("after_locked", sa.Boolean(), nullable=True),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("surface", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_toggle_audit_tenant_toggle",
        "toggle_audit_log",
        ["tenant_id", "toggle_id"],
    )
    op.create_index(
        "ix_toggle_audit_tenant_recent",
        "toggle_audit_log",
        ["tenant_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_toggle_audit_tenant_recent", table_name="toggle_audit_log")
    op.drop_index("ix_toggle_audit_tenant_toggle", table_name="toggle_audit_log")
    op.drop_table("toggle_audit_log")
