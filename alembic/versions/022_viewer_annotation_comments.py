"""Annotation comment threads + email fan-out support.

Adds ``viewer_annotation_comments`` so reviewers can hold a threaded
conversation on a :class:`ViewerAnnotation` (Wave B). Comments mirror
the parent annotation's ``share_token`` so the public-share routes can
filter without joining.

Revision ID: 022
Revises: 021
Create Date: 2026-04-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "viewer_annotation_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("annotation_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("share_token", sa.String(length=255), nullable=True),
        sa.Column("author_email", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["annotation_id"], ["viewer_annotations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_viewer_ann_comments_annotation",
        "viewer_annotation_comments",
        ["annotation_id", "created_at"],
    )
    op.create_index(
        "ix_viewer_ann_comments_token",
        "viewer_annotation_comments",
        ["share_token"],
    )


def downgrade() -> None:
    op.drop_index("ix_viewer_ann_comments_token", table_name="viewer_annotation_comments")
    op.drop_index("ix_viewer_ann_comments_annotation", table_name="viewer_annotation_comments")
    op.drop_table("viewer_annotation_comments")
