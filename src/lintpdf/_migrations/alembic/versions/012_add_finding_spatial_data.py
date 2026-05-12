"""Add spatial data columns to job_findings for viewer overlay support.

Revision ID: 012
Revises: 011
Create Date: 2026-03-25
"""

from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("job_findings", sa.Column("bbox_x0", sa.Float(), nullable=True))
    op.add_column("job_findings", sa.Column("bbox_y0", sa.Float(), nullable=True))
    op.add_column("job_findings", sa.Column("bbox_x1", sa.Float(), nullable=True))
    op.add_column("job_findings", sa.Column("bbox_y1", sa.Float(), nullable=True))
    op.add_column("job_findings", sa.Column("object_id", sa.String(100), nullable=True))
    op.add_column("job_findings", sa.Column("object_type", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("job_findings", "object_type")
    op.drop_column("job_findings", "object_id")
    op.drop_column("job_findings", "bbox_y1")
    op.drop_column("job_findings", "bbox_x1")
    op.drop_column("job_findings", "bbox_y0")
    op.drop_column("job_findings", "bbox_x0")
