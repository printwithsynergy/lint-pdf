"""Add growth/scale plan tiers and entitlement_overrides column.

Revision ID: 004
Revises: 003
Create Date: 2026-03-15
"""

from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # For PostgreSQL: add new enum values to the tenantplan type.
    # SQLite stores enums as plain strings so no ALTER TYPE is needed.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE tenantplan ADD VALUE IF NOT EXISTS 'growth'")
        op.execute("ALTER TYPE tenantplan ADD VALUE IF NOT EXISTS 'scale'")
        # Migrate existing 'pro' tenants to 'growth'
        op.execute("UPDATE tenants SET plan = 'growth' WHERE plan = 'pro'")
    else:
        # SQLite: plain string column, just update values
        op.execute("UPDATE tenants SET plan = 'growth' WHERE plan = 'pro'")

    # Add entitlement_overrides JSON column
    op.add_column("tenants", sa.Column("entitlement_overrides", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove entitlement_overrides column
    op.drop_column("tenants", "entitlement_overrides")

    # Revert growth tenants back to pro
    op.execute("UPDATE tenants SET plan = 'pro' WHERE plan = 'growth'")
    # Note: PostgreSQL does not easily support removing enum values.
    # The 'growth' and 'scale' values will remain in the type but be unused.
