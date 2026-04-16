"""Universal per-call override envelope persistence.

Two new JSON columns:

* ``jobs.overrides`` — the resolved :class:`OverridesEnvelope` captured
  at submit time. The orchestrator and downstream viewer config endpoints
  read it back so every step of the pipeline honours the caller's
  per-job tweaks (checks, thresholds, color workflow, AI, viewer
  defaults, share-link gating) without re-parsing the request.

* ``report_tokens.overrides`` — the resolved envelope captured at mint
  time. Drives per-token viewer behaviour so a single tenant can share
  the same job with three different tokens and three different override
  sets (e.g. gated for external distribution, ungated for internal
  review, hide-separations for a brand-only viewer).

Both columns are nullable — rows predating the migration see ``None``
and the resolver treats that as "inherit everything" / "no overrides".

Revision ID: 026
Revises: 025
Create Date: 2026-04-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("overrides", sa.JSON(), nullable=True))
    op.add_column(
        "report_tokens", sa.Column("overrides", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("report_tokens", "overrides")
    op.drop_column("jobs", "overrides")
