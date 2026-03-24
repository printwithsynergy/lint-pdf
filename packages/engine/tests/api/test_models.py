"""Tests for SQLAlchemy database models."""

from __future__ import annotations

from lintpdf.api.models import (
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
    @staticmethod
    def test_tenant_plan_values() -> None:
        assert TenantPlan.FREE.value == "free"
        assert TenantPlan.STARTER.value == "starter"
        assert TenantPlan.GROWTH.value == "growth"
        assert TenantPlan.SCALE.value == "scale"
        assert TenantPlan.ENTERPRISE.value == "enterprise"

    @staticmethod
    def test_job_status_values() -> None:
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.PROCESSING.value == "processing"
        assert JobStatus.COMPLETE.value == "complete"
        assert JobStatus.FAILED.value == "failed"

    @staticmethod
    def test_tenant_table_name() -> None:
        assert Tenant.__tablename__ == "tenants"

    @staticmethod
    def test_job_table_name() -> None:
        assert Job.__tablename__ == "jobs"

    @staticmethod
    def test_job_finding_table_name() -> None:
        assert JobFinding.__tablename__ == "job_findings"

    @staticmethod
    def test_webhook_table_name() -> None:
        assert WebhookEndpoint.__tablename__ == "webhook_endpoints"

    @staticmethod
    def test_custom_profile_table_name() -> None:
        assert CustomProfile.__tablename__ == "custom_profiles"

    @staticmethod
    def test_base_metadata_has_all_tables() -> None:
        table_names = set(Base.metadata.tables.keys())
        expected = {"tenants", "jobs", "job_findings", "webhook_endpoints", "custom_profiles"}
        assert expected.issubset(table_names)
