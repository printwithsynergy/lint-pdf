"""Webhook delivery audit table + replay support.

Adds ``webhook_deliveries`` so every dispatched event is persisted with
its signed payload + final status. Enables the new replay endpoint
(``POST /api/v1/webhooks/deliveries/{id}/replay``) and gives operators a
listing of what went out for which tenant.

Previously the dispatcher was fire-and-forget: a failed delivery only
left a line in the engine log, which made "a customer says their
webhook stopped firing — show me the last week of attempts" impossible
to answer. Every column is additive; no backfill needed for existing
webhook subscribers.

Revision ID: 028
Revises: 027
Create Date: 2026-04-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("webhook_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_status_code", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_error", sa.String(1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["webhook_id"], ["webhook_endpoints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_webhook_deliveries_webhook_id",
        "webhook_deliveries",
        ["webhook_id"],
    )
    op.create_index(
        "ix_webhook_deliveries_tenant_id",
        "webhook_deliveries",
        ["tenant_id"],
    )
    op.create_index(
        "ix_webhook_deliveries_endpoint_created",
        "webhook_deliveries",
        ["webhook_id", "created_at"],
    )
    op.create_index(
        "ix_webhook_deliveries_tenant_created",
        "webhook_deliveries",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_webhook_deliveries_event_created",
        "webhook_deliveries",
        ["event", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_event_created", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_tenant_created", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_endpoint_created", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_tenant_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_webhook_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
