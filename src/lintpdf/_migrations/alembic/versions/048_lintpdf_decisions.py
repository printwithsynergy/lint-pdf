"""Wave V V-05 — lintpdf_decisions audit-trail table.

Per-document, per-finding, per-operator decision audit table per
playbook §14.3. Captures every disposition an operator makes against
a job or finding (approve / reject / waive / suppress / annotate)
together with the actor, surface, and a correlation request id.

Decisions are append-only: revocation marks ``revoked_at`` /
``revoked_by_user_id`` / ``revoked_reason`` rather than deleting the
row, so audit replays stay correct even after an operator changes
their mind.

Indexes optimize the three common audit queries:

* ``(tenant_id, job_id)`` — "show every decision on this job"
* ``(tenant_id, finding_id)`` — "show every decision on this finding"
* ``(tenant_id, decided_by_user_id)`` — "show every decision this
  operator made"
* ``(tenant_id, decided_at DESC)`` — tenant audit timeline

Revision ID: 048
Revises: 047
Create Date: 2026-04-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lintpdf_decisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_findings.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("decision_type", sa.String(length=32), nullable=False),
        sa.Column("decision_value", sa.String(length=255), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_by_user_id", sa.String(length=128), nullable=False),
        sa.Column("decided_by_email", sa.String(length=255), nullable=True),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.String(length=128), nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "source IN ('dashboard','api','plugin','sdk','share_link',"
            "'approval_chain','desktop','system','migration')",
            name="ck_lintpdf_decisions_source",
        ),
    )
    op.create_index(
        "ix_lintpdf_decisions_tenant_job",
        "lintpdf_decisions",
        ["tenant_id", "job_id"],
    )
    op.create_index(
        "ix_lintpdf_decisions_tenant_finding",
        "lintpdf_decisions",
        ["tenant_id", "finding_id"],
        postgresql_where=sa.text("finding_id IS NOT NULL"),
    )
    op.create_index(
        "ix_lintpdf_decisions_tenant_actor",
        "lintpdf_decisions",
        ["tenant_id", "decided_by_user_id"],
    )
    op.create_index(
        "ix_lintpdf_decisions_tenant_recent",
        "lintpdf_decisions",
        ["tenant_id", sa.text("decided_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_lintpdf_decisions_tenant_recent", table_name="lintpdf_decisions")
    op.drop_index("ix_lintpdf_decisions_tenant_actor", table_name="lintpdf_decisions")
    op.drop_index("ix_lintpdf_decisions_tenant_finding", table_name="lintpdf_decisions")
    op.drop_index("ix_lintpdf_decisions_tenant_job", table_name="lintpdf_decisions")
    op.drop_table("lintpdf_decisions")
