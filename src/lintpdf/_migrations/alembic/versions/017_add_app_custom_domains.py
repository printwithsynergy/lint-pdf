"""Add app/viewer custom domain columns to tenants and brand_profiles.

Revision ID: 017
Revises: 016
Create Date: 2026-04-11
"""

import sqlalchemy as sa
from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("app_custom_domain", sa.String(255), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("app_custom_domain_verified", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "tenants",
        sa.Column("app_custom_domain_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_tenants_app_custom_domain",
        "tenants",
        ["app_custom_domain"],
        unique=True,
        postgresql_where=sa.text("app_custom_domain IS NOT NULL"),
    )

    op.add_column("brand_profiles", sa.Column("app_custom_domain", sa.String(255), nullable=True))
    op.add_column(
        "brand_profiles",
        sa.Column("app_custom_domain_verified", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "brand_profiles",
        sa.Column("app_custom_domain_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_brand_profiles_app_custom_domain",
        "brand_profiles",
        ["app_custom_domain"],
        unique=True,
        postgresql_where=sa.text("app_custom_domain IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_brand_profiles_app_custom_domain", table_name="brand_profiles")
    op.drop_column("brand_profiles", "app_custom_domain_requested_at")
    op.drop_column("brand_profiles", "app_custom_domain_verified")
    op.drop_column("brand_profiles", "app_custom_domain")
    op.drop_index("ix_tenants_app_custom_domain", table_name="tenants")
    op.drop_column("tenants", "app_custom_domain_requested_at")
    op.drop_column("tenants", "app_custom_domain_verified")
    op.drop_column("tenants", "app_custom_domain")
