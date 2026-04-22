"""AI accuracy audit — per-finding verdict columns.

Workstream 3 of the Amalgam_Catalyst follow-up. Every ``JobFinding``
gets four optional columns that the Opus-internal / Modal-customer
auditors populate after preflight completes:

* ``audit_status``     — ``confirmed`` / ``disputed`` / ``needs_context`` / ``error``.
* ``audit_rationale``  — one-sentence explanation (what the engine claims vs. what the PDF shows).
* ``audit_model``      — model identifier (e.g. ``claude-opus-4-7``, ``modal:qwen2-vl-7b``).
* ``audit_at``         — UTC timestamp of the verdict.

All four are NULL-able because auditing is opt-in; a job submitted
without ``ai_audit_enabled`` simply leaves them NULL. The viewer's
``<AuditChip/>`` renders nothing when the verdict is NULL, so the
column's default state is "no chip", not "unaudited".

Revision ID: 034
Revises: 033
Create Date: 2026-04-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_findings",
        sa.Column("audit_status", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "job_findings",
        sa.Column("audit_rationale", sa.Text(), nullable=True),
    )
    op.add_column(
        "job_findings",
        sa.Column("audit_model", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "job_findings",
        sa.Column("audit_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_job_findings_audit_status",
        "job_findings",
        "audit_status IS NULL OR audit_status IN "
        "('confirmed', 'disputed', 'needs_context', 'error')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_job_findings_audit_status",
        "job_findings",
        type_="check",
    )
    op.drop_column("job_findings", "audit_at")
    op.drop_column("job_findings", "audit_model")
    op.drop_column("job_findings", "audit_rationale")
    op.drop_column("job_findings", "audit_status")
