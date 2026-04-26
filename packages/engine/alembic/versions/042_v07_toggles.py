"""Wave V V-07 — toggle resolver + workflows.

Adds three tables for the per-tenant configuration cascade:

* ``workflows`` — first-class named scope above per-call overrides
  (e.g. "Packaging — Folding Carton"). Each tenant can define many
  workflows and exactly one ``is_default`` row per tenant.
* ``toggles`` — registry of every configurable knob in the system.
  Identified by dot-notation IDs (``checks.F-22.severity_override``,
  ``epm_thresholds.tac_limit_coated_pct``). Holds the registry-default
  value, allowed range, override scopes, lockability, and merge strategy.
* ``toggle_overrides`` — stored per-scope override values keyed by
  (toggle_id, scope, scope_id) where scope is TENANT, WORKFLOW, or
  CALL and scope_id is the tenant uuid, workflow id, or call id
  respectively. ``locked = TRUE`` only honored at TENANT scope.

Tenant scope FK uses Postgres native ``uuid`` to match
``tenants.id``. Workflow scope FK uses VARCHAR (cuid) to match
the Prisma-owned PK pattern used elsewhere for app-managed rows.
The CALL scope_id is opaque — a per-job nonce — so it is also
VARCHAR with no FK.

Revision ID: 042
Revises: 041
Create Date: 2026-04-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


# Postgres has no ``CREATE TYPE IF NOT EXISTS``. The idiomatic equivalent
# is a DO block that traps ``duplicate_object`` so re-runs (e.g. after a
# create_all/stamp fallback in lifespan, or a partial migration replay)
# don't bring the whole upgrade down. Raw SQL avoids SQLAlchemy's
# enum-creation event handlers entirely — those handlers fire from
# multiple paths (op.create_table column refs, postgresql.ARRAY wrappers)
# and any one of them issuing a bare ``CREATE TYPE`` without IF-NOT-EXISTS
# semantics aborts the migration with DuplicateObject.
def _create_enum_idempotent(name: str, *values: str) -> None:
    quoted = ", ".join(f"'{v}'" for v in values)
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                CREATE TYPE {name} AS ENUM ({quoted});
            EXCEPTION
                WHEN duplicate_object THEN
                    NULL;
            END
            $$;
            """
        )
    )


def upgrade() -> None:
    _create_enum_idempotent("toggle_type", "BOOLEAN", "NUMERIC", "ENUM", "STRING", "OBJECT")
    _create_enum_idempotent("toggle_scope", "TENANT", "WORKFLOW", "CALL")
    _create_enum_idempotent("merge_strategy", "REPLACE", "MERGE", "UNION")

    # All column references below carry ``create_type=False`` so the
    # column-level enum descriptors won't re-fire CREATE TYPE during
    # op.create_table (matches the 043 audit-log migration pattern).

    op.create_table(
        "workflows",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("human_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_workflows_tenant_slug"),
    )
    op.create_index(
        "ix_workflows_tenant_id",
        "workflows",
        ["tenant_id"],
    )
    # Exactly one default workflow per tenant — partial unique index.
    op.create_index(
        "ix_workflows_default_per_tenant",
        "workflows",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("is_default = TRUE"),
    )

    op.create_table(
        "toggles",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("human_name", sa.String(length=255), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                "BOOLEAN",
                "NUMERIC",
                "ENUM",
                "STRING",
                "OBJECT",
                name="toggle_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "default_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "allowed_range",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "override_at",
            postgresql.ARRAY(
                postgresql.ENUM(
                    "TENANT",
                    "WORKFLOW",
                    "CALL",
                    name="toggle_scope",
                    create_type=False,
                )
            ),
            nullable=False,
            server_default=sa.text("ARRAY['TENANT','WORKFLOW','CALL']::toggle_scope[]"),
        ),
        sa.Column(
            "lockable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "merge_strategy",
            postgresql.ENUM(
                "REPLACE",
                "MERGE",
                "UNION",
                name="merge_strategy",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'REPLACE'::merge_strategy"),
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_toggles_category", "toggles", ["category"])

    op.create_table(
        "toggle_overrides",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "toggle_id",
            sa.String(length=255),
            sa.ForeignKey("toggles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scope",
            postgresql.ENUM(
                "TENANT",
                "WORKFLOW",
                "CALL",
                name="toggle_scope",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("scope_id", sa.String(length=128), nullable=False),
        sa.Column(
            "value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "locked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("set_by", sa.String(length=128), nullable=False),
        sa.Column(
            "set_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("surface", sa.String(length=32), nullable=False),
        sa.UniqueConstraint(
            "toggle_id",
            "scope",
            "scope_id",
            name="uq_toggle_overrides_scope",
        ),
    )
    op.create_index(
        "ix_toggle_overrides_scope_lookup",
        "toggle_overrides",
        ["scope", "scope_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_toggle_overrides_scope_lookup", table_name="toggle_overrides")
    op.drop_table("toggle_overrides")
    op.drop_index("ix_toggles_category", table_name="toggles")
    op.drop_table("toggles")
    op.drop_index("ix_workflows_default_per_tenant", table_name="workflows")
    op.drop_index("ix_workflows_tenant_id", table_name="workflows")
    op.drop_table("workflows")
    # Use raw SQL with IF EXISTS for symmetric idempotency with upgrade().
    op.execute(sa.text("DROP TYPE IF EXISTS merge_strategy"))
    op.execute(sa.text("DROP TYPE IF EXISTS toggle_scope"))
    op.execute(sa.text("DROP TYPE IF EXISTS toggle_type"))
