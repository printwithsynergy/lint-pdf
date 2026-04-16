"""Tenant-level toggle for share-link email capture.

Adds ``tenants.share_email_required`` so admins can flip off the email
gate for tenants who share preflight reports internally and don't need
lead-gen on every share-link click. The engine route that validates
share tokens previously hard-coded ``email_required=True`` regardless
of tenant settings; this column + the route edit in the same commit
wire an actual preference through.

Defaults to ``True`` to preserve the pre-existing behaviour for every
row that existed before this migration.

Revision ID: 024
Revises: 023
Create Date: 2026-04-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "share_email_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "share_email_required")
