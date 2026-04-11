"""Add report_summary_page column to tenants table.

Revision ID: 016
Revises: 015
Create Date: 2026-04-11
"""

from alembic import op
import sqlalchemy as sa


revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("report_summary_page", sa.String(10), nullable=False, server_default="prepend"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "report_summary_page")
