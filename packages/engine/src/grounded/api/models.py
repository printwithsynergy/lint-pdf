"""SQLAlchemy database models for LintPDF API."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime  # noqa: TC003
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from grounded.tenants.models import TenantPlan


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class JobStatus(enum.StrEnum):
    """Job processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class AIBillingMode(enum.StrEnum):
    """AI credit billing mode."""

    PAY_PER_USE = "pay_per_use"
    CREDIT_PACKAGE = "credit_package"


class Tenant(Base):
    """Multi-tenant account."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    plan: Mapped[TenantPlan] = mapped_column(
        Enum(TenantPlan, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=TenantPlan.FREE,
    )
    rate_limit_daily: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_file_size_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    overage_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overage_cap_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overage_rate_override_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_item_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    brand_primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    brand_accent_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    brand_custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_hide_footer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    report_default_expiry_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    report_storage_used_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entitlement_overrides: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    jobs: Mapped[list[Job]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    webhook_endpoints: Mapped[list[WebhookEndpoint]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    ai_config: Mapped[TenantAIConfig | None] = relationship(
        back_populates="tenant", uselist=False, cascade="all, delete-orphan"
    )
    ai_credit_packages: Mapped[list[TenantAICreditPackage]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    ai_usage_logs: Mapped[list[AIUsageLog]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    color_config: Mapped[TenantColorConfig | None] = relationship(
        back_populates="tenant", uselist=False, cascade="all, delete-orphan"
    )


class Job(Base):
    """Preflight job record."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_tenant_created", "tenant_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=JobStatus.PENDING,
    )
    profile_id: Mapped[str] = mapped_column(String(255), nullable=False)
    file_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color_quality_score: Mapped[Any | None] = mapped_column(Numeric(5, 1), nullable=True)

    # Relationships
    tenant: Mapped[Tenant] = relationship(back_populates="jobs")
    findings: Mapped[list[JobFinding]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobFinding(Base):
    """Individual finding from a preflight job."""

    __tablename__ = "job_findings"
    __table_args__ = (Index("ix_job_findings_job_severity", "job_id", "severity"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inspection_id: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    page_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="engine")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    job: Mapped[Job] = relationship(back_populates="findings")


class WebhookEndpoint(Base):
    """Webhook endpoint registration for a tenant."""

    __tablename__ = "webhook_endpoints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    events: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship(back_populates="webhook_endpoints")


class CustomProfile(Base):
    """Custom preflight profile (Voyage Plan) owned by a tenant."""

    __tablename__ = "custom_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_id: Mapped[str] = mapped_column(String(255), nullable=False)
    voyage_plan_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Unique constraint: one profile_id per tenant
    __table_args__ = (
        Index("ix_custom_profiles_tenant_profile", "tenant_id", "profile_id", unique=True),
    )


class ApiKey(Base):
    """API key for tenant programmatic access. Supports multiple keys per tenant."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="Default")
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReportToken(Base):
    """Token-based access to hosted preflight reports."""

    __tablename__ = "report_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accessed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# --- AI Feature Models ---


class TenantAIConfig(Base):
    """AI feature configuration for a tenant (Fleet)."""

    __tablename__ = "tenant_ai_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    billing_mode: Mapped[AIBillingMode] = mapped_column(
        Enum(AIBillingMode, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=AIBillingMode.PAY_PER_USE,
    )
    credit_balance: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    overage_rate: Mapped[Any] = mapped_column(Numeric(8, 4), nullable=False, default=0.10)
    monthly_spending_limit: Mapped[Any | None] = mapped_column(Numeric(10, 2), nullable=True)
    enabled_categories: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    default_ai_features: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    trial_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trial_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Brand configuration for AI checks
    brand_palette: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    reference_logos: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    custom_dictionary: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    industry_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    regulatory_market: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Threshold defaults
    default_safe_zone_mm: Mapped[Any] = mapped_column(Numeric(6, 2), nullable=False, default=3.0)
    default_package_capacity_ml: Mapped[Any | None] = mapped_column(Numeric(10, 2), nullable=True)
    default_package_surface_area_cm2: Mapped[Any | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    min_image_quality_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    delta_e_squall_threshold: Mapped[Any] = mapped_column(
        Numeric(6, 2), nullable=False, default=2.0
    )
    delta_e_aground_threshold: Mapped[Any] = mapped_column(
        Numeric(6, 2), nullable=False, default=5.0
    )
    severity_labels: Mapped[dict[str, str] | None] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: {"aground": "Aground", "squall": "Squall", "advisory": "Advisory"},
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship(back_populates="ai_config")


class TenantAICreditPackage(Base):
    """Prepaid AI credit package for a tenant."""

    __tablename__ = "tenant_ai_credit_packages"
    __table_args__ = (Index("ix_ai_credit_packages_tenant", "tenant_id", "purchased_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    credits_purchased: Mapped[int] = mapped_column(Integer, nullable=False)
    credits_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    price_paid: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant: Mapped[Tenant] = relationship(back_populates="ai_credit_packages")


class AIUsageLog(Base):
    """Log entry for AI feature usage and credit consumption."""

    __tablename__ = "ai_usage_logs"
    __table_args__ = (
        Index("ix_ai_usage_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_ai_usage_logs_job", "job_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    feature: Mapped[str] = mapped_column(String(100), nullable=False)
    credits_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cost: Mapped[Any] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship(back_populates="ai_usage_logs")


# --- Color Management Models ---


class TenantColorConfig(Base):
    """Color management configuration for a tenant."""

    __tablename__ = "tenant_color_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    default_output_condition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    custom_icc_profiles: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    brand_palette: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    custom_dictionary_words: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    default_tac_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=320)
    default_safe_zone_margin_mm: Mapped[Any] = mapped_column(
        Numeric(6, 2), nullable=False, default=3.0
    )
    package_capacity_default: Mapped[str | None] = mapped_column(String(50), nullable=True)
    package_surface_area_default: Mapped[Any | None] = mapped_column(Numeric(10, 2), nullable=True)
    target_market: Mapped[str | None] = mapped_column(String(50), nullable=True)
    epm_mode_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship(back_populates="color_config")


class UserAIAccess(Base):
    """Per-user AI feature access control."""

    __tablename__ = "user_ai_access"
    __table_args__ = (Index("ix_user_ai_access_user_tenant", "user_id", "tenant_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    personal_spending_limit: Mapped[Any | None] = mapped_column(Numeric(10, 2), nullable=True)
    trial_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trial_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
