"""System-wide preflight profiles (DB-backed) + tenant default override.

Moves built-in preflight profiles out of the hard-coded
``ProfileRegistry`` bundled JSON into a runtime-editable
``system_profiles`` table, and adds ``tenants.default_profile_id`` for
the per-tenant "soft default" flow.

Seed of ``system_profiles`` from the bundled JSON happens lazily at app
boot (see ``lintpdf.profiles.seed.seed_system_profiles_from_bundled``)
using insert-if-absent semantics, so a modified bundled JSON for an
existing ``profile_id`` is silently ignored — once a row exists in the
DB it's authoritative. New ``profile_id``s added in the bundled
directory get picked up automatically because no row exists yet.

Revision ID: 036
Revises: 035
Create Date: 2026-04-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── system_profiles ─────────────────────────────────────────
    op.create_table(
        "system_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("profile_id", sa.String(length=255), nullable=False),
        sa.Column(
            "preflight_profile_json",
            postgresql.JSONB,
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default="bundled",
        ),
        sa.Column("bundled_version", sa.String(length=32), nullable=True),
        sa.Column(
            "visibility_mode",
            sa.String(length=32),
            nullable=False,
            server_default="all",
        ),
        sa.Column("min_plan", sa.String(length=32), nullable=True),
        sa.Column(
            "visible_tenant_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.Column("created_by_admin_id", sa.String(length=255), nullable=True),
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
    op.create_unique_constraint(
        "uq_system_profiles_profile_id",
        "system_profiles",
        ["profile_id"],
    )

    # Range check on ``source`` — only ``bundled`` (seeded from
    # committed JSON, never PATCHed) and ``admin`` (authored or edited
    # through the admin UI) are valid. A CHECK rather than a native
    # enum keeps future value additions a one-liner.
    op.create_check_constraint(
        "ck_system_profiles_source",
        "system_profiles",
        "source IN ('bundled', 'admin')",
    )

    # ``visibility_mode`` — ``all`` means every tenant sees it;
    # ``plan`` gates by ``min_plan`` (tenant.plan >= min_plan via the
    # plan hierarchy resolver); ``tenants`` gates by allowlist in
    # ``visible_tenant_ids``; ``plan_and_tenants`` requires both.
    op.create_check_constraint(
        "ck_system_profiles_visibility_mode",
        "system_profiles",
        "visibility_mode IN ('all', 'plan', 'tenants', 'plan_and_tenants')",
    )

    # ── tenants.default_profile_id ──────────────────────────────
    # No FK to system_profiles.profile_id — tenant defaults can point
    # at either a system or a custom profile, and custom lives in a
    # different table keyed on ``(tenant_id, profile_id)``. Validation
    # happens at the admin route that sets the default.
    op.add_column(
        "tenants",
        sa.Column("default_profile_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "default_profile_id")
    op.drop_constraint("ck_system_profiles_visibility_mode", "system_profiles", type_="check")
    op.drop_constraint("ck_system_profiles_source", "system_profiles", type_="check")
    op.drop_constraint("uq_system_profiles_profile_id", "system_profiles", type_="unique")
    op.drop_table("system_profiles")
