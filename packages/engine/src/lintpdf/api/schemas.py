"""Pydantic schemas for API request/response models."""

from __future__ import annotations

import uuid  # noqa: TC003
from datetime import datetime  # noqa: TC003

from pydantic import BaseModel, Field

# --- Job schemas ---


class JobCreateResponse(BaseModel):
    """Response after submitting a preflight job."""

    job_id: uuid.UUID
    status: str = "pending"
    message: str = "Job submitted successfully"


class FindingResponse(BaseModel):
    """A single preflight finding."""

    inspection_id: str = Field(
        ...,
        description=(
            "Stable identifier for the check that produced this finding. "
            "Collates repeated findings across jobs. For imported findings "
            "the upstream check ID is passed through when available."
        ),
    )
    severity: str = Field(
        ...,
        description="Canonical severity. One of: `error`, `warning`, `advisory`.",
    )
    message: str = Field(
        ...,
        description="Human-readable description rendered in the viewer and reports.",
    )
    page_num: int | None = Field(
        default=None,
        description=("1-indexed page number. `null` for document-level findings."),
    )
    details: dict[str, object] | None = Field(
        default=None,
        description=(
            "Free-form key/value metadata surfaced in the finding detail panel. "
            "Typical keys: `resolution_dpi`, `threshold_dpi`, `color_space`."
        ),
    )
    source: str = Field(
        default="engine",
        description=(
            "Where the finding originated. Values: `engine`, `ai`, "
            "`external:pitstop`, `external:callas`, `external:acrobat`, "
            "`external:lintpdf_json`, `external:custom:<mapping-id>`."
        ),
    )
    category: str | None = Field(
        default=None,
        description=(
            "Grouping key. Typical values: `color`, `fonts`, `images`, "
            "`geometry`, `transparency`, `overprint`, `text`, `metadata`."
        ),
    )
    bbox: list[float] | None = Field(
        default=None,
        description=(
            "Bounding box `[x0, y0, x1, y1]` in PDF points (lower-left "
            "origin). Used by the viewer to draw highlight boxes."
        ),
    )
    object_id: str | None = Field(
        default=None,
        description=(
            "Resource name of the target object. Examples: `Im42` for an "
            "image XObject, `Helvetica-Bold` for a font."
        ),
    )
    object_type: str | None = Field(
        default=None,
        description=(
            "Target object classifier. One of: `image`, `text`, `path`, `font`, `page`, `document`."
        ),
    )


class JobSummaryResponse(BaseModel):
    """Summary statistics for a completed job."""

    total_findings: int
    error_count: int
    warning_count: int
    advisory_count: int
    passed: bool
    page_count: int
    file_size_bytes: int


class JobResponse(BaseModel):
    """Full job response with status and optional results."""

    job_id: uuid.UUID
    status: str = Field(
        ...,
        description=(
            "Terminal values are `complete` and `failed`. In-flight values are "
            "`pending` and `processing`. Note the enum uses `complete` (not "
            "`completed`) -- callers polling for status == completed will "
            "loop forever. Accept both spellings when writing client code."
        ),
    )
    profile_id: str
    file_name: str
    file_size: int
    page_count: int | None = None
    created_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    summary: JobSummaryResponse | None = None
    findings: list[FindingResponse] | None = None
    error_message: str | None = None
    jdf_overrides: dict[str, object] | None = None
    color_quality_score: float | None = None
    color_quality_grade: str | None = None
    color_score_breakdown: dict[str, float] | None = None
    reports: dict[str, str] | None = None


class JobListResponse(BaseModel):
    """Paginated list of jobs."""

    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int


# --- Aggregated /jobs/{id}/state schemas ---


