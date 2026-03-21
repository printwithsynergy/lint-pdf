"""Add color management models: TenantColorConfig, UserAIAccess, color_quality_score.

Revision ID: 007_add_color_models
Revises: 006_nautical_rebrand
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007_add_color_models"
down_revision = "006_nautical_rebrand"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- TenantColorConfig ---
    op.create_table(
        "tenant_color_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("default_output_condition", sa.String(100), nullable=True),
        sa.Column("custom_icc_profiles", sa.JSON(), nullable=True),
        sa.Column("brand_palette", sa.JSON(), nullable=True),
        sa.Column("custom_dictionary_words", sa.JSON(), nullable=True),
        sa.Column(
            "default_tac_threshold", sa.Integer(), nullable=False, server_default="320"
        ),
        sa.Column(
            "default_safe_zone_margin_mm",
            sa.Numeric(6, 2),
            nullable=False,
            server_default="3.0",
        ),
        sa.Column("package_capacity_default", sa.String(50), nullable=True),
        sa.Column("package_surface_area_default", sa.Numeric(10, 2), nullable=True),
        sa.Column("target_market", sa.String(50), nullable=True),
        sa.Column(
            "epm_mode_default", sa.Boolean(), nullable=False, server_default="false"
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
    op.create_index(
        "ix_tenant_color_configs_tenant_id", "tenant_color_configs", ["tenant_id"]
    )

    # --- UserAIAccess ---
    op.create_table(
        "user_ai_access",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ai_enabled", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("personal_spending_limit", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "trial_enabled", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("trial_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_user_ai_access_user_id", "user_ai_access", ["user_id"])
    op.create_index("ix_user_ai_access_tenant_id", "user_ai_access", ["tenant_id"])
    op.create_index(
        "ix_user_ai_access_user_tenant",
        "user_ai_access",
        ["user_id", "tenant_id"],
        unique=True,
    )

    # --- Add color_quality_score to jobs ---
    op.add_column(
        "jobs",
        sa.Column("color_quality_score", sa.Numeric(5, 1), nullable=True),
    )


def downgrade() -> None:
    # Remove color_quality_score from jobs
    op.drop_column("jobs", "color_quality_score")

    # Drop tables
    op.drop_table("user_ai_access")
    op.drop_table("tenant_color_configs")
