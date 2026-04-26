"""Phase 0.7 PR-A — workflow column completeness + resolved-config snapshot.

Builds on the V-07/V-08 substrate (alembic 042/043). Two concerns in one
migration, both additive:

1. ``workflows`` gains four columns missing from the original V-07 cut:

   * ``is_active`` — soft-delete flag. NULL-safe default ``TRUE`` lets
     existing rows survive the ALTER without a backfill loop.
   * ``response_mode`` — CHECK enum (``async`` / ``sync``) carried over
     from the legacy ``custom_endpoints.response_mode`` column. Default
     ``async`` matches the prior CustomEndpoint default.
   * ``server_revision`` — monotonic counter bumped on every config
     mutation that targets this workflow. Used by the desktop reconcile
     path (Q-E4) so offline edits can be reordered against the server's
     authoritative sequence on reconnect. Default ``1`` so existing
     rows have a non-null starting point.
   * ``created_by_user_id`` — opaque Prisma cuid string matching the
     ``set_by`` convention on ``toggle_overrides``. Nullable; rows
     produced by data migrations leave it ``NULL``.

2. ``resolved_config_snapshots`` — per-job durable record of the merged
   configuration that drove that job, with per-field provenance. Every
   job submission writes one row at resolve time so audit views can
   answer "what config was active when finding F-22 fired on this job"
   even after the workflow has since been edited (Q-W2).

The snapshot table is small (~5 KB per row); at current scale (50k
jobs/day at peak) it grows ~90 GB / year. Partitioning by month is
deferred until row count crosses 50M.

Revision ID: 044
Revises: 043
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── workflows column completeness ────────────────────────────────
    op.add_column(
        "workflows",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "workflows",
        sa.Column(
            "response_mode",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'async'"),
        ),
    )
    op.create_check_constraint(
        "ck_workflows_response_mode",
        "workflows",
        "response_mode IN ('async', 'sync')",
    )
    op.add_column(
        "workflows",
        sa.Column(
            "server_revision",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "workflows",
        sa.Column(
            "created_by_user_id",
            sa.String(length=128),
            nullable=True,
        ),
    )

    # New partial-unique index: only one is_default workflow per tenant
    # AMONG ACTIVE rows. The original 042 partial index didn't account
    # for soft-delete. Drop it first if present, then recreate with the
    # is_active condition. Using IF EXISTS so idempotent replays survive.
    op.execute(sa.text("DROP INDEX IF EXISTS ix_workflows_default_per_tenant"))
    op.create_index(
        "ix_workflows_default_per_tenant",
        "workflows",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_default = TRUE AND is_active = TRUE"),
    )

    # ── resolved_config_snapshots ────────────────────────────────────
    op.create_table(
        "resolved_config_snapshots",
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_id",
            sa.String(length=64),
            sa.ForeignKey("workflows.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "resolved_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "system_default_version",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_resolved_config_snapshots_tenant_recent",
        "resolved_config_snapshots",
        ["tenant_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_resolved_config_snapshots_workflow_recent",
        "resolved_config_snapshots",
        ["workflow_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_resolved_config_snapshots_workflow_recent",
        table_name="resolved_config_snapshots",
    )
    op.drop_index(
        "ix_resolved_config_snapshots_tenant_recent",
        table_name="resolved_config_snapshots",
    )
    op.drop_table("resolved_config_snapshots")

    # Restore the original 042 partial unique index (without is_active)
    op.drop_index("ix_workflows_default_per_tenant", table_name="workflows")
    op.create_index(
        "ix_workflows_default_per_tenant",
        "workflows",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_default = TRUE"),
    )

    op.drop_column("workflows", "created_by_user_id")
    op.drop_column("workflows", "server_revision")
    op.drop_constraint("ck_workflows_response_mode", "workflows", type_="check")
    op.drop_column("workflows", "response_mode")
    op.drop_column("workflows", "is_active")