class JobStateReportInfo(BaseModel):
    """One minted report token as embedded in /jobs/{id}/state."""

    format: str = Field(
        ...,
        description="Report format: `pdf`, `annotated_pdf`, `annotated_pdf_markup`, `html`, `json`, `xml`.",
    )
    url: str = Field(..., description="Public hosted URL (`/r/{token}.{ext}`).")
    token: str = Field(
        ...,
        description="Raw token. Use only for building URLs; never embed in client-side code.",
    )
    expires_at: str | None = Field(
        default=None,
        description="ISO-8601 UTC. `null` means no expiry.",
    )
    allow_annotations: bool = Field(
        default=False,
        description=(
            "When True, anonymous viewers at `/view/{token}` can POST annotations if "
            "they supply an `X-Visitor-Email` header. Default False = read-only share."
        ),
    )
    require_visitor_email: bool | None = Field(
        default=None,
        description=(
            "Per-token override of the tenant-wide email-capture gate. `null` inherits "
            "tenant default; True forces gate on; False forces gate off."
        ),
    )


class JobStateApprovalStep(BaseModel):
    """One row in the approval chain history embedded in /jobs/{id}/state."""

    step_index: int = Field(..., description="0-indexed step position in the chain.")
    step_name: str = Field(..., description="Human label for the step.")
    approver_email: str = Field(..., description="Email of the approver who decided.")
    decision: str = Field(
        ...,
        description="`pending`, `approved`, or `rejected`. `pending` means the step is open.",
    )
    notes: str | None = Field(
        default=None,
        description=(
            "Free-text notes recorded by the approver alongside their decision. "
            "Rendered in the aggregated `verdict.notes` field and in the markup PDF."
        ),
    )
    decided_at: datetime | None = Field(
        default=None,
        description="ISO-8601 timestamp of the decision. `null` for pending steps.",
    )


class JobStateApprovalChain(BaseModel):
    """Approval chain section of /jobs/{id}/state.

    Returned as `null` when no chain is attached to the job.
    """

    id: str = Field(..., description="Chain UUID.")
    template_id: str | None = Field(
        default=None,
        description="UUID of the template the chain was spawned from, or `null` for ad-hoc.",
    )
    status: str = Field(
        ...,
        description="`pending`, `approved`, `rejected`, or `cancelled`.",
    )
    current_step: int = Field(
        ...,
        description="Index of the step currently awaiting a decision. `-1` when the chain is terminal.",
    )
    step_history: list[JobStateApprovalStep] = Field(
        default_factory=list,
        description="Ordered per-step decisions, including any approver `notes`.",
    )
    created_at: datetime | None = None
    completed_at: datetime | None = None


class JobStateVerdict(BaseModel):
    """Manual verdict section of /jobs/{id}/state.

    Carries both the auto-assigned `auto_passed` (from preflight summary) and any
    human-set verdict + aggregated approval notes.
    """

    verdict: str | None = Field(
        default=None,
        description="Human-set verdict: `pass`, `fail`, or `null` if no manual verdict is recorded.",
    )
    auto_passed: bool | None = Field(
        default=None,
        description="Mirrors `summary.passed`. `true` when the preflight run had zero errors.",
    )
    verdict_by: str | None = Field(
        default=None,
        description="Email of the reviewer who set the manual verdict.",
    )
    verdict_at: str | None = Field(
        default=None,
        description="ISO-8601 timestamp of the manual verdict.",
    )
    notes: str | None = Field(
        default=None,
        description=(
            "Aggregated approval notes. Concatenation of every step's `notes` field "
            "once the chain completes, for easy export in audit trails."
        ),
    )


class JobStateAnnotationComment(BaseModel):
    """One comment embedded in the `annotations.items[].comments` array."""

    id: str
    annotation_id: str
    author_email: str
    body: str
    created_at: str
    updated_at: str


class JobStateAnnotationItem(BaseModel):
    """One annotation with its full comment thread embedded inline.

    Matches the shape returned by `GET /viewer/jobs/{id}/annotations?include=comments`
    so both endpoints can share the same client-side parser.
    """

    id: str
    job_id: str
    page_num: int
    kind: str = Field(..., description='"rect" | "circle" | "arrow" | "freehand" | "note"')
    geometry: dict[str, object]
    color: str
    text: str | None
    author_email: str
    created_at: str
    updated_at: str
    comments: list[JobStateAnnotationComment] = Field(
        default_factory=list,
        description="Threaded comments on this annotation, oldest first.",
    )


