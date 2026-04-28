"""Add verdict columns and ensure all recent Job model columns exist.

Revision ID: 015
Revises: 014
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Verdict columns (manual review disposition) — added to Job model
    # but never migrated.
    op.execute("""
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS verdict VARCHAR(20) NULL;
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS verdict_by VARCHAR(255) NULL;
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS verdict_at TIMESTAMPTZ NULL;
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS verdict_notes TEXT NULL;
    """)

    # Safety net: ensure other recent columns exist too (idempotent).
    op.execute("""
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS color_quality_score NUMERIC(5,1) NULL;
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS jdf_overrides JSONB NULL;
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS file_name VARCHAR(255) NOT NULL DEFAULT '';
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS file_size INTEGER NOT NULL DEFAULT 0;
    """)


def downgrade() -> None:
    op.drop_column("jobs", "verdict_notes")
    op.drop_column("jobs", "verdict_at")
    op.drop_column("jobs", "verdict_by")
    op.drop_column("jobs", "verdict")
