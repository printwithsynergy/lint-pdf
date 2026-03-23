"""Add custom_endpoints table for vanity URL slugs bound to profiles.

Revision ID: 009
Revises: 008
Create Date: 2026-03-23
"""

from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: str | None = "008_print_terminology_rebrand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "custom_endpoints",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("profile_id", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1024), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_custom_endpoints_tenant_id",
        "custom_endpoints",
        ["tenant_id"],
    )
    op.create_index(
        "ix_custom_endpoints_tenant_slug",
        "custom_endpoints",
        ["tenant_id", "slug"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_custom_endpoints_tenant_slug", table_name="custom_endpoints")
    op.drop_index("ix_custom_endpoints_tenant_id", table_name="custom_endpoints")
    op.drop_table("custom_endpoints")
