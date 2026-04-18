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
    Float,
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

from lintpdf.tenants.models import TenantPlan


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class BrandProfileType(enum.StrEnum):
    """Brand profile type."""

    CUSTOM = "custom"
    LINTPDF = "lintpdf"
    NONE = "none"


class JobStatus(enum.StrEnum):
    """Job processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class PreflightSource(enum.StrEnum):
    """How preflight findings are obtained for a job.

    - ``engine``: run the LintPDF preflight pipeline (default).
    - ``external``: ingest findings from an uploaded third-party preflight
      report (PitStop, callas, Acrobat, or the LintPDF native JSON schema).
    - ``minimal``: skip all analyzers and only extract viewer essentials
      (page count, geometry, document metadata). Viewer tools that require
      findings or richer data can be filled in on-demand.
    """

    ENGINE = "engine"
    EXTERNAL = "external"
    MINIMAL = "minimal"


# Tool → capability mapping. Viewer tools read this to decide whether to
# render as active, show a "Load" affordance, or hide completely. Entries
# here must match keys in ``Job.data_capabilities`` JSONB.
CAPABILITY_KEYS: tuple[str, ...] = (
    "findings",  # job findings populated (engine or imported)
    "separations",  # spot color / ink separation data extracted
    "tac",  # total area coverage / ink coverage data extracted
    "layers",  # OCG / optional content layer data extracted
    "fonts",  # font analysis available
    "images",  # image analysis available
    "thumbnails",  # page thumbnail tiles rendered
    "metadata",  # document metadata extracted
)


def default_capabilities(all_true: bool = True) -> dict[str, bool]:
    """Build a full capabilities map. Default true matches engine preflight."""
    return {key: all_true for key in CAPABILITY_KEYS}


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
    # Per-tenant metered-resource overrides. NULL = inherit plan default
    # from PLAN_LIMITS; integer = use this value regardless of plan. Lets
    # ops grant a VIP Growth customer Enterprise-level monthly credits
    # without upselling them the whole plan.
    monthly_ai_credits_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_files_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_item_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    brand_primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    brand_accent_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    brand_custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_custom_domain_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    brand_custom_domain_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    app_custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    app_custom_domain_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    app_custom_domain_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    brand_hide_footer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    report_default_expiry_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    report_summary_page: Mapped[str] = mapped_column(String(10), nullable=False, default="prepend")
    # Gate public share-link viewers behind an email capture prompt. Default
    # ``True`` for brokers / print shops who need lead-gen on every shared
    # report; admins can flip it to ``False`` for tenants that only share
    # internally (the LintPDF Production tenant itself, for example). The
    # token validation endpoint previously hard-coded ``email_required=True``
    # here regardless of tenant settings, which broke trusted-share workflows.
    share_email_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    report_storage_used_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    default_brand_profile_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # Default output branding — when true, viewer config + reports default to
    # the ``none`` brand profile type (stripped LintPDF branding). Per-request
    # override still applies via ``brand`` query param or ``brand_profile_id``
    # on submission.
    unbranded_by_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
    brand_profiles: Mapped[list[BrandProfile]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
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
    jdf_overrides: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Universal per-call override envelope (see ``lintpdf.overrides``).
    # The resolved envelope is persisted here at submit time so the
    # orchestrator and viewer config endpoints can read it back later
    # without re-parsing the request. JDF overrides continue to live in
    # ``jdf_overrides`` above (they're a specialised subset of thresholds
    # + conformance, fed by the JDF parser) and are merged on top.
    overrides: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Verdict (manual review disposition)
    verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verdict_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verdict_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verdict_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # How findings were produced for this job. Drives the Celery pipeline
    # branch and the viewer's capability-aware rendering.
    preflight_source: Mapped[PreflightSource] = mapped_column(
        Enum(PreflightSource, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=PreflightSource.ENGINE,
        server_default=PreflightSource.ENGINE.value,
    )
    # Format of the imported preflight report when ``preflight_source == EXTERNAL``.
    # One of: ``pitstop_xml``, ``callas_json``, ``callas_xml``, ``acrobat_xml``,
    # ``lintpdf_json`` (populated by the import parser on success).
    external_format: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Per-capability availability flags. Viewer tools read this to decide
    # whether to render, hide, or offer a one-click fill-in.
    data_capabilities: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # Per-job brand override — if set, wins over tenant default.
    brand_profile_id_override: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # Per-job unbranded override (request-level flag, orthogonal to
    # ``brand_profile_id_override``). ``True`` forces rendering with the
    # ``none`` brand profile type even if a branded profile is otherwise
    # resolved.
    unbranded_override: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship(back_populates="jobs")
    findings: Mapped[list[JobFinding]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    imported_reports: Mapped[list[JobImportedReport]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobImportedReport(Base):
    """Raw third-party preflight report uploaded alongside a PDF.

    Keeping the raw artifact lets us re-parse or audit the import without
    re-uploading, and supports future parser improvements.
    """

    __tablename__ = "job_imported_reports"
    __table_args__ = (Index("ix_job_imported_reports_job", "job_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_blob_key: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    job: Mapped[Job] = relationship(back_populates="imported_reports")


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
    bbox_x0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y0: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_x1: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[float | None] = mapped_column(Float, nullable=True)
    object_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    object_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

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


class WebhookDelivery(Base):
    """Audit row for one webhook delivery attempt.

    Every time the engine dispatches an event to a ``WebhookEndpoint``,
    a row is written here before the first attempt and updated with the
    final status after retries. The row persists the exact payload we
    signed so operators can replay a failed delivery verbatim via
    ``POST /api/v1/webhooks/deliveries/{id}/replay``. Without this
    table the previous behaviour was fire-and-forget: a 5xx on the
    caller's endpoint meant the event was lost with only the engine
    log as trail.
    """

    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_deliveries_endpoint_created", "webhook_id", "created_at"),
        Index("ix_webhook_deliveries_tenant_created", "tenant_id", "created_at"),
        Index("ix_webhook_deliveries_event_created", "event", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("webhook_endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    # Full JSON body we POSTed -- stored verbatim so replay re-sends the
    # exact same signed bytes. ``sort_keys=True`` in the dispatcher keeps
    # the serialisation stable.
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    # URL at time of dispatch (persisted even if endpoint later changes URL).
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    # Number of HTTP attempts made (1 = first try + 0 retries, up to max_retries+1).
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Final HTTP status code from the caller, or 0 if no response was
    # received (DNS / connection / timeout failures).
    final_status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # True iff the final attempt returned a 2xx / 3xx. False for 4xx, 5xx,
    # or network failure.
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Last error string (HTTP status text, exception message, etc).
    # Capped by the column length; full details stay in engine logs.
    last_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CustomProfile(Base):
    """Custom preflight profile owned by a tenant."""

    __tablename__ = "custom_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_id: Mapped[str] = mapped_column(String(255), nullable=False)
    preflight_profile_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
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


class CustomEndpoint(Base):
    """Custom API endpoint bound to a specific profile for simplified job submission."""

    __tablename__ = "custom_endpoints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_id: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Unique constraint: one slug per tenant
    __table_args__ = (Index("ix_custom_endpoints_tenant_slug", "tenant_id", "slug", unique=True),)

    # Relationships
    tenant: Mapped[Tenant] = relationship()


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
    # VARCHAR(32) fits every current format name with headroom for
    # future additions. The original VARCHAR(10) was fine for the
    # initial ``html / pdf / json / xml`` set but silently broke the
    # mint endpoint as soon as ``annotated_pdf`` (13 chars) and
    # ``annotated_pdf_markup`` (20 chars) came online — Postgres
    # rejected the INSERT with ``StringDataRightTruncation`` and the
    # whole ``POST /api/v1/jobs/{id}/reports`` request 500'd. Widened
    # via Alembic 023 + startup.sh ALTER TABLE.
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accessed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Branding captured at mint time so downstream viewers/share pages see
    # the exact branding the minter chose, even if the tenant later flips
    # defaults. ``brand_mode`` is one of ``anonymous`` / ``lintpdf`` /
    # ``profile``; the latter pairs with ``brand_profile_id``.
    brand_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    brand_profile_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # Permission for anonymous reviewers to create annotations on the
    # token-scoped public viewer. False = viewer-only (default). True means
    # anyone with the token can POST annotations as long as they provide an
    # email identity (captured via X-Visitor-Email header).
    allow_annotations: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    # Per-token override for the email-capture gate at ``/view/{token}``.
    # ``NULL`` → inherit the tenant's ``share_email_required`` setting;
    # ``True`` → force the gate on regardless of tenant;
    # ``False`` → force the gate off regardless of tenant.
    # Persisting per-token means a single tenant can mint "gated" tokens
    # for external distribution *and* "ungated" tokens for internal review
    # in the same session, without flipping a tenant-wide flag between calls.
    require_visitor_email: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Universal per-call override envelope captured at mint time (see
    # ``lintpdf.overrides``). The viewer config endpoint reads this dict
    # to apply per-token viewer flags (hide separations, force dark
    # mode, override footer text, etc.) so each share link carries its
    # own immutable behaviour — you can share the same job via three
    # tokens with three different override sets.
    overrides: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


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
    delta_e_warning_threshold: Mapped[Any] = mapped_column(
        Numeric(6, 2), nullable=False, default=2.0
    )
    delta_e_error_threshold: Mapped[Any] = mapped_column(Numeric(6, 2), nullable=False, default=5.0)
    severity_labels: Mapped[dict[str, str] | None] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: {"error": "Error", "warning": "Warning", "advisory": "Advisory"},
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
    """Prepaid metered-resource package (AI credits or file quota).

    Despite the legacy ``tenant_ai_credit_packages`` table name, this
    table holds both kinds of packs — the ``kind`` discriminator column
    selects between them. See ``packages/engine/src/lintpdf/billing/
    metered_packs.py`` for the pack catalogue.

    Sources:
      - ``plan_monthly`` — granted on invoice.paid, expires on next cycle
      - ``purchase`` — tenant bought via Stripe Checkout
      - ``admin_grant`` — ops bypass via the admin API
      - ``trial`` — trial allocation from the AI-trial endpoint
    """

    __tablename__ = "tenant_ai_credit_packages"
    __table_args__ = (
        Index("ix_ai_credit_packages_tenant", "tenant_id", "purchased_at"),
        Index("ix_ai_credit_packages_tenant_kind", "tenant_id", "kind"),
        Index(
            "ix_ai_credit_packages_stripe_session",
            "stripe_session_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Which metered resource this pack funds. 'credits' preserves
    # pre-refactor behavior for existing rows (default).
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default="credits", server_default="credits"
    )
    # Origin of the package — see docstring for the enum values.
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="admin_grant", server_default="admin_grant"
    )
    credits_purchased: Mapped[int] = mapped_column(Integer, nullable=False)
    credits_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    price_paid: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    # Stripe checkout session id when source='purchase'. Unique to
    # enforce webhook idempotency.
    stripe_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # For source='plan_monthly': the start of the billing period this
    # allotment is for. Used to dedupe allocations so a replayed
    # invoice.paid webhook never double-grants.
    billing_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
    custom_pantone_overrides: Mapped[dict[str, dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True, comment="Customer Pantone color overrides keyed by normalized name"
    )
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


# --- Trial Submission Models ---


class TrialSubmissionStatus(enum.StrEnum):
    """Trial submission processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    CONTACTED = "contacted"


