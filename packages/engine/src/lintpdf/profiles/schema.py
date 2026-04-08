"""Preflight Profile schema - configurable preflight profile.

A Preflight Profile defines which checks to run, severity overrides,
threshold configuration, and optional conformance standard.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConditionBlock(BaseModel):
    """A conditional rule for a specific check.

    When the 'when' clause matches a finding's context, the condition's
    overrides are applied (severity, params, include/exclude).
    """

    when: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Context conditions to match. Keys: page, object_type, object_id, "
            "source, category, severity, or any details key. Values: literal "
            "match or operator dict ({in: [...], gt: N, contains: str, ...})."
        ),
    )
    severity: str | None = Field(
        default=None, description="Override severity when condition matches."
    )
    params: dict[str, object] = Field(
        default_factory=dict,
        description="Override threshold parameters when condition matches.",
    )
    include: bool = Field(
        default=True, description="Set to false to suppress findings matching this condition."
    )


class PerCheckConfig(BaseModel):
    """Per-check configuration with conditional overrides."""

    enabled: bool = Field(default=True, description="Whether this check is enabled.")
    params: dict[str, object] = Field(
        default_factory=dict, description="Default parameter overrides for this check."
    )
    conditions: list[ConditionBlock] = Field(
        default_factory=list,
        description="Ordered list of conditional rules. First match wins.",
    )


class CheckConfig(BaseModel):
    """Controls which checks are enabled and severity overrides."""

    enabled: list[str] = Field(
        default_factory=lambda: ["LPDF_*", "PDFX4-*"],
        description="Check ID patterns to enable (glob-style). Default: all.",
    )
    disabled: list[str] = Field(
        default_factory=list,
        description="Check ID patterns to disable (takes precedence over enabled).",
    )
    severity_overrides: dict[str, str] = Field(
        default_factory=dict,
        description='Map of check ID to severity override (e.g. {"LPDF_IMG_002": "ignore"}).',
    )
    max_severity: str | None = Field(
        default=None,
        description=(
            'Cap every finding severity at this value (one of "error", '
            '"warning", "advisory"). Used by non-blocking profiles such as '
            "lintpdf-advisory-only. ``None`` leaves severities untouched."
        ),
    )
    per_check: dict[str, PerCheckConfig] = Field(
        default_factory=dict,
        description="Per-check configuration with conditional overrides.",
    )


class ThresholdConfig(BaseModel):
    """Numeric thresholds for analyzer checks."""

    min_dpi: float = Field(default=150.0, ge=0, description="Minimum image DPI.")
    max_dpi: float = Field(default=600.0, ge=0, description="Maximum image DPI warning.")
    tac_limit: float = Field(default=300.0, ge=0, description="Total Area Coverage limit (%).")
    min_bleed_mm: float = Field(default=3.0, ge=0, description="Minimum bleed in mm.")
    hairline_threshold: float = Field(
        default=0.25, ge=0, description="Stroke width below which is considered hairline (pt)."
    )
    small_text_threshold: float = Field(
        default=6.0, ge=0, description="Font size below which text is 'small' (pt)."
    )
    very_small_text_threshold: float = Field(
        default=4.0, ge=0, description="Font size below which text is 'very small' (pt)."
    )
    safety_margin_mm: float = Field(
        default=3.0, ge=0, description="Safety margin from trim edge (mm)."
    )
    max_file_size_mb: float = Field(
        default=500.0, ge=0, description="Maximum file size warning (MB)."
    )
    barcode_min_dpi: float = Field(default=300.0, ge=0, description="Minimum barcode DPI.")
    barcode_min_grade: str = Field(default="C", description="Minimum barcode grade (A/B/C/D/F).")
    barcode_quiet_zone_mm: float = Field(default=2.5, ge=0, description="Barcode quiet zone in mm.")
    barcode_min_contrast: float = Field(
        default=0.7, ge=0, le=1.0, description="Minimum barcode symbol contrast (0.0-1.0)."
    )

    # Color management thresholds
    target_output_condition: str = Field(
        default="",
        description="Target output condition for gamut checking (e.g., 'fogra39_coated').",
    )
    gamut_check: bool = Field(
        default=False, description="Enable gamut boundary checking against target condition."
    )
    epm_mode: bool = Field(
        default=False, description="Enable HP Indigo EPM (CMY-only) readiness checks."
    )
    ecg_mode: bool = Field(
        default=False, description="Enable Extended Gamut (CMYKOGV) readiness checks."
    )
    cmy_tac_threshold: float = Field(
        default=240.0, ge=0, description="TAC threshold for CMY-only (EPM) workflows (%)."
    )
    rich_black_c: float = Field(
        default=60.0, ge=0, le=100, description="Target Cyan component for rich black (%)."
    )
    rich_black_m: float = Field(
        default=40.0, ge=0, le=100, description="Target Magenta component for rich black (%)."
    )
    rich_black_y: float = Field(
        default=40.0, ge=0, le=100, description="Target Yellow component for rich black (%)."
    )
    rich_black_k: float = Field(
        default=100.0, ge=0, le=100, description="Target Key component for rich black (%)."
    )
    spot_color_delta_e_warning: float = Field(
        default=5.0, ge=0, description="Delta-E 2000 threshold for spot color fallback warning."
    )
    spot_color_delta_e_advisory: float = Field(
        default=2.0, ge=0, description="Delta-E 2000 threshold for spot color fallback advisory."
    )
    min_printing_dot: float = Field(
        default=2.0, ge=0, le=100, description="Minimum printing dot percentage (scum dot risk)."
    )
    ecg_tac_limit: float = Field(
        default=350.0, ge=0, description="TAC limit for ECG/CMYKOGV workflows (FOGRA55)."
    )
    ecg_delta_e_excellent: float = Field(
        default=2.0, ge=0, description="Delta-E 2000 for excellent ECG spot achievability."
    )
    ecg_delta_e_good: float = Field(
        default=3.0, ge=0, description="Delta-E 2000 for good ECG spot achievability."
    )
    ecg_delta_e_acceptable: float = Field(
        default=5.0, ge=0, description="Delta-E 2000 for acceptable ECG spot achievability."
    )
    ecg_max_ink_per_channel: float = Field(
        default=0.95,
        ge=0,
        le=1.0,
        description="Maximum ink per individual channel for ECG workflows (0.0-1.0).",
    )
    epm_toner_limit: float = Field(
        default=280.0,
        ge=0,
        description="Total toner area coverage limit for EPM digital devices (%).",
    )
    epm_min_line_weight: float = Field(
        default=0.35, ge=0, description="Minimum line weight for digital press output (pt)."
    )
    color_score_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "color_spaces": 25.0,
            "ink_coverage": 25.0,
            "profiles": 20.0,
            "spot_colors": 15.0,
            "overprint": 15.0,
        },
        description="Weights for Color Quality Score categories (must sum to 100).",
    )


class AIFeatureConfig(BaseModel):
    """Configuration for AI-powered inspections within a Preflight Profile."""

    enabled: bool = Field(default=False, description="Enable AI inspections for this profile.")
    categories: list[str] = Field(
        default_factory=lambda: ["all"],
        description='AI categories to enable (e.g., ["barcode_detection", "regulatory_compliance"] or ["all"]).',
    )
    features: list[str] = Field(
        default_factory=list,
        description="Specific AI feature slugs to enable (overrides categories if non-empty).",
    )
    language_for_reports: str = Field(
        default="en",
        description="ISO 639-1 language code for AI-generated report text.",
    )


class ColorConfig(BaseModel):
    """Per-request color configuration overrides."""

    target_condition: str = Field(
        default="", description="Target output condition (overrides threshold)."
    )
    tac_threshold: float | None = Field(
        default=None, ge=0, description="TAC threshold override (%)."
    )
    gamut_check: bool | None = Field(
        default=None, description="Enable/disable gamut checking override."
    )
    epm_mode: bool | None = Field(default=None, description="Enable/disable EPM mode override.")


class PreflightProfile(BaseModel):
    """A complete preflight configuration profile.

    Preflight Profiles configure the preflight pipeline: which checks run,
    what thresholds to use, and whether conformance validation applies.
    """

    name: str = Field(description="Human-readable profile name.")
    description: str = Field(default="", description="Profile description.")
    version: str = Field(default="1.0", description="Schema version.")
    conformance: str | None = Field(
        default=None,
        description='Conformance standard to validate ("pdfx4" or None).',
    )
    workflow: str = Field(
        default="CMYK",
        description='Target workflow ("CMYK", "RGB", or "auto").',
    )
    checks: CheckConfig = Field(default_factory=CheckConfig)
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    ai: AIFeatureConfig = Field(default_factory=AIFeatureConfig)
    color: ColorConfig = Field(default_factory=ColorConfig)

    def is_check_enabled(self, check_id: str) -> bool:
        """Determine if a check ID is enabled by this profile."""
        import fnmatch

        # Disabled takes precedence
        for pattern in self.checks.disabled:
            if fnmatch.fnmatch(check_id, pattern):
                return False

        # Check if explicitly ignored via severity override
        if self.checks.severity_overrides.get(check_id) == "ignore":
            return False

        # Must match at least one enabled pattern
        return any(fnmatch.fnmatch(check_id, pattern) for pattern in self.checks.enabled)

    def get_severity_override(self, check_id: str) -> str | None:
        """Get severity override for a check, or None if no override."""
        return self.checks.severity_overrides.get(check_id)
