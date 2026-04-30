"""External preflight imports, minimal viewer mode, and unbranded outputs.

Adds:
- ``jobs.preflight_source`` (engine|external|minimal) — branching column for the
  Celery pipeline.
- ``jobs.external_format`` — format hint for imported third-party reports.
- ``jobs.data_capabilities`` — per-capability availability map read by the viewer.
- ``jobs.brand_profile_id_override`` — per-request brand override.
- ``jobs.unbranded_override`` — per-request unbranded toggle.
- ``tenants.unbranded_by_default`` — tenant-level unbranded default.
- ``job_imported_reports`` — raw third-party preflight artifacts keyed by job.
- ``report_tokens.brand_mode`` / ``brand_profile_id`` — branding captured
  at mint time so downstream viewers see consistent branding.

Revision ID: 019
Revises: 018
Create Date: 2026-04-12
"""

from alembic import op
import sqlalchemy as sa


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


_PREFLIGHT_SOURCE_ENUM = sa.Enum("engine", "external", "minimal", name="preflightsource")


def upgrade() -> None:
    bind = op.get_bind()
    _PREFLIGHT_SOURCE_ENUM.create(bind, checkfirst=True)

    op.add_column(
        "jobs",
        sa.Column(
            "preflight_source",
            _PREFLIGHT_SOURCE_ENUM,
            nullable=False,
            server_default="engine",
        ),
    )
    op.add_column("jobs", sa.Column("external_format", sa.String(32), nullable=True))
    op.add_column("jobs", sa.Column("data_capabilities", sa.JSON(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("brand_profile_id_override", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "unbranded_override",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    op.add_column(
        "tenants",
        sa.Column(
            "unbranded_by_default",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    op.create_table(
        "job_imported_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("format", sa.String(32), nullable=False),
        sa.Column("raw_blob_key", sa.String(512), nullable=False),
        sa.Column("raw_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parser_version", sa.String(32), nullable=False, server_default="1"),
        sa.Column("source_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "parsed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_imported_reports_job", "job_imported_reports", ["job_id"])

    op.add_column("report_tokens", sa.Column("brand_mode", sa.String(16), nullable=True))
    op.add_column("report_tokens", sa.Column("brand_profile_id", sa.Uuid(), nullable=True))


def downgrade() -> None:
    op.drop_column("report_tokens", "brand_profile_id")
    op.drop_column("report_tokens", "brand_mode")

    op.drop_index("ix_job_imported_reports_job", table_name="job_imported_reports")
    op.drop_table("job_imported_reports")

    op.drop_column("tenants", "unbranded_by_default")

    op.drop_column("jobs", "unbranded_override")
    op.drop_column("jobs", "brand_profile_id_override")
    op.drop_column("jobs", "data_capabilities")
    op.drop_column("jobs", "external_format")
    op.drop_column("jobs", "preflight_source")

    bind = op.get_bind()
    _PREFLIGHT_SOURCE_ENUM.drop(bind, checkfirst=True)
