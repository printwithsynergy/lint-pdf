"""Drop the vestigial ``waitlist_entries`` table.

Created by alembic 003 for the pre-launch waitlist sign-up. The
flow ended up living in the marketing site (``packages/web``)
before launch and the table was never wired up -- zero references
in either OSS engine or SaaS shell. Dropping per the orphan-tables
audit follow-up (audit/saas-residual-modules.md).

Revision ID: 053
Revises: 052
Create Date: 2026-05-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ``IF EXISTS`` guards: production has the table from alembic 003;
    # fresh dev environments where 003 was already squashed don't.
    op.execute("DROP INDEX IF EXISTS ix_waitlist_entries_email")
    op.execute("DROP TABLE IF EXISTS waitlist_entries")


def downgrade() -> None:
    # Recreate per the original 003 schema for completeness, although
    # the table is unused so a real rollback would never be exercised.
    op.create_table(
        "waitlist_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_waitlist_entries_email", "waitlist_entries", ["email"], unique=True
    )
