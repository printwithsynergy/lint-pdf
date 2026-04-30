"""Viewer annotations + share-link visitor capture.

Adds the ``viewer_annotations`` table (rect / circle / arrow / freehand /
note primitives with PDF-point geometry), the ``share_link_visitors``
audit table for anonymous reviewers, and a new ``allow_annotations``
boolean column on ``report_tokens`` that gates writes from the public
``/view/{token}`` viewer.

Revision ID: 021
Revises: 020
Create Date: 2026-04-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "viewer_annotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("share_token", sa.String(length=255), nullable=True),
        sa.Column("page_num", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("geometry_json", sa.JSON(), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False, server_default="#dc2626"),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("author_email", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_viewer_annotations_job_page",
        "viewer_annotations",
        ["job_id", "page_num"],
    )
    op.create_index("ix_viewer_annotations_token", "viewer_annotations", ["share_token"])

    op.create_table(
        "share_link_visitors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("share_token", sa.String(length=255), nullable=False),
        sa.Column("visitor_email", sa.String(length=255), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_share_visitors_token", "share_link_visitors", ["share_token"])
    op.create_index(
        "ix_share_visitors_token_email",
        "share_link_visitors",
        ["share_token", "visitor_email"],
    )

    op.add_column(
        "report_tokens",
        sa.Column(
            "allow_annotations",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("report_tokens", "allow_annotations")
    op.drop_index("ix_share_visitors_token_email", table_name="share_link_visitors")
    op.drop_index("ix_share_visitors_token", table_name="share_link_visitors")
    op.drop_table("share_link_visitors")
    op.drop_index("ix_viewer_annotations_token", table_name="viewer_annotations")
    op.drop_index("ix_viewer_annotations_job_page", table_name="viewer_annotations")
    op.drop_table("viewer_annotations")
