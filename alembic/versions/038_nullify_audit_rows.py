"""Null Modal-era audit rows + seed scoped re-audit queue (WS-H).

Clean-slate migration:
* Nulls every ``job_findings.audit_*`` column where the audit was
  produced by something other than Claude Haiku / Sonnet / Opus.
  The Modal Qwen2-VL fallback is gone (WS-A), and 0/3275 of its
  verdicts made it onto the HSI smoke job, so re-running them
  through Claude is a net win.
* Creates ``ai_audit_rerun_queue`` with a single ``job_id`` PK.
  A worker boot hook drains the queue by enqueueing
  ``audit_findings_async.delay(job_id)`` and deleting rows on
  success.
* Seeds the queue with up to 100 most-recent complete jobs
  **whose tenant is opted-in to the ``audit`` feature** (the
  resolver's union-merge, approximated here with a SQL lookup
  against ``tenants.ai_features @> '["audit"]'::jsonb``).

Depends on 037 having landed first — the ``@>`` predicate needs
the ``ai_features`` column.

Revision ID: 038
Revises: 037
Create Date: 2026-04-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE job_findings
           SET audit_status    = NULL,
               audit_rationale = NULL,
               audit_model     = NULL,
               audit_at        = NULL
         WHERE audit_model IS NULL
            OR audit_model NOT LIKE 'claude-%'
        """
    )

    op.create_table(
        "ai_audit_rerun_queue",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Seed ONLY jobs whose tenant has been granted the audit feature.
    # Avoids surprise Haiku spend on tenants who weren't opted in.
    op.execute(
        """
        INSERT INTO ai_audit_rerun_queue (job_id)
        SELECT j.id
          FROM jobs j
          JOIN tenants t ON t.id = j.tenant_id
         WHERE j.status = 'complete'
           AND t.ai_features @> '["audit"]'::jsonb
         ORDER BY j.completed_at DESC NULLS LAST
         LIMIT 100
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("ai_audit_rerun_queue")
    # audit_* nulling is not reversible — skipping the restore.
