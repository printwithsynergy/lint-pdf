"""Tenant-defined import mappings for custom preflight formats.

Teams running proprietary or niche preflight tools supply a JSON
mapping config that tells the engine how to walk their report shape
and pull out finding fields (severity, message, page, bbox, …). This
migration adds the ``tenant_import_mappings`` table that stores those
configs plus a sample payload for preview / round-trip.

Revision ID: 020
Revises: 019
Create Date: 2026-04-12
"""

import sqlalchemy as sa
from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_import_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("format", sa.String(8), nullable=False, server_default="xml"),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("sample_payload", sa.Text(), nullable=True),
        sa.Column("sample_mime", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tenant_import_mappings_tenant",
        "tenant_import_mappings",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_import_mappings_tenant", table_name="tenant_import_mappings")
    op.drop_table("tenant_import_mappings")
