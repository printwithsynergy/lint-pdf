"""Drop vestigial custom_domain_alias columns.

The CF-Worker branded-subdomain flow was retired in favor of the Fly.io
Caddy edge. Every BYO customer CNAMEs directly at ``edge.lintpdf.com``;
the per-tenant ``{slug}-custom.lintpdf.com`` alias is no longer
provisioned or read by any code path. Columns become vestigial noise
on the row.

Dropped from both ``tenants`` and ``brand_profiles``:

* ``custom_domain_alias``
* ``app_custom_domain_alias``

Revision ID: 030
Revises: 029
Create Date: 2026-04-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tenants") as batch:
        batch.drop_column("custom_domain_alias")
        batch.drop_column("app_custom_domain_alias")
    with op.batch_alter_table("brand_profiles") as batch:
        batch.drop_column("custom_domain_alias")
        batch.drop_column("app_custom_domain_alias")


def downgrade() -> None:
    with op.batch_alter_table("brand_profiles") as batch:
        batch.add_column(sa.Column("app_custom_domain_alias", sa.String(255), nullable=True))
        batch.add_column(sa.Column("custom_domain_alias", sa.String(255), nullable=True))
    with op.batch_alter_table("tenants") as batch:
        batch.add_column(sa.Column("app_custom_domain_alias", sa.String(255), nullable=True))
        batch.add_column(sa.Column("custom_domain_alias", sa.String(255), nullable=True))