class TrialSubmission(Base):
    """Public trial upload submission from a prospect."""

    __tablename__ = "trial_submissions"
    __table_args__ = (
        Index("ix_trial_submissions_email", "email"),
        Index("ix_trial_submissions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[TrialSubmissionStatus] = mapped_column(
        Enum(TrialSubmissionStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=TrialSubmissionStatus.PENDING,
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    files: Mapped[list[TrialFile]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class TrialFile(Base):
    """Individual file within a trial submission."""

    __tablename__ = "trial_files"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("trial_submissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_key: Mapped[str] = mapped_column(String(512), nullable=False)
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    scan_clean: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    submission: Mapped[TrialSubmission] = relationship(back_populates="files")
    job: Mapped[Job | None] = relationship()


# --- Brand Profile Models ---


class BrandProfile(Base):
    """Named brand profile for report branding."""

    __tablename__ = "brand_profiles"
    __table_args__ = (Index("ix_brand_profiles_tenant", "tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_type: Mapped[BrandProfileType] = mapped_column(
        Enum(BrandProfileType, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=BrandProfileType.CUSTOM,
    )
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    accent_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    footer_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hide_footer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custom_domain_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    custom_domain_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    app_custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    app_custom_domain_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    app_custom_domain_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    viewer_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship(back_populates="brand_profiles")


# --- Approval Chain Models ---


class ApprovalChainTemplate(Base):
    """Reusable multi-step approval chain preset for a tenant."""

    __tablename__ = "approval_chain_templates"
    __table_args__ = (Index("ix_approval_templates_tenant", "tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ApprovalChain(Base):
    """An instance of an approval chain attached to a specific job."""

    __tablename__ = "approval_chains"
    __table_args__ = (
        Index("ix_approval_chains_tenant_status", "tenant_id", "status"),
        Index("ix_approval_chains_job", "job_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("approval_chain_templates.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantImportMapping(Base):
    """Tenant-defined mapping that turns a proprietary preflight report into
    engine findings.

    Teams running in-house or niche preflight tools don't fit the built-in
    PitStop / callas / Acrobat / LintPDF-native parsers. Rather than ask us
    to ship a new parser for every vendor, tenants define a **mapping**: a
    small config that says "in my XML/JSON, each finding lives at this path;
    the severity comes from this sub-selector; the message lives here; …"

    The mapping's ``config`` column is a JSON document with this shape::

        {
          "format": "xml" | "json",
          "item_selector": "//finding" | "results[*].issues[*]",
          "fields": {
            "severity":   {"selector": "@level",        "required": false},
            "message":    {"selector": "description",   "required": true},
            "page":       {"selector": "@page"},
            "check_id":   {"selector": "@id"},
            "bbox":       {"selector": "geom/bbox"},
            "object_id":  {"selector": "@objRef"},
            "object_type":{"selector": "@objKind"},
            "category":   {"selector": "category"},
            "iso_clause": {"selector": "@iso"}
          },
          "severity_map": {"fatal": "error", "info": "advisory", "high": "error"},
          "default_severity": "warning"
        }

    ``sample_payload`` is the tenant's uploaded example — persisted so the
    UI can round-trip a preview and so we can re-validate the mapping if
    the tenant later reports a regression.
    """

    __tablename__ = "tenant_import_mappings"
    __table_args__ = (Index("ix_tenant_import_mappings_tenant", "tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[str] = mapped_column(String(8), nullable=False, default="xml")
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    sample_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_mime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ApprovalStep(Base):
    """Individual step decision on an approval chain."""

    __tablename__ = "approval_steps"
    __table_args__ = (
        Index("ix_approval_steps_chain", "chain_id", "step_index"),
        Index("ix_approval_steps_token", "access_token", unique=True),
        Index("ix_approval_steps_pending_expiry", "decision", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    chain_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("approval_chains.id", ondelete="CASCADE"), nullable=False
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    approver_email: Mapped[str] = mapped_column(String(255), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ViewerAnnotation(Base):
    """Reviewer-drawn markup on a preflight viewer page.

    Supports five geometry kinds (``rect``, ``circle``, ``arrow``,
    ``freehand``, ``note``). Coordinates are stored in PDF points with
    the origin at the page's lower-left corner so annotations remain
    valid regardless of viewer zoom or rendering DPI.

    Public share-link writers are identified by ``author_email`` (captured
    via the viewer's email gate); authenticated dashboard writers carry
    the tenant user's email via the auth session.
    """

    __tablename__ = "viewer_annotations"
    __table_args__ = (
        Index("ix_viewer_annotations_job_page", "job_id", "page_num"),
        Index("ix_viewer_annotations_token", "share_token"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    # Optional link to a share-link token. Populated only for annotations
    # created via the public /view/{token} surface; NULL for dashboard
    # writers. Lets a share reader see only annotations made through the
    # same link (future work) while the authenticated dashboard still
    # sees everything for the job.
    share_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    page_num: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # Serialised primitive (points list or rect corners). Schema is
    # intentionally free-form so the client can evolve geometry types
    # without a migration: callers read/write the same JSON blob.
    geometry_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#dc2626")
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_email: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ViewerAnnotationComment(Base):
    """Thread of follow-up comments on a :class:`ViewerAnnotation`.

    Wave B collaboration: reviewers and share-link visitors can reply
    to a note, building a conversation thread without cluttering the
    page with additional markup primitives. The author's email is
    captured the same way as on the parent annotation (tenant user for
    dashboard writers, ``X-Visitor-Email`` for share-link visitors).
    """

    __tablename__ = "viewer_annotation_comments"
    __table_args__ = (
        Index("ix_viewer_ann_comments_annotation", "annotation_id", "created_at"),
        Index("ix_viewer_ann_comments_token", "share_token"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    annotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("viewer_annotations.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    # Mirrors the parent annotation's share_token (NULL for dashboard
    # comments). Kept denormalised so the public-share mirror routes can
    # filter without joining through viewer_annotations.
    share_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_email: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ShareLinkVisitor(Base):
    """Email + IP capture for anonymous annotators on /view/{token} share links.

    Anonymous viewers with the "allow_annotations" flag set on their
    ReportToken must identify themselves with an email (via the
    X-Visitor-Email header) before they can create annotations. Each
    first-time identification inserts a row here so we have an audit
    trail of who wrote what.
    """

    __tablename__ = "share_link_visitors"
    __table_args__ = (Index("ix_share_visitors_token_email", "share_token", "visitor_email"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    share_token: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    visitor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
