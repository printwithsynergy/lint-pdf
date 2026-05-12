"""Nautical rebrand: rename columns and update severity values.

Revision ID: 006_nautical_rebrand
Revises: 005
Create Date: 2026-03-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006_nautical_rebrand"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename flight_plan_json -> voyage_plan_json in custom_profiles
    op.alter_column(
        "custom_profiles",
        "flight_plan_json",
        new_column_name="voyage_plan_json",
    )

    # Rename delta_e_no_fly_threshold -> delta_e_aground_threshold in tenant_ai_configs
    op.alter_column(
        "tenant_ai_configs",
        "delta_e_no_fly_threshold",
        new_column_name="delta_e_aground_threshold",
    )

    # Rename delta_e_delay_threshold -> delta_e_squall_threshold in tenant_ai_configs
    op.alter_column(
        "tenant_ai_configs",
        "delta_e_delay_threshold",
        new_column_name="delta_e_squall_threshold",
    )

    # Update severity values in job_findings: "no-fly" -> "aground", "delay" -> "squall"
    op.execute(sa.text("UPDATE job_findings SET severity = 'aground' WHERE severity = 'no-fly'"))
    op.execute(sa.text("UPDATE job_findings SET severity = 'squall' WHERE severity = 'delay'"))

    # Add severity_labels JSON column to tenant_ai_configs
    op.add_column(
        "tenant_ai_configs",
        sa.Column(
            "severity_labels",
            sa.JSON(),
            nullable=True,
            server_default=sa.text(
                """'{"aground": "Aground", "squall": "Squall", "advisory": "Advisory"}'"""
            ),
        ),
    )


def downgrade() -> None:
    # Remove severity_labels column
    op.drop_column("tenant_ai_configs", "severity_labels")

    # Revert severity values in job_findings: "aground" -> "no-fly", "squall" -> "delay"
    op.execute(sa.text("UPDATE job_findings SET severity = 'no-fly' WHERE severity = 'aground'"))
    op.execute(sa.text("UPDATE job_findings SET severity = 'delay' WHERE severity = 'squall'"))

    # Rename delta_e_squall_threshold -> delta_e_delay_threshold in tenant_ai_configs
    op.alter_column(
        "tenant_ai_configs",
        "delta_e_squall_threshold",
        new_column_name="delta_e_delay_threshold",
    )

    # Rename delta_e_aground_threshold -> delta_e_no_fly_threshold in tenant_ai_configs
    op.alter_column(
        "tenant_ai_configs",
        "delta_e_aground_threshold",
        new_column_name="delta_e_no_fly_threshold",
    )

    # Rename voyage_plan_json -> flight_plan_json in custom_profiles
    op.alter_column(
        "custom_profiles",
        "voyage_plan_json",
        new_column_name="flight_plan_json",
    )
