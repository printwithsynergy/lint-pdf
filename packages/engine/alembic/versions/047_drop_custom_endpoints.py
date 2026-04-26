"""Phase 0.7 PR-B5 — drop the legacy custom_endpoints table.

Last of the five legacy tenant-config tables. Endpoints are now backed
by ``workflows`` rows + the unified-config substrate's
``endpoint_defaults`` ToggleOverride at WORKFLOW scope. Every consumer
(``api/routes/endpoints.py`` route + the worker hot path) reads from
the new shape.

``Job.endpoint_id`` column (if any) is left behind — historical jobs
that came in via the legacy submit-via-endpoint path keep their
reference for audit. The column has no FK now (was never created with
one in the legacy schema).

Revision ID: 047
Revises: 046
Create Date: 2026-04-26
"""

from __future__ import annotations

from alembic import op

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("custom_endpoints")


def downgrade() -> None:
    raise RuntimeError(
        "047_drop_custom_endpoints: irreversible. Endpoint metadata lives in"
        " workflows + endpoint_defaults ToggleOverride rows now; restore from"
        " a Railway volume snapshot if a rollback is required."
    )