class JobStateAnnotations(BaseModel):
    """Annotations section of /jobs/{id}/state."""

    total: int = Field(..., description="Total annotation count across every page.")
    by_page: dict[str, int] = Field(
        default_factory=dict,
        description="Counts keyed by `page_num` as a string (JSON-object-safe).",
    )
    items: list[JobStateAnnotationItem] = Field(
        default_factory=list,
        description="Every annotation, each with its `comments: []` thread embedded.",
    )


class JobStateResponse(BaseModel):
    """Universal state of a preflight job — preflight + approvals + annotations + reports.

    One call returns everything a dashboard / audit exporter / partner integration
    needs. Each section is nullable so callers can filter with `?include=...` and
    get a compact payload.
    """

    job: JobResponse = Field(
        ...,
        description="Core job metadata + preflight summary + findings + auto-report URLs.",
    )
    reports: list[JobStateReportInfo] | None = Field(
        default=None,
        description=(
            "Every minted report token for this job, including share-link metadata "
            "(`allow_annotations`, `require_visitor_email`). `null` when the "
            "`reports` section is excluded via `?include=`."
        ),
    )
    approval_chain: JobStateApprovalChain | None = Field(
        default=None,
        description=(
            "Approval chain attached to the job, including each step's `notes`. "
            "`null` when no chain is attached, OR when the section is excluded."
        ),
    )
    verdict: JobStateVerdict | None = Field(
        default=None,
        description="Manual verdict + aggregated approval notes + auto-pass flag.",
    )
    annotations: JobStateAnnotations | None = Field(
        default=None,
        description=(
            "Every viewer annotation with its comments embedded inline — no N+1 "
            "fan-out. `null` when the section is excluded."
        ),
    )


# --- Profile schemas ---


class ProfileSummaryResponse(BaseModel):
    """Summary of a preflight profile."""

    profile_id: str
    name: str
    description: str = ""
    conformance: str | None = None
    workflow: str = "CMYK"
    is_builtin: bool = True


class ProfileListResponse(BaseModel):
    """List of available profiles."""

    profiles: list[ProfileSummaryResponse]


class ProfileDetailResponse(BaseModel):
    """Full profile details including thresholds."""

    profile_id: str
    name: str
    description: str = ""
    version: str = "1.0"
    conformance: str | None = None
    workflow: str = "CMYK"
    checks: dict[str, object] = Field(default_factory=dict)
    thresholds: dict[str, object] = Field(default_factory=dict)
    is_builtin: bool = True


class ProfileCreateRequest(BaseModel):
    """Request to create a custom profile."""

    profile_id: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$",
        description="Lowercase kebab-case profile identifier.",
    )
    preflight_profile: dict[str, object] = Field(
        description="Preflight Profile JSON conforming to PreflightProfile schema.",
    )


class ProfileCreateResponse(BaseModel):
    """Response after creating a custom profile."""

    profile_id: str
    message: str = "Profile created successfully"


# --- Webhook schemas ---


