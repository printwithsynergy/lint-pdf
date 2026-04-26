"""Wave V V-06 — webhook signing tenant-default secret.

Adds ``tenants.webhook_signing_secret`` so a tenant can carry a default
HMAC-SHA256 secret used for any of its ``webhook_endpoints`` whose own
``secret`` is NULL. Per Q-D3 the resolver order is per-webhook
override > tenant default > sign-time error.

Also relaxes ``webhook_endpoints.secret`` from NOT NULL to nullable
so an endpoint can opt into the tenant default by leaving its own
secret unset. Existing rows already carry per-endpoint secrets so
the relaxation is a safe widening.

Revision ID: 049
Revises: 048
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "webhook_signing_secret",
            sa.String(length=255),
            nullable=True,
        ),
    )

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("webhook_endpoints") as batch:
            batch.alter_column(
                "secret",
                existing_type=sa.String(length=255),
                nullable=True,
            )
        return

    op.alter_column(
        "webhook_endpoints",
        "secret",
        existing_type=sa.String(length=255),
        nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("webhook_endpoints") as batch:
            batch.alter_column(
                "secret",
                existing_type=sa.String(length=255),
                nullable=False,
            )
    else:
        op.alter_column(
            "webhook_endpoints",
            "secret",
            existing_type=sa.String(length=255),
            nullable=False,
        )
    op.drop_column("tenants", "webhook_signing_secret")
