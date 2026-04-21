"""Composite index on ``jobs(tenant_id, status)``.

The dashboard's job-list view filters by ``tenant_id`` **and** ``status``
(``PENDING``, ``PROCESSING``, ``COMPLETED``, ``FAILED``) simultaneously.
The pre-existing ``ix_jobs_tenant_created`` index covers tenant scoping
plus ordering, but adds nothing for the ``status`` predicate, leaving
Postgres to filter the post-index-scan rows in memory. Once a tenant
accumulates more than ~10k jobs the partial filter dominates the query
plan.

This migration adds ``ix_jobs_tenant_status`` so the planner can satisfy
both predicates from a single index scan. Additive, zero-risk.

Revision ID: 031
Revises: 030
Create Date: 2026-04-20
"""

from __future__ import annotations

from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_jobs_tenant_status",
        "jobs",
        ["tenant_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_tenant_status", table_name="jobs")