class WebhookCreateRequest(BaseModel):
    """Request to register a webhook endpoint."""

    url: str = Field(max_length=2048, description="Webhook delivery URL.")
    events: list[str] = Field(
        default_factory=lambda: ["job.completed", "job.failed"],
        description="Events to subscribe to.",
    )
    max_retries: int | None = Field(
        default=None,
        ge=0,
        le=10,
        description=(
            "Override the default retry budget (3) for 5xx/timeout failures. "
            "Capped at 10 so a runaway config can't DoS the dispatch pool. "
            "Null inherits the platform default."
        ),
    )
    retry_base_delay_seconds: int | None = Field(
        default=None,
        ge=1,
        le=600,
        description=(
            "Initial retry delay. Subsequent retries double exponentially, "
            "capped by `retry_max_delay_seconds`. Null inherits 5."
        ),
    )
    retry_max_delay_seconds: int | None = Field(
        default=None,
        ge=1,
        le=3600,
        description=(
            "Ceiling on the exponential backoff so a high `max_retries` "
            "never waits absurdly long. Null inherits 300."
        ),
    )
    delivery_retention_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description=(
            "Days to keep WebhookDelivery audit rows before the nightly "
            "sweep deletes them. Null keeps forever (use with care -- "
            "payloads stay queryable until you remove the endpoint)."
        ),
    )
    retention_overrides: dict[str, int] | None = Field(
        default=None,
        description=(
            "Per-event retention overrides. Keys are fnmatch globs matched "
            'against event names, e.g. `{"billing.*": 365, "annotation.*": 7}`. '
            "Longest-match wins. Events that don't match any key use "
            "`delivery_retention_days`."
        ),
    )


class WebhookResponse(BaseModel):
    """Webhook endpoint details."""

    id: uuid.UUID
    url: str
    events: list[str]
    is_active: bool
    created_at: datetime
    max_retries: int | None = Field(
        default=None,
        description="Per-endpoint retry budget override. Null = platform default (3).",
    )
    retry_base_delay_seconds: int | None = Field(
        default=None,
        description="Initial retry delay in seconds. Null = platform default (5).",
    )
    retry_max_delay_seconds: int | None = Field(
        default=None,
        description="Exponential-backoff ceiling in seconds. Null = platform default (300).",
    )
    delivery_retention_days: int | None = Field(
        default=None,
        description="Days to retain WebhookDelivery rows. Null = forever.",
    )
    retention_overrides: dict[str, int] | None = Field(
        default=None,
        description="Per-event retention overrides keyed by fnmatch glob.",
    )


class WebhookUpdateRequest(BaseModel):
    """Request to update a webhook endpoint. All fields optional."""

    url: str | None = Field(default=None, max_length=2048, description="New webhook URL.")
    events: list[str] | None = Field(default=None, description="New event subscriptions.")
    is_active: bool | None = Field(default=None, description="Enable or disable the webhook.")
    max_retries: int | None = Field(default=None, ge=0, le=10)
    retry_base_delay_seconds: int | None = Field(default=None, ge=1, le=600)
    retry_max_delay_seconds: int | None = Field(default=None, ge=1, le=3600)
    delivery_retention_days: int | None = Field(default=None, ge=1, le=365)
    retention_overrides: dict[str, int] | None = None


class WebhookListResponse(BaseModel):
    """List of webhook endpoints."""

    webhooks: list[WebhookResponse]


# --- Custom endpoint schemas ---


class EndpointCreateRequest(BaseModel):
    """Request to create a custom API endpoint."""

    slug: str = Field(
        min_length=2,
        max_length=255,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$",
        description="Lowercase kebab-case URL slug.",
    )
    profile_id: str = Field(description="Profile ID to bind this endpoint to.")
    description: str = Field(default="", max_length=1024)


class EndpointResponse(BaseModel):
    """Custom endpoint details."""

    id: uuid.UUID
    slug: str
    profile_id: str
    description: str
    is_active: bool
    created_at: datetime


class EndpointUpdateRequest(BaseModel):
    """Request to update a custom endpoint. All fields optional."""

    slug: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    profile_id: str | None = None
    description: str | None = None
    is_active: bool | None = None


class EndpointListResponse(BaseModel):
    """List of custom endpoints."""

    endpoints: list[EndpointResponse]


# --- Health schemas ---


class HealthResponse(BaseModel):
    """Service health check response."""

    status: str
    service: str = "lintpdf"


