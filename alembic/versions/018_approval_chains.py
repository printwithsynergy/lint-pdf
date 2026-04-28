"""Add approval chain templates, chains, and steps.

Revision ID: 018
Revises: 017
Create Date: 2026-04-12
"""

from alembic import op
import sqlalchemy as sa


revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_chain_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("steps", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_templates_tenant", "approval_chain_templates", ["tenant_id"])

    op.create_table(
        "approval_chains",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("steps", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["approval_chain_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_chains_tenant_status", "approval_chains", ["tenant_id", "status"])
    op.create_index("ix_approval_chains_job", "approval_chains", ["job_id"], unique=True)

    op.create_table(
        "approval_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chain_id", sa.Uuid(), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(100), nullable=False),
        sa.Column("approver_email", sa.String(255), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_token", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chain_id"], ["approval_chains.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_steps_chain", "approval_steps", ["chain_id", "step_index"])
    op.create_index("ix_approval_steps_token", "approval_steps", ["access_token"], unique=True)
    op.create_index("ix_approval_steps_pending_expiry", "approval_steps", ["decision", "expires_at"])


def downgrade() -> None:
    op.drop_index("ix_approval_steps_pending_expiry", table_name="approval_steps")
    op.drop_index("ix_approval_steps_token", table_name="approval_steps")
    op.drop_index("ix_approval_steps_chain", table_name="approval_steps")
    op.drop_table("approval_steps")
    op.drop_index("ix_approval_chains_job", table_name="approval_chains")
    op.drop_index("ix_approval_chains_tenant_status", table_name="approval_chains")
    op.drop_table("approval_chains")
    op.drop_index("ix_approval_templates_tenant", table_name="approval_chain_templates")
    op.drop_table("approval_chain_templates")
