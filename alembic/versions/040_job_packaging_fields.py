"""Job.dieline + Job.art_size_mm + Job.legend_swatches (WS-D).

Three new JSONB columns that carry the packaging inspector outputs
onto ``JobResponse`` for the Art Info viewer panel (WS-E).

* ``dieline`` — ``DielineResult`` as JSON:
  ``{source, polylines, spot_name, confidence}``.
* ``art_size_mm`` — ``{width_mm, height_mm}`` or ``NULL`` when
  the dieline is missing.
* ``legend_swatches`` — list of ``SwatchClassification`` JSON.

Revision ID: 040
Revises: 039
Create Date: 2026-04-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "dieline",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "art_size_mm",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "legend_swatches",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("jobs", "legend_swatches")
    op.drop_column("jobs", "art_size_mm")
    op.drop_column("jobs", "dieline")