class StatusResponse(BaseModel):
    """Detailed service status."""

    status: str
    service: str = "lintpdf"
    version: str = "0.1.0"
    database: str = "unknown"
    redis: str = "unknown"
    queue_depth: int = 0
    queue_depths: dict[str, int] = Field(default_factory=dict)
    worker_count: int = 0


# --- Color config schemas ---


class ColorConfigResponse(BaseModel):
    """Tenant color management configuration."""

    default_output_condition: str | None = None
    custom_icc_profiles: list[dict[str, object]] | None = None
    brand_palette: list[dict[str, object]] | None = None
    custom_dictionary_words: list[str] | None = None
    default_tac_threshold: int = 320
    default_safe_zone_margin_mm: float = 3.0
    package_capacity_default: str | None = None
    package_surface_area_default: float | None = None
    target_market: str | None = None
    epm_mode_default: bool = False
    custom_pantone_overrides: dict[str, dict[str, object]] | None = None


class ColorConfigUpdateRequest(BaseModel):
    """Request to update color config. All fields optional."""

    default_output_condition: str | None = None
    default_tac_threshold: int | None = None
    default_safe_zone_margin_mm: float | None = None
    package_capacity_default: str | None = None
    package_surface_area_default: float | None = None
    target_market: str | None = None
    epm_mode_default: bool | None = None


class PaletteUpdateRequest(BaseModel):
    """Request to update brand color palette."""

    colors: list[dict[str, object]] = Field(
        description="Array of color definitions with name, value, and thresholds."
    )


# --- Pantone override schemas ---


class PantoneOverrideEntry(BaseModel):
    """A single Pantone color override."""

    name: str = Field(description="Pantone color name, e.g. 'PANTONE 485 C'")
    lab: list[float] = Field(min_length=3, max_length=3, description="CIE L*a*b* values")
    cmyk_bridge: list[float] | None = Field(
        None, min_length=4, max_length=4, description="CMYK bridge values [C, M, Y, K]"
    )


class PantoneOverridesUpdateRequest(BaseModel):
    """Bulk set / replace all Pantone overrides for a tenant."""

    overrides: list[PantoneOverrideEntry] = Field(
        description="List of Pantone color overrides to set."
    )


class PantoneOverridesResponse(BaseModel):
    """Current Pantone overrides for a tenant."""

    count: int
    overrides: dict[str, dict[str, object]]


class GamutConditionResponse(BaseModel):
    """Available gamut condition."""

    slug: str
    name: str
    region: str
    use_case: str
    tac_limit: int | None = None


class GamutConditionsListResponse(BaseModel):
    """List of available gamut conditions."""

    conditions: list[GamutConditionResponse]


class IccProfileUploadResponse(BaseModel):
    """Response after uploading an ICC profile."""

    profile_id: str
    name: str
    color_space: str | None = None
    version: str | None = None
    message: str = "ICC profile uploaded successfully"


# --- User AI access schemas ---


class UserAIAccessResponse(BaseModel):
    """User AI access configuration."""

    user_id: uuid.UUID
    ai_enabled: bool = False
    personal_spending_limit: float | None = None
    trial_enabled: bool = False
    trial_expires_at: datetime | None = None


class UserAIAccessUpdateRequest(BaseModel):
    """Request to update user AI access."""

    ai_enabled: bool | None = None
    personal_spending_limit: float | None = None
    trial_enabled: bool | None = None
    trial_expires_at: datetime | None = None


# --- Brand profile schemas ---


class BrandProfileResponse(BaseModel):
    """Brand profile details."""

    id: uuid.UUID
    name: str
    profile_type: str
    brand_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    footer_text: str | None = None
    hide_footer: bool = False
    is_default: bool = False
    created_at: datetime
    updated_at: datetime
    custom_domain: str | None = None
    custom_domain_verified: bool = False
    custom_domain_dns_target: str | None = Field(
        default=None,
        description=(
            "CNAME target for this profile's report domain. Always "
            "``edge.lintpdf.com`` -- our Fly.io Caddy edge that "
            "terminates TLS and path-routes to the right backend."
        ),
    )
    app_custom_domain: str | None = None
    app_custom_domain_verified: bool = False
    app_custom_domain_dns_target: str | None = Field(
        default=None,
        description="CNAME target for this profile's app/viewer domain.",
    )


