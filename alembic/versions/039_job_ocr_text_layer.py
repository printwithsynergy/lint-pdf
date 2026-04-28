"""Job.ocr_text_layer + Job.ocr_force (WS-C).

Adds the recovered text layer from the Claude OCR pass plus the
per-job opt-in flag that ``POST /jobs?ocr=force`` sets.

Revision ID: 039
Revises: 038
Create Date: 2026-04-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "ocr_text_layer",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "ocr_force",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("jobs", "ocr_force")
    op.drop_column("jobs", "ocr_text_layer")
