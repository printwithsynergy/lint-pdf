"""Per-customer brand specifications (WS-11).

Introduces the ``brand_specs`` table so a tenant can maintain many
named colour specifications — one per end-customer or product —
and select which one applies at the endpoint level (endpoint
default) or per-submission (job override). Replaces the legacy
``tenant_ai_configs.brand_palette`` single-palette-per-tenant
model.

Existing ``brand_palette`` values are migrated to a BrandSpec row
named ``"Default palette (migrated)"`` with ``is_default = TRUE``
so the tenant keeps its resolved brand palette without any
re-work. The legacy ``brand_palette`` JSONB column stays in place
for one release cycle as a read-only fallback for services that
haven't yet been updated; a follow-up migration drops it once the
field is fully dormant.

Two FK columns are added for resolution chaining:

* ``custom_endpoints.default_brand_spec_id`` — endpoint-level
  default applied to every submission through that endpoint.
* ``jobs.brand_spec_id`` — per-submission override captured at
  submit time; wins over the endpoint default and the tenant
  default row.

Both FKs use ``ON DELETE SET NULL`` so archiving or deleting a
spec doesn't cascade-destroy historical jobs or endpoint configs.

Revision ID: 041
Revises: 040
Create Date: 2026-04-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── brand_specs ─────────────────────────────────────────────
    op.create_table(
        "brand_specs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "colors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "rich_black_spec",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_brand_specs_tenant_id",
        "brand_specs",
        ["tenant_id"],
    )
    # Partial-unique index so at most one tenant-default-active
    # spec exists per tenant. Archived specs fall out of the
    # predicate so an archived default doesn't block creating a
    # fresh one.
    op.create_index(
        "ix_brand_specs_tenant_default",
        "brand_specs",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_default AND NOT is_archived"),
    )

    # ── custom_endpoints.default_brand_spec_id ─────────────────
    op.add_column(
        "custom_endpoints",
        sa.Column(
            "default_brand_spec_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brand_specs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ── jobs.brand_spec_id ─────────────────────────────────────
    op.add_column(
        "jobs",
        sa.Column(
            "brand_spec_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brand_specs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ── backfill from tenant_ai_configs.brand_palette ──────────
    # For every tenant_ai_configs row that carries a non-empty
    # brand_palette today, synthesise a default BrandSpec so the
    # tenant's existing palette keeps resolving without manual
    # migration through the UI. The legacy JSONB column itself is
    # left alone — dropping it belongs in a follow-up revision
    # once every consumer reads from BrandSpec.
    op.execute(
        sa.text(
            """
            INSERT INTO brand_specs (
                id, tenant_id, name, customer_name, description,
                colors, rich_black_spec, is_default, is_archived,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                tac.tenant_id,
                'Default palette (migrated)',
                NULL,
                'Migrated automatically from tenant_ai_configs.brand_palette.',
                tac.brand_palette::jsonb,
                NULL,
                TRUE,
                FALSE,
                NOW(),
                NOW()
            FROM tenant_ai_configs tac
            WHERE tac.brand_palette IS NOT NULL
              AND jsonb_array_length(tac.brand_palette::jsonb) > 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM brand_specs bs
                  WHERE bs.tenant_id = tac.tenant_id AND bs.is_default
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_column("jobs", "brand_spec_id")
    op.drop_column("custom_endpoints", "default_brand_spec_id")
    op.drop_index("ix_brand_specs_tenant_default", table_name="brand_specs")
    op.drop_index("ix_brand_specs_tenant_id", table_name="brand_specs")
    op.drop_table("brand_specs")
