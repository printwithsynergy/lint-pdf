"""ai_features + ai_usage_logs + rescale monthly_ai_credits to cents.

WS-F + WS-G schema. Replaces the per-tenant ``ai_audit_enabled``
boolean with a ``ai_features`` JSONB list, rescales existing
``monthly_ai_credits*`` columns from whole dollars to integer
cents, and stands up ``ai_usage_logs`` for per-call metering.

Intentional deviations from the plan text:

* ``plan_limit_overrides`` keeps its generic ``overrides`` JSON
  blob (callers just nest ``ai_features`` inside it). Adding a
  dedicated column would be redundant and require a schema
  migration on every plan-tier overrides update.
* Feature-name validation lives at the admin PATCH schema layer
  (``EntitlementOverridesPatch._ai_features_are_known``), not in
  Postgres. A stray flag never lands via admin writes but this
  migration tolerates whatever's already in ``entitlement_overrides``.

Revision ID: 037
Revises: 036
Create Date: 2026-04-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ai_features on tenants ────────────────────────────────────
    op.add_column(
        "tenants",
        sa.Column(
            "ai_features",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )

    # Extend the pre-existing ai_usage_logs table with the WS-G
    # per-Claude-call columns. ``cost_cents`` is the integer-cent
    # cost computed by ``lintpdf.audit.metering.record_usage``;
    # sub-cent calls round UP to 1. All nullable to stay compatible
    # with pre-037 rows that only logged (credits_consumed, cost).
    op.add_column(
        "ai_usage_logs", sa.Column("model", sa.String(64), nullable=True)
    )
    op.add_column(
        "ai_usage_logs", sa.Column("input_tokens", sa.Integer, nullable=True)
    )
    op.add_column(
        "ai_usage_logs", sa.Column("output_tokens", sa.Integer, nullable=True)
    )
    op.add_column(
        "ai_usage_logs", sa.Column("cache_read_tokens", sa.Integer, nullable=True)
    )
    op.add_column(
        "ai_usage_logs", sa.Column("cache_write_tokens", sa.Integer, nullable=True)
    )
    op.add_column(
        "ai_usage_logs", sa.Column("cost_cents", sa.Integer, nullable=True)
    )
    op.create_index(
        "ix_ai_usage_logs_tenant_month",
        "ai_usage_logs",
        ["tenant_id", sa.text("date_trunc('month', created_at)")],
    )

    # Rescale existing monthly_ai_credits from whole dollars to cents.
    # Column type stays int — only the UNIT changes. Every $5 becomes 500.
    op.execute(
        """
        UPDATE tenants
           SET monthly_ai_credits_override =
               COALESCE(monthly_ai_credits_override, 0) * 100
         WHERE monthly_ai_credits_override IS NOT NULL
           AND monthly_ai_credits_override > 0
        """
    )
    op.execute(
        "COMMENT ON COLUMN tenants.monthly_ai_credits_override IS "
        "'Monthly AI credit cap in INTEGER CENTS (500 = $5.00). "
        "NULL = inherit plan default.'"
    )

    # Copy the dead ai_audit_enabled bool → ai_features=["audit"].
    # entitlement_overrides is JSON; read via ->> cast.
    op.execute(
        """
        UPDATE tenants
           SET ai_features = '["audit"]'::jsonb
         WHERE (entitlement_overrides->>'ai_audit_enabled')::bool = true
        """
    )
    # Drop the dead key from the JSON blob so the resolver never
    # sees it again.
    op.execute(
        """
        UPDATE tenants
           SET entitlement_overrides = entitlement_overrides - 'ai_audit_enabled'
         WHERE entitlement_overrides ? 'ai_audit_enabled'
        """
    )
    # Mirror the clean-up on plan-tier overrides — any row that
    # carried ``ai_audit_enabled`` gets ``ai_features=["audit"]``
    # folded into its ``overrides`` JSON and the dead key stripped.
    op.execute(
        """
        UPDATE plan_limit_overrides
           SET overrides = jsonb_set(
                   (overrides::jsonb - 'ai_audit_enabled'),
                   '{ai_features}',
                   '["audit"]'::jsonb,
                   true
               )
         WHERE (overrides::jsonb->>'ai_audit_enabled')::bool = true
        """
    )


def downgrade() -> None:
    op.drop_index("ix_ai_usage_logs_tenant_month", table_name="ai_usage_logs")
    op.drop_column("ai_usage_logs", "cost_cents")
    op.drop_column("ai_usage_logs", "cache_write_tokens")
    op.drop_column("ai_usage_logs", "cache_read_tokens")
    op.drop_column("ai_usage_logs", "output_tokens")
    op.drop_column("ai_usage_logs", "input_tokens")
    op.drop_column("ai_usage_logs", "model")
    op.drop_column("tenants", "ai_features")
    # Rescale back to whole dollars.
    op.execute(
        """
        UPDATE tenants
           SET monthly_ai_credits_override = monthly_ai_credits_override / 100
         WHERE monthly_ai_credits_override IS NOT NULL
        """
    )
