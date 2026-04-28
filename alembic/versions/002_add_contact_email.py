"""Add contact_email, overage, and stripe columns to tenants.

Revision ID: 002
Revises: 001
Create Date: 2026-03-14
"""

from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("contact_email", sa.String(255), nullable=True))
    op.add_column(
        "tenants", sa.Column("overage_enabled", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column("tenants", sa.Column("overage_cap_cents", sa.Integer(), nullable=True))
    op.add_column("tenants", sa.Column("overage_rate_override_cents", sa.Integer(), nullable=True))
    op.add_column("tenants", sa.Column("stripe_customer_id", sa.String(255), nullable=True))
    op.add_column(
        "tenants", sa.Column("stripe_subscription_item_id", sa.String(255), nullable=True)
    )
    # Branding columns
    op.add_column("tenants", sa.Column("brand_name", sa.String(255), nullable=True))
    op.add_column("tenants", sa.Column("brand_logo_url", sa.String(2048), nullable=True))
    op.add_column("tenants", sa.Column("brand_primary_color", sa.String(7), nullable=True))
    op.add_column("tenants", sa.Column("brand_accent_color", sa.String(7), nullable=True))
    op.add_column("tenants", sa.Column("brand_custom_domain", sa.String(255), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("brand_hide_footer", sa.Boolean(), nullable=False, server_default="false"),
    )
    # Report columns
    op.add_column("tenants", sa.Column("report_default_expiry_days", sa.Integer(), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("report_email_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "tenants",
        sa.Column("report_storage_used_bytes", sa.Integer(), nullable=False, server_default="0"),
    )
    # Report tokens table
    op.create_table(
        "report_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token", sa.String(255), nullable=False, unique=True),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("accessed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_report_tokens_token", "report_tokens", ["token"], unique=True)
    op.create_index("ix_report_tokens_job_id", "report_tokens", ["job_id"])
    op.create_index("ix_report_tokens_tenant_id", "report_tokens", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("report_tokens")
    op.drop_column("tenants", "report_storage_used_bytes")
    op.drop_column("tenants", "report_email_enabled")
    op.drop_column("tenants", "report_default_expiry_days")
    op.drop_column("tenants", "brand_hide_footer")
    op.drop_column("tenants", "brand_custom_domain")
    op.drop_column("tenants", "brand_accent_color")
    op.drop_column("tenants", "brand_primary_color")
    op.drop_column("tenants", "brand_logo_url")
    op.drop_column("tenants", "brand_name")
    op.drop_column("tenants", "stripe_subscription_item_id")
    op.drop_column("tenants", "stripe_customer_id")
    op.drop_column("tenants", "overage_rate_override_cents")
    op.drop_column("tenants", "overage_cap_cents")
    op.drop_column("tenants", "overage_enabled")
    op.drop_column("tenants", "contact_email")
