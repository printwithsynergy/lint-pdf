"""Plan-tier entitlement overrides table.

Until now the per-plan defaults in ``siftpdf.tenants.models.PLAN_LIMITS``
were hardcoded — bumping Scale's monthly_ai_credits or flipping the
default `ai_audit_enabled` on Enterprise meant a code change + deploy.

This migration introduces a single-row-per-plan DB table that the
resolver reads before PLAN_LIMITS. The row's ``overrides`` JSON
gets merged over the hardcoded defaults, giving ops a no-deploy path
to adjust plan-wide ceilings and gates without a schema change on
the engine side every time. Per-tenant overrides still win over the
plan-level ones — three-layer stack is defaults → plan row →
tenant row.

Revision ID: 035
Revises: 034
Create Date: 2026-04-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_limit_overrides",
        sa.Column("plan", sa.String(length=32), primary_key=True),
        sa.Column(
            "overrides",
            sa.JSON,
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("plan_limit_overrides")
