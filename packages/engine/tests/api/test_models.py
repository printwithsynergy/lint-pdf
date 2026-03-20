"""Tests for SQLAlchemy database models."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.api.models import (
    Base,
    CustomProfile,
    Job,
    JobFinding,
    JobStatus,
    Tenant,
    TenantPlan,
    WebhookEndpoint,
)


class TestModelDefinitions:
    def test_tenant_plan_values(self) -> None:
        assert TenantPlan.FREE.value == "free"
        assert TenantPlan.STARTER.value == "starter"
        assert TenantPlan.GROWTH.value == "growth"
        assert TenantPlan.SCALE.value == "scale"
        assert TenantPlan.ENTERPRISE.value == "enterprise"

    def test_job_status_values(self) -> None:
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.PROCESSING.value == "processing"
        assert JobStatus.COMPLETE.value == "complete"
        assert JobStatus.FAILED.value == "failed"

    def test_tenant_table_name(self) -> None:
        assert Tenant.__tablename__ == "tenants"

    def test_job_table_name(self) -> None:
        assert Job.__tablename__ == "jobs"

    def test_job_finding_table_name(self) -> None:
        assert JobFinding.__tablename__ == "job_findings"

    def test_webhook_table_name(self) -> None:
        assert WebhookEndpoint.__tablename__ == "webhook_endpoints"

    def test_custom_profile_table_name(self) -> None:
        assert CustomProfile.__tablename__ == "custom_profiles"

    def test_base_metadata_has_all_tables(self) -> None:
        table_names = set(Base.metadata.tables.keys())
        expected = {"tenants", "jobs", "job_findings", "webhook_endpoints", "custom_profiles"}
        assert expected.issubset(table_names)
