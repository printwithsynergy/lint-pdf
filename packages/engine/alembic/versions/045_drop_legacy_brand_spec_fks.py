"""Phase 0.7 PR-B3d — drop legacy brand_specs FK constraints.

Removes the two foreign-key constraints that pin ``Job.brand_spec_id``
and ``CustomEndpoint.default_brand_spec_id`` to ``brand_specs.id``.
The columns themselves stay; their values now reference keys inside
the tenant's ``ToggleOverride(toggle_id='brand', scope=TENANT)`` dict
(per PR-B2 + PR-B3b) which the FK can't see.

Without this migration any caller persisting a Job or CustomEndpoint
with ``brand_spec_id`` referencing a spec id that lives only in the
new substrate raises ``IntegrityError(FK constraint failed)``.

After this migration the two columns become opaque foreign keys into
the unified-config substrate (the single source of truth post-PR-B3b).
PR-B4 drops the columns entirely when the legacy ``custom_endpoints``
and ``brand_specs`` tables are dropped together.

Revision ID: 045
Revises: 044
Create Date: 2026-04-26
"""

from __future__ import annotations

from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


# Postgres auto-names FK constraints ``<table>_<column>_fkey``.
_JOB_FK = "jobs_brand_spec_id_fkey"
_ENDPOINT_FK = "custom_endpoints_default_brand_spec_id_fkey"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite stores FKs inline on the column; the only way to
        # remove them is a table rebuild via ``batch_alter_table``,
        # which copies the table without the constraint. Production
        # is Postgres so this branch only runs in test harnesses; the
        # batch operation is a no-op when the FK was already dropped.
        with op.batch_alter_table("jobs") as batch:
            batch.drop_constraint(_JOB_FK, type_="foreignkey")
        with op.batch_alter_table("custom_endpoints") as batch:
            batch.drop_constraint(_ENDPOINT_FK, type_="foreignkey")
        return

    op.drop_constraint(_JOB_FK, "jobs", type_="foreignkey")
    op.drop_constraint(_ENDPOINT_FK, "custom_endpoints", type_="foreignkey")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("jobs") as batch:
            batch.create_foreign_key(
                _JOB_FK,
                "brand_specs",
                ["brand_spec_id"],
                ["id"],
                ondelete="SET NULL",
            )
        with op.batch_alter_table("custom_endpoints") as batch:
            batch.create_foreign_key(
                _ENDPOINT_FK,
                "brand_specs",
                ["default_brand_spec_id"],
                ["id"],
                ondelete="SET NULL",
            )
        return

    op.create_foreign_key(
        _JOB_FK,
        "jobs",
        "brand_specs",
        ["brand_spec_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        _ENDPOINT_FK,
        "custom_endpoints",
        "brand_specs",
        ["default_brand_spec_id"],
        ["id"],
        ondelete="SET NULL",
    )
