"""Job.structural_evidence JSONB column.

Persists the orchestrator's structural-evidence dict (PR B Slot 2A:
audit upgrade). Carries the parsed-PDF fields the Opus audit harness
uses to adjudicate findings vision can't verify (font embedding, ICC,
encryption, XMP, output intents, spot colorspaces, AcroForm / OCG
presence). NULL on legacy jobs preceding the PR.

Revision ID: 052
Revises: 051
Create Date: 2026-04-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "structural_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("jobs", "structural_evidence")
