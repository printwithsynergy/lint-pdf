"""Job.stage_durations_ms JSON column.

Persists the orchestrator's per-stage timing (extract, analyzers,
conformance, text_regions, ai_analyzers, filter, color_score,
bbox_enrich) plus the nested ``codex`` subtree captured from the
``X-Codex-Stage-Durations-Ms`` response header when
``LINTPDF_CODEX_STAGE_TELEMETRY_ENABLED`` is on.

NULL means the orchestrator didn't capture stage timings for this
job (older jobs, or a job that ran before the column was deployed).

Revision ID: 054
Revises: 053
Create Date: 2026-05-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "stage_durations_ms",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("jobs", "stage_durations_ms")
