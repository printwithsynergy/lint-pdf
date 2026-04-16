"""Universal per-call override envelope for submit + mint endpoints.

The LintPDF API has always accepted a few per-call overrides — ``brand``,
``ai_enabled``, ``ai_features``, ``require_visitor_email`` and so on —
scattered across form fields and body keys. That worked for the headline
cases but left a long tail of tenant/profile settings that could only be
changed by editing the tenant row or cloning the profile.

This module introduces **one consistent envelope** every submission and
mint accepts. Every field is optional; only provided values take effect.
Nothing the tenant doesn't already have access to becomes reachable —
the resolver enforces tenant entitlements on every path (plan-gated
formats, whitelabel branding, etc.) and silently drops AI categories the
tenant hasn't been provisioned for rather than 403'ing the whole call.

Back-compat: the flat parameters that already existed keep working.
``_merge_flat_compat`` folds them onto the same override slots before
resolution, so old clients see zero behaviour change.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChecksOverrides(BaseModel):
    """Per-call tweaks to which preflight checks fire and at what severity.

    Mirrors ``profile.checks`` — see
    ``lintpdf.profiles.schema.CheckConfig`` — so an override applies on top
    of the selected profile's own values. Lists replace, not merge
    (match the JDF contract used for thresholds): pass the full list you
    want enabled / disabled, not a delta.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: list[str] | None = Field(
        default=None,
        description=(
            "Glob patterns of check IDs to enable (e.g. ``['LPDF_*', "
            "'PDFX4-*']``). ``None`` leaves the profile's ``checks.enabled``"
            " untouched."
        ),
    )
    disabled: list[str] | None = Field(
        default=None,
        description=(
            "Glob patterns of check IDs to disable. Takes precedence over"
            " ``enabled``. ``None`` leaves the profile's ``checks.disabled``"
            " untouched."
        ),
    )
    severity_overrides: dict[str, str] | None = Field(
        default=None,
        description=(
            "Map check ID -> severity (``error`` / ``warning`` / "
            "``advisory`` / ``ignore``). Merges into the profile's"
            " ``severity_overrides`` — later keys win."
        ),
    )
    max_severity: str | None = Field(
        default=None,
        description=(
            "Cap every finding at this severity. ``None`` leaves the"
            " profile value untouched; pass the empty string to clear a"
            " profile-level cap."
        ),
    )


class ColorOverrides(BaseModel):
    """Per-call color-workflow knobs."""

    model_config = ConfigDict(extra="forbid")

    target_output_condition: str | None = None
    gamut_check: bool | None = None
    epm_mode: bool | None = None
    ecg_mode: bool | None = None
    tac_limit: float | None = Field(default=None, ge=0, le=500)


class AIOverrides(BaseModel):
    """Per-call AI feature selection.

    Coexists with the existing flat ``ai_enabled`` / ``ai_categories`` /
    ``ai_features`` / ``ai_preset`` form params. If both the flat form
    and this nested object are provided, the nested object wins (it's
    more explicit).
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    categories: list[str] | None = None
    features: list[str] | None = None
    preset: str | None = None
    language_for_reports: str | None = None


class ViewerOverrides(BaseModel):
    """Per-call viewer capability + UI-default toggles.

    Mirrors ``lintpdf.profiles.schema.ViewerConfig``. Applied when the
    viewer config endpoint builds its response so every share link can
    carry its own UI shape (hide separations for brand assets, force
    dark mode for press floor viewing, etc.) without needing a
    BrandProfile.
    """

    model_config = ConfigDict(extra="forbid")

    # Feature toggles
    enable_separations: bool | None = None
    enable_tac_heatmap: bool | None = None
    enable_annotations: bool | None = None
    enable_measurement: bool | None = None
    enable_comparison: bool | None = None
    enable_layers: bool | None = None
    enable_findings_panel: bool | None = None
    enable_page_thumbnails: bool | None = None
    enable_zoom: bool | None = None
    enable_download: bool | None = None
    enable_html_report_link: bool | None = None

    # Behaviour defaults
    verdict_mode: str | None = None
    default_zoom: int | None = Field(default=None, ge=25, le=400)
    default_dpi: int | None = Field(default=None, ge=72, le=600)
    default_tac_limit: float | None = Field(default=None, ge=100, le=500)
    toolbar_position: str | None = None
    dark_mode: bool | None = None
    viewer_logo_url: str | None = None
    viewer_accent_color: str | None = None


class ReportOverrides(BaseModel):
    """Per-mint report-generation knobs.

    Some of these (``formats``, ``detail_level``, ``summary_page``,
    ``expiry_days``, ``email_to``) already exist as top-level fields on
    ``GenerateReportsRequest``. Repeating them here lets callers send a
    single ``overrides`` envelope across endpoints; the resolver folds
    the flat fields in first, so both shapes work.
    """

    model_config = ConfigDict(extra="forbid")

    formats: list[str] | None = None
    detail_level: str | None = None
    summary_page: str | None = None
    expiry_days: int | None = Field(default=None, ge=0)
    email_to: str | None = None
    footer_text: str | None = None


class BrandingOverridesEnvelope(BaseModel):
    """Per-call branding selection.

    Mirrors the existing flat ``brand`` / ``unbranded`` params and the
    ``BrandingOverride`` body used on mint, rolled into one structure.
    """

    model_config = ConfigDict(extra="forbid")

    mode: str | None = Field(
        default=None,
        description="``anonymous``, ``lintpdf``, or ``profile``.",
    )
    profile_id: str | None = Field(
        default=None,
        description="Required when ``mode='profile'``. BrandProfile UUID.",
    )
    name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    hide_footer: bool | None = None
    footer_text: str | None = None


class ShareOverrides(BaseModel):
    """Per-call share-link gating (email capture, annotation permissions)."""

    model_config = ConfigDict(extra="forbid")

    require_visitor_email: bool | None = None
    allow_annotations: bool | None = None


class OverridesEnvelope(BaseModel):
    """Top-level envelope. Every field optional; absent = inherit.

    This is the single surface both submit and mint accept. Submit
    receives it as a JSON string form field (multipart form can't nest
    JSON naturally); mint as a body key. The resolver treats them the
    same way.
    """

    model_config = ConfigDict(extra="forbid")

    checks: ChecksOverrides | None = None
    thresholds: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Arbitrary subset of ``ThresholdConfig`` fields to override."
            " Dict form rather than a full Pydantic mirror because the"
            " threshold surface is large and mostly numeric — a dict is"
            " cheap to validate in the orchestrator against the existing"
            " ``ThresholdConfig.model_copy(update=...)`` path."
        ),
    )
    conformance: str | None = None
    workflow: str | None = None
    color: ColorOverrides | None = None
    ai: AIOverrides | None = None
    viewer: ViewerOverrides | None = None
    report: ReportOverrides | None = None
    branding: BrandingOverridesEnvelope | None = None
    share: ShareOverrides | None = None
