"""Add AI feature models: TenantAIConfig, TenantAICreditPackage, AIUsageLog.

Also extends job_findings with source and category columns.

Revision ID: 005
Revises: 004
Create Date: 2026-03-16
"""

from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # --- Add AI billing mode enum for PostgreSQL ---
    if is_pg:
        op.execute(
            sa.text(
                """
                DO $$
                BEGIN
                    CREATE TYPE aibillingmode AS ENUM ('pay_per_use', 'credit_package');
                EXCEPTION
                    WHEN duplicate_object THEN
                        NULL;
                END
                $$;
                """
            )
        )

    # --- TenantAIConfig ---
    op.create_table(
        "tenant_ai_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "billing_mode",
            sa.Enum("pay_per_use", "credit_package", name="aibillingmode", create_type=False)
            if is_pg
            else sa.String(20),
            nullable=False,
            server_default="pay_per_use",
        ),
        sa.Column("credit_balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("overage_rate", sa.Numeric(8, 4), nullable=False, server_default="0.10"),
        sa.Column("monthly_spending_limit", sa.Numeric(10, 2), nullable=True),
        sa.Column("enabled_categories", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("default_ai_features", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("trial_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("trial_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("brand_palette", sa.JSON(), nullable=True),
        sa.Column("reference_logos", sa.JSON(), nullable=True),
        sa.Column("custom_dictionary", sa.JSON(), nullable=True),
        sa.Column("industry_type", sa.String(100), nullable=True),
        sa.Column("regulatory_market", sa.String(50), nullable=True),
        sa.Column("default_safe_zone_mm", sa.Numeric(6, 2), nullable=False, server_default="3.0"),
        sa.Column("default_package_capacity_ml", sa.Numeric(10, 2), nullable=True),
        sa.Column("default_package_surface_area_cm2", sa.Numeric(10, 2), nullable=True),
        sa.Column("min_image_quality_score", sa.Integer(), nullable=False, server_default="50"),
        sa.Column(
            "delta_e_delay_threshold", sa.Numeric(6, 2), nullable=False, server_default="2.0"
        ),
        sa.Column(
            "delta_e_no_fly_threshold", sa.Numeric(6, 2), nullable=False, server_default="5.0"
        ),
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
    op.create_index("ix_tenant_ai_configs_tenant_id", "tenant_ai_configs", ["tenant_id"])

    # --- TenantAICreditPackage ---
    op.create_table(
        "tenant_ai_credit_packages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("credits_purchased", sa.Integer(), nullable=False),
        sa.Column("credits_remaining", sa.Integer(), nullable=False),
        sa.Column("price_paid", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "purchased_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_ai_credit_packages_tenant",
        "tenant_ai_credit_packages",
        ["tenant_id", "purchased_at"],
    )

    # --- AIUsageLog ---
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.Uuid(),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("feature", sa.String(100), nullable=False),
        sa.Column("credits_consumed", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cost", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("processing_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ai_usage_logs_tenant_created", "ai_usage_logs", ["tenant_id", "created_at"])
    op.create_index("ix_ai_usage_logs_job", "ai_usage_logs", ["job_id"])

    # --- Extend job_findings with source and category ---
    op.add_column(
        "job_findings",
        sa.Column("source", sa.String(20), nullable=False, server_default="engine"),
    )
    op.add_column(
        "job_findings",
        sa.Column("category", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # Remove new columns from job_findings
    op.drop_column("job_findings", "category")
    op.drop_column("job_findings", "source")

    # Drop AI tables
    op.drop_table("ai_usage_logs")
    op.drop_table("tenant_ai_credit_packages")
    op.drop_table("tenant_ai_configs")

    # Drop enum type
    if is_pg:
        op.execute("DROP TYPE IF EXISTS aibillingmode")
