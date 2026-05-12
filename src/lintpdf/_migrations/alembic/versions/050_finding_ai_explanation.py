"""Q-C4/C5 — AI-Explain caches on job_findings.

Adds three columns so a single Claude Haiku call per finding can be
reused across dashboard re-views without paying for tokens twice:

* ``ai_explanation`` (TEXT) — the rendered plain-language explanation.
* ``ai_explanation_model`` (VARCHAR 64) — model id that produced it
  so a future model bump can invalidate stale cache rows.
* ``ai_explanation_at`` (TIMESTAMPTZ) — when it was cached.

The columns are nullable; rows that haven't been explained leave them
NULL. The explain service treats a NULL ``ai_explanation`` as "needs
to call Claude" and a non-NULL value as "already cached, return it".

Revision ID: 050
Revises: 049
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_findings",
        sa.Column("ai_explanation", sa.Text(), nullable=True),
    )
    op.add_column(
        "job_findings",
        sa.Column("ai_explanation_model", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "job_findings",
        sa.Column(
            "ai_explanation_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("job_findings", "ai_explanation_at")
    op.drop_column("job_findings", "ai_explanation_model")
    op.drop_column("job_findings", "ai_explanation")
