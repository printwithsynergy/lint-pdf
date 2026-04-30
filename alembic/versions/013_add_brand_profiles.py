"""Add brand_profiles table and default_brand_profile_id to tenants.

Revision ID: 013
Revises: 012
Create Date: 2026-03-25
"""

from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brand_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "profile_type",
            sa.Enum("custom", "siftpdf", "none", name="brandprofiletype"),
            nullable=False,
            server_default="custom",
        ),
        sa.Column("brand_name", sa.String(255), nullable=True),
        sa.Column("logo_url", sa.String(2048), nullable=True),
        sa.Column("primary_color", sa.String(7), nullable=True),
        sa.Column("accent_color", sa.String(7), nullable=True),
        sa.Column("footer_text", sa.String(500), nullable=True),
        sa.Column("hide_footer", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_brand_profiles_tenant", "brand_profiles", ["tenant_id"])

    op.add_column("tenants", sa.Column("default_brand_profile_id", sa.Uuid(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "default_brand_profile_id")
    op.drop_index("ix_brand_profiles_tenant", table_name="brand_profiles")
    op.drop_table("brand_profiles")
    op.execute("DROP TYPE IF EXISTS brandprofiletype")
