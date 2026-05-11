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
from sqlalchemy import JSON as SA_JSON
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from lintpdf.tenants.models import TenantPlan

# PG_ARRAY only compiles under the Postgres dialect — SQLite (used by
# the unit-test fixtures) raises CompileError. Fall back to JSON there.
# ``with_variant`` keeps the Postgres-side behaviour identical while
# giving the SQLite test harness a column shape it can render.
_PG_UUID_ARRAY = PG_ARRAY(Uuid).with_variant(SA_JSON(), "sqlite")


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


# AIBillingMode was extracted to lintpdf_saas.api.models in W6c-2r
# (PR thinkneverland/lint-pdf#436 + thinkneverland/lint-pdf-saas#31).


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
    # Wave V V-06 (Q-D3) — default HMAC-SHA256 signing secret used for
    # any of this tenant's ``webhook_endpoints`` whose own ``secret`` is
    # NULL. Per-webhook override wins; this is the fallback before the
    # dispatcher raises. Leave NULL to require every endpoint to carry
    # its own secret.
    webhook_signing_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    # Soft-default preflight profile — used when a job is submitted
    # without an explicit ``profile_id``. Set by site-admins via
    # ``PATCH /api/v1/admin/tenants/{id}/default-profile``. NULL falls
    # back to the hardcoded ``lintpdf-default``. No FK — can reference
    # either a system profile or one of this tenant's custom profiles
    # (validation happens at the admin route).
    default_profile_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Default output branding — when true, viewer config + reports default to
    # the ``none`` brand profile type (stripped LintPDF branding). Per-request
    # override still applies via ``brand`` query param or ``brand_profile_id``
    # on submission.
    unbranded_by_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    entitlement_overrides: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    # Per-feature AI grant list (WS-F — Alembic 037). JSONB list of
    # flag names; the resolver union-merges with PLAN_LIMITS[plan]
    # and ``plan_limit_overrides.ai_features``. Empty list is the
    # floor; ``[]``/NULL + ``ai_enabled=True`` + plan=STARTER means
    # no AI at all (the ``can_use`` AND-gate short-circuits).
    ai_features: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
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
    # ai_config / ai_credit_packages / ai_usage_logs relationships
    # removed in W6c-2r: TenantAIConfig / TenantAICreditPackage /
    # AIUsageLog live in lintpdf_saas.api.models on a separate
    # MetaData. Code that needs these tables queries them via the
    # SaaS-side service Protocols (AICreditBalanceService,
    # AIMonthlyUsageService, AIUsageRecorderService).
    #
    # color_config relationship removed in W6c-3: TenantColorConfig
    # lives in lintpdf_saas.api.models on a separate MetaData. No
    # OSS code accessed tenant.color_config directly anyway.
    brand_profiles: Mapped[list[BrandProfile]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class Job(Base):
    """Preflight job record."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_tenant_created", "tenant_id", "created_at"),
        Index("ix_jobs_tenant_status", "tenant_id", "status"),
    )

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
    # WS-C — Claude OCR recovered text layer. List[OCRPage]-shaped
    # JSONB: [{page_num, blocks: [{text, bbox, confidence}, ...]}, ...].
    # NULL when OCR didn't run (text-extraction succeeded, or the
    # tenant doesn't have the ``ocr`` AI feature).
    ocr_text_layer: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    # Opt-in override from ``POST /jobs?ocr=force``. When True the
    # OCR async task runs regardless of the extractable-char check.
    ocr_force: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa_text("false")
    )
    # PR 2 (OCR/ML accuracy): persisted output of the orchestrator's
    # shared text-region pass — list[DetectedTextRegion] serialised as JSON.
    # NULL when the pass didn't run (heuristic gated, GPU outage, or feature
    # disabled). Multiple downstream analyzers read this back at viewer time
    # to highlight outlined captions and fold-zone text.
    detected_text_regions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    # PR B (Slot 2A): compact structural evidence (font embedding, ICC,
    # encryption, XMP, output intents, spot colorspaces, AcroForm /
    # OCG presence) the Opus audit harness reads to adjudicate findings
    # vision can't verify on the rendered PDF alone.
    structural_evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # WS-D packaging inspectors. ``dieline`` carries the name-match
    # or Sonnet-fallback verdict; ``art_size_mm`` is NULL when the
    # dieline is missing (strict — see LPDF_DIE_MISSING);
    # ``legend_swatches`` carries the position/vision verdicts.
    dieline: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    art_size_mm: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)
    legend_swatches: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Per-stage timing captured by the orchestrator (extract, analyzers,
    # conformance, text_regions, ai_analyzers, filter, color_score,
    # bbox_enrich). Nested ``codex`` subtree carries codex's own per-stage
    # spans when LINTPDF_CODEX_STAGE_TELEMETRY_ENABLED is on and codex
    # emits the X-Codex-Stage-Durations-Ms header. NULL for jobs that
    # ran before this column was deployed.
    stage_durations_ms: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
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
    # Per-job brand specification — captured at submit time, wins
    # over the endpoint's ``default_brand_spec_id`` and the
    # tenant-default BrandSpec row. The orchestrator resolves this
    # via :func:`lintpdf.brand_specs.resolver.resolve_brand_spec_for_job`
    # and the analyzers gate the strict color advisories on
    # whether a spec was actually resolved. FK set to NULL on
    # delete so archived specs can't dangle. Phase 0.7 PR-B3d: the
    # FK to ``brand_specs.id`` was dropped (alembic 045) — the column
    # value now references a key inside the tenant's
    # ``ToggleOverride(toggle_id='brand')`` dict. PR-B4 drops the
    # column entirely when the legacy ``brand_specs`` table goes.
    brand_spec_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )
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

    # AI accuracy audit verdict (WS3 — Alembic 034).
    # Populated by ``lintpdf.audit.internal.InternalAuditor`` during
    # dev/QA runs (via the admin health toolbox) and by
    # ``lintpdf.audit.claude.ClaudeAuditor`` during production runs
    # when the tenant has ``"audit"`` in ``ai_features``. Left NULL
    # otherwise; the viewer's ``<AuditChip/>`` renders nothing when
    # the whole block is NULL.
    audit_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    audit_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Q-C4 / Q-C5 — AI-Explain cache. Populated by
    # ``lintpdf.ai.explain.explain_finding`` after a successful Claude
    # Haiku 4.5 call; left NULL until the dashboard / SDK calls the
    # explain endpoint. Caching avoids paying for the same explanation
    # on every page reload. Bumping the model id (``ai_explanation_model``)
    # signals stale data so a future cache-invalidation pass can refresh.
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_explanation_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_explanation_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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
    # Wave V V-06 (Q-D3) — per-webhook signing secret; NULL means the
    # dispatcher falls back to ``Tenant.webhook_signing_secret``.
    secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    events: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Per-endpoint retry budget. NULL -> fall back to the Celery
    # decorator's max_retries=3. Capped at 10 so a runaway config can't
    # DoS the webhook worker pool.
    max_retries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Initial retry delay in seconds. The dispatcher applies exponential
    # backoff: attempt N waits ``min(base * 2**N, retry_max_delay_seconds)``.
    retry_base_delay_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Ceiling on the exponential backoff. NULL -> fall back to 300s.
    retry_max_delay_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Default age (days) for WebhookDelivery rows owned by this endpoint
    # before the daily sweep deletes them. NULL -> keep forever.
    delivery_retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Per-event retention overrides, e.g.
    # ``{"billing.*": 365, "annotation.*": 7}``. Keys are fnmatch globs
    # matched against the event name; longest-match wins. Events that
    # don't match any key use ``delivery_retention_days``.
    retention_overrides: Mapped[dict[str, int] | None] = mapped_column(JSON, nullable=True)

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
        # Partial index for the admin "dead letters" view — most rows
        # will never flip to is_dead=true so a partial index keeps the
        # lookup fast without paying to index every delivery.
        Index(
            "ix_webhook_deliveries_dead",
            "tenant_id",
            "created_at",
            postgresql_where=sa_text("is_dead = true"),
        ),
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
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Dead-letter flag: set to True once the dispatcher gives up (max
    # retries exhausted). Operators replay via
    # ``POST /api/v1/webhooks/deliveries/{id}/replay``; a successful
    # replay flips this back to False.
    is_dead: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=sa_text("false"), default=False
    )
    # Count of manual replay attempts kicked off from the admin UI.
    # Useful for detecting chronic-failing endpoints.
    replay_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=sa_text("0"), default=0
    )


class SystemProfile(Base):
    """System-wide preflight profile.

    Runtime-editable replacement for the bundled-JSON-only
    ``ProfileRegistry``. Seeded from
    ``packages/engine/src/lintpdf/profiles/builtin/*.json`` on first
    boot with ``source='bundled'``. Admins can PATCH any row — the
    first edit flips ``source`` to ``'admin'`` so future re-seed
    passes skip it.

    Visibility:
      * ``all`` — every tenant sees this preset (default).
      * ``plan`` — only tenants whose plan is ``>= min_plan`` (plan
        hierarchy resolver) see it.
      * ``tenants`` — only tenants whose id appears in
        ``visible_tenant_ids`` see it.
      * ``plan_and_tenants`` — both gates apply.
    """

    __tablename__ = "system_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    preflight_profile_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, server_default="bundled")
    bundled_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    visibility_mode: Mapped[str] = mapped_column(String(32), nullable=False, server_default="all")
    min_plan: Mapped[str | None] = mapped_column(String(32), nullable=True)
    visible_tenant_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        _PG_UUID_ARRAY, nullable=True
    )
    created_by_admin_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# PlanLimitOverride was extracted to lintpdf_saas.api.models in W6c-1
# (PRs thinkneverland/lint-pdf-saas#25 + thinkneverland/lint-pdf#PR-B).
# The plan_limit_overrides table remains in the shared Postgres database;
# only the Python class definition moves. Engine code reaches it through
# the PlanOverridesService Protocol seam (no direct import).


# ApiKey was extracted to lintpdf_saas.api.models in W6c-7n
# (thinkneverland/lint-pdf-saas#44). The api_keys table remains in
# the shared Postgres database; only the Python class definition
# moves. Engine code never reads ApiKey directly -- auth dispatches
# through the TenantContextService.load_by_api_key_hash Protocol
# seam (default no-op in OSS, SaaSTenantContextService walks
# lintpdf_saas.api.models.ApiKey in production).


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


# TenantAIConfig / TenantAICreditPackage / AIUsageLog and the
# AIBillingMode enum were extracted to lintpdf_saas.api.models in
# W6c-2r (PRs thinkneverland/lint-pdf-saas#31 + thinkneverland/lint-pdf#436).
# Engine code reaches the underlying tables through Protocol seams in
# lintpdf.services.* (AICreditBalanceService, AICreditCheckService,
# AICreditDeductionService, AIMonthlyUsageService, AIUsageRecorderService,
# AIConfigService) — no direct ORM import survives in OSS source.
#
# TenantColorConfig was extracted to lintpdf_saas.api.models in W6c-3
# (PRs thinkneverland/lint-pdf-saas#26 + thinkneverland/lint-pdf#418/#419).
# Engine code reaches it through the TenantColorService Protocol seam
# at lintpdf.services.tenant_color (no direct import).


# UserAIAccess was extracted to lintpdf_saas.api.models in W6b
# (PRs thinkneverland/lint-pdf-saas#23 + thinkneverland/lint-pdf#PR-B).
# The user_ai_access table remains in the shared Postgres database.


# Trial Submission models (TrialSubmissionStatus, TrialSubmission,
# TrialFile) were extracted to lintpdf_saas.api.models in W6a
# (PRs thinkneverland/lint-pdf-saas#22 + thinkneverland/lint-pdf#PR-B).
# The trial_submissions and trial_files tables remain in the shared
# Postgres database — the extraction only moves the Python class
# definitions. SaaS code accesses them via lintpdf_saas.api.models.


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


# ApprovalChain / ApprovalStep were extracted to lintpdf_saas.api.models
# in W6c-5 (PRs thinkneverland/lint-pdf-saas#39/#40 +
# thinkneverland/lint-pdf#439/#440/#441/#442). Engine code reaches
# the underlying tables exclusively through the ApprovalsService
# Protocol seam at lintpdf.services.approvals.


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


# ShareLinkVisitor was extracted to lintpdf_saas.api.models in W6c-4
# (PRs thinkneverland/lint-pdf-saas#37/#38 + thinkneverland/lint-pdf#437/#XX).
# Engine code reaches the share_link_visitors table through the
# ShareLinkVisitorService Protocol seam at
# lintpdf.services.share_link_visitor (no direct ORM import in OSS).
