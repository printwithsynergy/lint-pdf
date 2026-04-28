"""Webhook dead-letter flag + replay counter.

Before this migration the webhook dispatcher exhausted its retries and
logged a warning; the audit row on ``webhook_deliveries`` was left with
``success=false`` but there was no efficient way for operators to
enumerate "deliveries that gave up", and no bookkeeping for manual
replays triggered from the admin UI.

Adds two columns plus a partial index so the admin dead-letter view can
stay snappy even when the table grows into the millions of rows:

* ``is_dead``       — True once ``MaxRetriesExceededError`` fires. Flips
                      back to False when an operator replays via
                      ``POST /api/v1/webhooks/deliveries/{id}/replay``.
* ``replay_count``  — number of manual replays kicked off against this
                      delivery. Spots chronic-failing endpoints.

The partial index ``ix_webhook_deliveries_dead`` only indexes the rows
where ``is_dead = true`` — the steady-state expectation is that the
overwhelming majority of deliveries succeed, so a partial index costs
essentially nothing while giving the admin view an O(log N) scan.

Revision ID: 032
Revises: 031
Create Date: 2026-04-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("webhook_deliveries") as batch:
        batch.add_column(
            sa.Column(
                "is_dead",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
        batch.add_column(
            sa.Column(
                "replay_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )

    op.create_index(
        "ix_webhook_deliveries_dead",
        "webhook_deliveries",
        ["tenant_id", "created_at"],
        unique=False,
        postgresql_where=sa.text("is_dead = true"),
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_dead", table_name="webhook_deliveries")
    with op.batch_alter_table("webhook_deliveries") as batch:
        batch.drop_column("replay_count")
        batch.drop_column("is_dead")
