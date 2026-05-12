"""Phase 0.7 PR-B4-final — drop the four fully-migrated legacy tables.

End of the unified-config collapse for the per-tenant config layers.
``custom_profiles``, ``brand_specs``, ``approval_chain_templates``,
and ``tenant_import_mappings`` are no longer read or written by any
engine code path; their data was folded into the unified
``ToggleOverride`` substrate by v13 and every consumer has been
rewired (PR-B3a/b/c/e + PR-B4-final). This migration does the actual
``DROP TABLE`` per Q-W3 ("drop in same alembic transaction").

``custom_endpoints`` is intentionally NOT dropped here — endpoints.py
still maintains it. A follow-up PR replaces endpoints.py with a
Workflow-backed router and drops ``custom_endpoints`` then.

Also drops ``ApprovalChain.template_id`` foreign-key constraint
(target table is going away). The ``template_id`` column itself
stays so historical chains keep their template reference for audit.

Revision ID: 046
Revises: 045
Create Date: 2026-04-26
"""

from __future__ import annotations

from alembic import op

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


_APPROVAL_CHAIN_TEMPLATE_FK = "approval_chains_template_id_fkey"


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # ── Drop FK from approval_chains.template_id → approval_chain_templates.id ──
    if is_sqlite:
        with op.batch_alter_table("approval_chains") as batch:
            batch.drop_constraint(_APPROVAL_CHAIN_TEMPLATE_FK, type_="foreignkey")
    else:
        op.drop_constraint(_APPROVAL_CHAIN_TEMPLATE_FK, "approval_chains", type_="foreignkey")

    # ── Drop the four legacy tenant-config tables ──
    # Order matters only insofar as no remaining FK references them;
    # the only inbound FKs (jobs.brand_spec_id + custom_endpoints
    # .default_brand_spec_id) were dropped in alembic 045.
    op.drop_table("custom_profiles")
    op.drop_table("brand_specs")
    op.drop_table("approval_chain_templates")
    op.drop_table("tenant_import_mappings")


def downgrade() -> None:
    raise RuntimeError(
        "046_drop_legacy_tenant_config_tables: irreversible. The data lives in"
        " ToggleOverride rows now; restore from a Railway volume snapshot if"
        " a rollback is required."
    )
