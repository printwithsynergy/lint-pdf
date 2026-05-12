"""Add custom_pantone_overrides column to tenant_color_configs.

Revision ID: 010
Revises: 009
Create Date: 2026-03-23
"""

from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_color_configs",
        sa.Column(
            "custom_pantone_overrides",
            sa.JSON(),
            nullable=True,
            comment="Customer Pantone color overrides keyed by normalized name",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_color_configs", "custom_pantone_overrides")
