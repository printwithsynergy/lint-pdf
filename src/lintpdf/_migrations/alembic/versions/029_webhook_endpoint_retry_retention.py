"""Per-endpoint retry + retention config on webhook_endpoints.

Adds five nullable columns so tenants can tune their webhook delivery
behaviour without asking ops to flip global defaults:

* ``max_retries``              — upper bound on ``dispatch_webhook``
                                 retries; falls back to the Celery
                                 decorator default (3) when NULL.
* ``retry_base_delay_seconds`` — first-retry delay; exponential
                                 doubling after that, capped by
                                 ``retry_max_delay_seconds``.
* ``retry_max_delay_seconds``  — ceiling on the exponential backoff so
                                 an aggressive ``max_retries`` doesn't
                                 produce absurdly long waits.
* ``delivery_retention_days``  — how many days ``WebhookDelivery`` rows
                                 stick around before the sweep deletes
                                 them. NULL = forever.
* ``retention_overrides``      — JSON dict of glob → days, e.g.
                                 ``{"billing.*": 365, "annotation.*": 7}``.
                                 Takes precedence over
                                 ``delivery_retention_days`` for
                                 matching event names.

All columns are additive + nullable, so existing tenants keep their
current behaviour (global defaults) until they opt in.

Revision ID: 029
Revises: 028
Create Date: 2026-04-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("webhook_endpoints") as batch:
        batch.add_column(
            sa.Column("max_retries", sa.Integer(), nullable=True),
        )
        batch.add_column(
            sa.Column("retry_base_delay_seconds", sa.Integer(), nullable=True),
        )
        batch.add_column(
            sa.Column("retry_max_delay_seconds", sa.Integer(), nullable=True),
        )
        batch.add_column(
            sa.Column("delivery_retention_days", sa.Integer(), nullable=True),
        )
        batch.add_column(
            sa.Column("retention_overrides", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    with op.batch_alter_table("webhook_endpoints") as batch:
        batch.drop_column("retention_overrides")
        batch.drop_column("delivery_retention_days")
        batch.drop_column("retry_max_delay_seconds")
        batch.drop_column("retry_base_delay_seconds")
        batch.drop_column("max_retries")
