"""Job.detected_text_regions JSON column.

Persists the orchestrator's shared OCR text-region pass (PR 2: OCR/ML
accuracy gap closure). Each value is a list of ``DetectedTextRegion``
shapes serialised as JSON: ``{bbox, text, confidence, polygon, source}``.
``NULL`` means the pass didn't run for that job (heuristic gated, GPU
outage, or feature disabled).

Revision ID: 051
Revises: 050
Create Date: 2026-04-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "detected_text_regions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("jobs", "detected_text_regions")
