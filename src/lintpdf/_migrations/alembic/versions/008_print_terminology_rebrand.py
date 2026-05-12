"""Rebrand nautical terminology to standard print terms + add JDF support.

Revision ID: 008_print_terminology_rebrand
Revises: 007_add_color_models
Create Date: 2026-03-23

Renames:
- custom_profiles.voyage_plan_json -> preflight_profile_json
- tenant_ai_configs.delta_e_aground_threshold -> delta_e_error_threshold
- tenant_ai_configs.delta_e_squall_threshold -> delta_e_warning_threshold
- job_findings severity values: aground -> error, squall -> warning
- tenant_ai_configs.severity_labels defaults updated
- jobs.jdf_overrides column added for JDF sidecar support
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "008_print_terminology_rebrand"
down_revision = "007_add_color_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Column renames ---
    op.alter_column(
        "custom_profiles",
        "voyage_plan_json",
        new_column_name="preflight_profile_json",
    )
    op.alter_column(
        "tenant_ai_configs",
        "delta_e_aground_threshold",
        new_column_name="delta_e_error_threshold",
    )
    op.alter_column(
        "tenant_ai_configs",
        "delta_e_squall_threshold",
        new_column_name="delta_e_warning_threshold",
    )

    # --- Severity value updates ---
    op.execute("UPDATE job_findings SET severity = 'error' WHERE severity = 'aground'")
    op.execute("UPDATE job_findings SET severity = 'warning' WHERE severity = 'squall'")

    # --- Update severity_labels defaults ---
    op.execute(
        "UPDATE tenant_ai_configs SET severity_labels = "
        '\'{"error": "Error", "warning": "Warning", "advisory": "Advisory"}\' '
        "WHERE severity_labels = "
        '\'{"aground": "Aground", "squall": "Squall", "advisory": "Advisory"}\''
    )

    # --- Add JDF overrides column ---
    op.add_column(
        "jobs",
        sa.Column("jdf_overrides", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    # --- Remove JDF overrides column ---
    op.drop_column("jobs", "jdf_overrides")

    # --- Revert severity_labels defaults ---
    op.execute(
        "UPDATE tenant_ai_configs SET severity_labels = "
        '\'{"aground": "Aground", "squall": "Squall", "advisory": "Advisory"}\' '
        "WHERE severity_labels = "
        '\'{"error": "Error", "warning": "Warning", "advisory": "Advisory"}\''
    )

    # --- Revert severity values ---
    op.execute("UPDATE job_findings SET severity = 'aground' WHERE severity = 'error'")
    op.execute("UPDATE job_findings SET severity = 'squall' WHERE severity = 'warning'")

    # --- Revert column renames ---
    op.alter_column(
        "tenant_ai_configs",
        "delta_e_warning_threshold",
        new_column_name="delta_e_squall_threshold",
    )
    op.alter_column(
        "tenant_ai_configs",
        "delta_e_error_threshold",
        new_column_name="delta_e_aground_threshold",
    )
    op.alter_column(
        "custom_profiles",
        "preflight_profile_json",
        new_column_name="voyage_plan_json",
    )
