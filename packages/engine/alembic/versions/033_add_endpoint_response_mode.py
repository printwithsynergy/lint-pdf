"""Custom endpoint response_mode (async default, sync opt-in).

The ``/api/v1/endpoints/{slug}/submit`` route has always returned 202 and
the caller has had to poll ``/api/v1/jobs/{id}`` until the job reached a
terminal state. That's the right default for hundreds-of-files batches
and for customers wiring the API into a hot folder, but it's a poor fit
for the "drop one PDF, get the verdict inline" use-case — typically a
Zapier/n8n/Make.com integration that can't orchestrate a polling loop.

The response_mode column lets tenants flip a per-endpoint knob:

* ``async`` (default, current behavior) — 202 + job id, caller polls.
* ``sync``                              — the submit request blocks until
                                          the job is terminal (up to the
                                          configured max wait), then
                                          returns the full JobResponse.

VARCHAR(16) + CHECK constraint keeps the enum in Postgres without paying
for a native enum type we'd otherwise have to ``CREATE TYPE ... ADD
VALUE`` against on every future extension (``stream`` is an obvious
follow-up).

Revision ID: 033
Revises: 032
Create Date: 2026-04-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "custom_endpoints",
        sa.Column(
            "response_mode",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'async'"),
        ),
    )
    op.create_check_constraint(
        "ck_custom_endpoints_response_mode",
        "custom_endpoints",
        "response_mode IN ('async', 'sync')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_custom_endpoints_response_mode",
        "custom_endpoints",
        type_="check",
    )
    op.drop_column("custom_endpoints", "response_mode")
