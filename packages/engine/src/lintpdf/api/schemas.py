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


class WebhookResponse(BaseModel):
    """Webhook endpoint details."""

    id: uuid.UUID
    url: str
    events: list[str]
    is_active: bool
    created_at: datetime


class WebhookUpdateRequest(BaseModel):
    """Request to update a webhook endpoint. All fields optional."""

    url: str | None = Field(default=None, max_length=2048, description="New webhook URL.")
    events: list[str] | None = Field(default=None, description="New event subscriptions.")
    is_active: bool | None = Field(default=None, description="Enable or disable the webhook.")


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
        default="reports.lintpdf.com",
        description="The CNAME target customers should point their subdomain at.",
    )


class AdminCustomDomainRow(BaseModel):
    """Admin view of a tenant-level or profile-level custom domain."""

    scope: str = Field(description="'tenant' or 'brand_profile'")
    tenant_id: uuid.UUID
    tenant_name: str
    brand_profile_id: uuid.UUID | None = None
    brand_profile_name: str | None = None
    domain: str
    verified: bool
    requested_at: datetime | None


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
