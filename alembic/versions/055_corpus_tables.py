"""Corpus testing tables (assays, runs, run_assays).

Adds the three tables that back the corpus-testing / golden-master
regression feature:

  corpus_assays      — registered test-fixture PDFs with expected findings
  corpus_runs        — a batch run of assays against a profile
  corpus_run_assays  — per-assay result join table

Revision ID: 055
Revises: 054
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "corpus_assays",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("pdf_storage_key", sa.String(512), nullable=False),
        sa.Column("pdf_hash", sa.String(64), nullable=False),
        sa.Column(
            "expected_findings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_corpus_assays_tenant_created", "corpus_assays", ["tenant_id", "created_at"]
    )

    op.create_table(
        "corpus_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "processing",
                "passed",
                "failed",
                "error",
                name="corpusrunstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("assay_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pass_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "certificate_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_corpus_runs_tenant_created", "corpus_runs", ["tenant_id", "created_at"]
    )

    op.create_table(
        "corpus_run_assays",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("assay_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "passed",
                "failed",
                "error",
                name="corpusassaystatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "bootstrapped",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "diff_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assay_id"], ["corpus_assays.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["corpus_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_corpus_run_assays_run", "corpus_run_assays", ["run_id"])
    op.create_index("ix_corpus_run_assays_assay", "corpus_run_assays", ["assay_id"])


def downgrade() -> None:
    op.drop_index("ix_corpus_run_assays_assay", table_name="corpus_run_assays")
    op.drop_index("ix_corpus_run_assays_run", table_name="corpus_run_assays")
    op.drop_table("corpus_run_assays")
    op.execute("DROP TYPE IF EXISTS corpusassaystatus")

    op.drop_index("ix_corpus_runs_tenant_created", table_name="corpus_runs")
    op.drop_table("corpus_runs")
    op.execute("DROP TYPE IF EXISTS corpusrunstatus")

    op.drop_index("ix_corpus_assays_tenant_created", table_name="corpus_assays")
    op.drop_table("corpus_assays")
