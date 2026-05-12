"""Add white-label custom report domain columns + data migration.

Adds verification + timestamp columns for tenant-level custom domains,
adds per-brand-profile custom domains, enforces uniqueness via partial
unique indexes, and rewrites any stored logo URLs that still point at
the obsolete reports.lintpdf.com default (which was never actually
configured in DNS).

Revision ID: 014
Revises: 013
Create Date: 2026-04-09
"""

from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003

import sqlalchemy as sa
from alembic import op

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- tenants: gate brand_custom_domain behind a verification flag -----
    op.add_column(
        "tenants",
        sa.Column(
            "brand_custom_domain_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "brand_custom_domain_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    # Each domain can only be claimed by one tenant (when not null).
    op.create_index(
        "ix_tenants_brand_custom_domain_unique",
        "tenants",
        ["brand_custom_domain"],
        unique=True,
        postgresql_where=sa.text("brand_custom_domain IS NOT NULL"),
    )

    # -- brand_profiles: optional per-profile custom domain ---------------
    op.add_column(
        "brand_profiles",
        sa.Column("custom_domain", sa.String(255), nullable=True),
    )
    op.add_column(
        "brand_profiles",
        sa.Column(
            "custom_domain_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "brand_profiles",
        sa.Column(
            "custom_domain_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_brand_profiles_custom_domain_unique",
        "brand_profiles",
        ["custom_domain"],
        unique=True,
        postgresql_where=sa.text("custom_domain IS NOT NULL"),
    )

    # -- data migration: rewrite dead reports.lintpdf.com logo URLs -------
    # An earlier draft defaulted the engine's report_base_url to
    # https://reports.lintpdf.com (never configured in DNS). Any logo
    # uploaded during that window has its URL baked in — rewrite to the
    # working api.lintpdf.com host so existing tenants keep their logos.
    op.execute(
        "UPDATE brand_profiles "
        "SET logo_url = REPLACE(logo_url, 'https://reports.lintpdf.com/', 'https://api.lintpdf.com/') "
        "WHERE logo_url LIKE 'https://reports.lintpdf.com/%'"
    )
    op.execute(
        "UPDATE tenants "
        "SET brand_logo_url = REPLACE(brand_logo_url, 'https://reports.lintpdf.com/', 'https://api.lintpdf.com/') "
        "WHERE brand_logo_url LIKE 'https://reports.lintpdf.com/%'"
    )


def downgrade() -> None:
    op.drop_index("ix_brand_profiles_custom_domain_unique", table_name="brand_profiles")
    op.drop_column("brand_profiles", "custom_domain_requested_at")
    op.drop_column("brand_profiles", "custom_domain_verified")
    op.drop_column("brand_profiles", "custom_domain")
    op.drop_index("ix_tenants_brand_custom_domain_unique", table_name="tenants")
    op.drop_column("tenants", "brand_custom_domain_requested_at")
    op.drop_column("tenants", "brand_custom_domain_verified")
