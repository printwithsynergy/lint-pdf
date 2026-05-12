"""Widen ``report_tokens.format`` from VARCHAR(10) to VARCHAR(32).

The original schema sized ``format`` for the initial 4-value set
(``html``, ``pdf``, ``json``, ``xml``). When ``annotated_pdf`` (13
chars) and ``annotated_pdf_markup`` (20 chars) shipped, every mint
request that asked for either format blew up with
``StringDataRightTruncation`` and returned HTTP 500 — the error
surfaced only at INSERT time, so the Python model layer happily
produced bytes and uploaded them to R2 before the token row failed
to persist, leaving orphaned objects in storage on every attempt.

Widening to VARCHAR(32) fits every current value plus room for
future additions without reaching for unbounded TEXT.

Revision ID: 023
Revises: 022
Create Date: 2026-04-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "report_tokens",
        "format",
        existing_type=sa.String(length=10),
        type_=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Narrowing back to VARCHAR(10) would truncate existing
    # ``annotated_pdf`` / ``annotated_pdf_markup`` rows, so delete them
    # first to avoid silent data loss on a rollback.
    op.execute(
        "DELETE FROM report_tokens WHERE format IN ('annotated_pdf', 'annotated_pdf_markup')"
    )
    op.alter_column(
        "report_tokens",
        "format",
        existing_type=sa.String(length=32),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