class BrandProfileListResponse(BaseModel):
    """List of brand profiles."""

    profiles: list[BrandProfileResponse]


class BrandProfileCreateRequest(BaseModel):
    """Request to create a brand profile."""

    name: str = Field(min_length=1, max_length=255, description="Display name for this profile.")
    profile_type: str = Field(
        default="custom",
        description="Profile type: custom, lintpdf, or none.",
    )
    brand_name: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=2048)
    primary_color: str | None = Field(default=None, max_length=7)
    accent_color: str | None = Field(default=None, max_length=7)
    footer_text: str | None = Field(default=None, max_length=500)
    hide_footer: bool = False


class BrandProfileUpdateRequest(BaseModel):
    """Request to update a brand profile. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    profile_type: str | None = None
    brand_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    footer_text: str | None = None
    hide_footer: bool | None = None


class SetDefaultBrandProfileRequest(BaseModel):
    """Request to set the default brand profile."""

    brand_profile_id: uuid.UUID | None = Field(
        description="ID of the brand profile to set as default, or null to clear."
    )


# --- White-label custom report domain schemas ---


class SetCustomDomainRequest(BaseModel):
    """Request to set or clear a tenant's white-label custom report domain.

    Pass null to clear the domain. Setting always resets the verified
    flag to False — only admins can flip verified=True after confirming
    Railway + DNS are in place.
    """

    domain: str | None = Field(
        default=None,
        max_length=255,
        description=(
            "Hostname (no scheme, no path, no port) — e.g. 'reports.acmeprint.com'. "
            "Pass null to remove the existing domain."
        ),
    )


class TenantCustomDomainResponse(BaseModel):
    """Current state of a tenant's white-label custom report domain."""

    tenant_id: uuid.UUID
    domain: str | None
    verified: bool
    requested_at: datetime | None
    plan_allows_whitelabel: bool
    dns_target: str = Field(
        default="edge.lintpdf.com",
        description=(
            "The CNAME target customers point their hostname at. Always "
            "``edge.lintpdf.com`` -- our Fly.io Caddy edge that terminates "
            "TLS (via on-demand Let's Encrypt) and path-routes to LintPDF's "
            "Railway backends. One CNAME, no TXT records, no cert to install."
        ),
    )


class AdminCustomDomainRow(BaseModel):
    """Admin view of a tenant-level or profile-level custom domain."""

    scope: str = Field(description="'tenant', 'tenant_app', 'brand_profile', or 'brand_profile_app'")
    tenant_id: uuid.UUID
    tenant_name: str
    brand_profile_id: uuid.UUID | None = None
    brand_profile_name: str | None = None
    domain: str
    verified: bool
    requested_at: datetime | None
    dns_target: str | None = Field(
        default=None,
        description=(
            "CNAME target the customer should point their domain at. "
            "Always ``edge.lintpdf.com`` -- the Fly.io Caddy edge."
        ),
    )


class AdminCustomDomainListResponse(BaseModel):
    """Paginated-ish list of custom domains from the admin panel."""

    pending: list[AdminCustomDomainRow]
    active: list[AdminCustomDomainRow]


class AdminUpdateCustomDomainRequest(BaseModel):
    """Admin PATCH to set verification state on a custom domain.

    Scope is implicit from which URL parameter is populated — tenant_id
    vs (tenant_id, profile_id). This body only carries the fields the
    admin is changing.
    """

    domain: str | None = Field(
        default=None,
        max_length=255,
        description="New domain value. Pass null to clear the domain entirely.",
    )
    verified: bool | None = Field(
        default=None,
        description="Flip verified state. null = no change.",
    )
