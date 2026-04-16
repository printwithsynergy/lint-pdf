"""Per-token override for the share-link email gate.

Adds ``report_tokens.require_visitor_email`` so a single tenant can
mint "gated" share links (external distribution) *and* "ungated"
share links (internal review) in the same session without flipping
the tenant-wide ``share_email_required`` flag between calls.

``NULL`` → inherit the tenant's default. ``True`` / ``False`` → force
the gate on / off regardless of tenant setting. The validator endpoint
resolves token-first, tenant-second, ``True`` last.

Revision ID: 025
Revises: 024
Create Date: 2026-04-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_tokens",
        sa.Column("require_visitor_email", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("report_tokens", "require_visitor_email")
