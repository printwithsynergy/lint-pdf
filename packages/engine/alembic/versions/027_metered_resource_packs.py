"""Metered-resource packs: generalise credit packages + add plan overrides.

Two things happen here:

* ``tenant_ai_credit_packages`` gets four new columns so it can hold
  both AI credit packs and file packs in one table, discriminated by
  ``kind``. Existing rows all have ``kind='credits'`` and
  ``source='admin_grant'`` (the pre-refactor default path). New columns
  ``stripe_session_id`` (webhook idempotency key) and
  ``billing_period_start`` (plan-monthly allocation anchor) are
  nullable because they only apply to specific sources.

* ``tenants`` gets two per-tenant overrides so ops can grant a Growth
  customer Enterprise-level monthly credits (or files) without
  upselling the whole plan. NULL inherits the plan default.

All changes are additive + defaulted → no data loss.

Revision ID: 027
Revises: 026
Create Date: 2026-04-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tenants: per-tenant monthly overrides
    op.add_column(
        "tenants",
        sa.Column("monthly_ai_credits_override", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("monthly_files_override", sa.Integer(), nullable=True),
    )

    # packages: kind + source + stripe idempotency + billing anchor
    op.add_column(
        "tenant_ai_credit_packages",
        sa.Column(
            "kind",
            sa.String(length=16),
            nullable=False,
            server_default="credits",
        ),
    )
    op.add_column(
        "tenant_ai_credit_packages",
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="admin_grant",
        ),
    )
    op.add_column(
        "tenant_ai_credit_packages",
        sa.Column("stripe_session_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "tenant_ai_credit_packages",
        sa.Column("billing_period_start", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_ai_credit_packages_tenant_kind",
        "tenant_ai_credit_packages",
        ["tenant_id", "kind"],
    )
    op.create_index(
        "ix_ai_credit_packages_stripe_session",
        "tenant_ai_credit_packages",
        ["stripe_session_id"],
        unique=True,
        postgresql_where=sa.text("stripe_session_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_credit_packages_stripe_session",
        table_name="tenant_ai_credit_packages",
    )
    op.drop_index(
        "ix_ai_credit_packages_tenant_kind",
        table_name="tenant_ai_credit_packages",
    )
    op.drop_column("tenant_ai_credit_packages", "billing_period_start")
    op.drop_column("tenant_ai_credit_packages", "stripe_session_id")
    op.drop_column("tenant_ai_credit_packages", "source")
    op.drop_column("tenant_ai_credit_packages", "kind")
    op.drop_column("tenants", "monthly_files_override")
    op.drop_column("tenants", "monthly_ai_credits_override")
