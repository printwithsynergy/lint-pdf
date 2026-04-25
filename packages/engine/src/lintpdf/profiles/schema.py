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

    # PDF version range — T1-CMP02 / LPDF_DOC_009
    min_pdf_version: str | None = Field(
        default=None,
        description=(
            "Lowest acceptable PDF header version (e.g. '1.6' for PDF/X-4). "
            "Absent means no lower bound. Fires LPDF_DOC_009 below this."
        ),
    )
    max_pdf_version: str | None = Field(
        default=None,
        description=(
            "Highest acceptable PDF header version (e.g. '1.4' for PDF/X-1a-2003). "
            "Absent means no upper bound. Fires LPDF_DOC_009 above this."
        ),
    )

    # Expected page size — T1-STR04 / LPDF_BOX_010. Compare the page's
    # effective trim/media dimensions against the tenant's declared
    # target product size. Either both dims must be set together, or
    # the check is disabled. Tolerance defaults to 0.5 mm.
    expected_page_width_mm: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Expected page width in mm (measured against effective_width_mm, "
            "which respects rotation and UserUnit). Pair with "
            "expected_page_height_mm. Absent → LPDF_BOX_010 disabled."
        ),
    )
    expected_page_height_mm: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Expected page height in mm. Pair with expected_page_width_mm. "
            "Absent → LPDF_BOX_010 disabled."
        ),
    )
    expected_page_size_tolerance_mm: float = Field(
        default=0.5,
        ge=0,
        description=(
            "Tolerance in mm when comparing actual vs expected page size. "
            "0.5mm matches PitStop's default."
        ),
    )

    # T3-D04 — maximum acceptable bleed past the dieline polygon. When
    # absent the LPDF_DIE_EXCESSIVE_BLEED check silently no-ops.
    max_bleed_mm: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Maximum bleed extent past the dieline polygon in mm. Artwork "
            "extending further than this triggers LPDF_DIE_EXCESSIVE_BLEED. "
            "Typical range: 5-15mm. Absent disables the check."
        ),
    )

    # T3-D08 — minimum dieline feature size + segment length thresholds
    # (cutter-resolution gate).
    min_dieline_feature_mm: float = Field(
        default=1.0,
        ge=0,
        description=(
            "Minimum dieline polygon width / height in mm. Polygons below "
            "this fire LPDF_DIE_TOO_SMALL (cutter blade can't track tiny "
            "features cleanly). Default 1.0mm matches cardstock norms."
        ),
    )
    min_dieline_segment_length_mm: float = Field(
        default=1.0,
        ge=0,
        description=(
            "Minimum dieline polygon perimeter in mm. Polygons below this "
            "fire LPDF_DIE_TOO_SMALL. Default 1.0mm matches cardstock "
            "norms."
        ),
    )

    # T3-D09 — minimum white-underprint coverage of the dieline area.
    # 0 disables the check; default 0.95 = 95% coverage required.
    white_coverage_min: float = Field(
        default=0.95,
        ge=0,
        le=1.0,
        description=(
            "Minimum fraction (0-1) of the dieline area that must be "
            "covered by White / OpaqueWhite spots. Below this triggers "
            "LPDF_DIE_WHITE_GAP. 0 disables the check."
        ),
    )

    # T3-D07 — minimum clearance from text bbox to fold/crease line.
    # 0 disables the check; default 3.0mm.
    text_to_fold_distance_mm: float = Field(
        default=3.0,
        ge=0,
        description=(
            "Minimum clearance (mm) from any text bbox to a fold / "
            "crease line. Below this triggers LPDF_TEXT_NEAR_FOLD. "
            "0 disables the check."
        ),
    )

    # T3-D12 — target substrate. Enables substrate-aware TAC advisory.
    substrate: str | None = Field(
        default=None,
        description=(
            "Target substrate for this profile. One of: uncoated_offset, "
            "coated_offset, newsprint, digital, flexo, gravure, "
            "large_format. Absent → LPDF_INK_SUBSTRATE advisory is "
            "disabled."
        ),
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


class ViewerConfig(BaseModel):
    """Viewer feature toggles and defaults — stored on BrandProfile.viewer_config."""

    # Feature toggles
    enable_separations: bool = Field(
        default=True, description="Show ink separation channel toggling."
    )
    enable_tac_heatmap: bool = Field(default=True, description="Show TAC heatmap overlay toggle.")
    enable_annotations: bool = Field(default=True, description="Show annotation tools.")
    enable_measurement: bool = Field(default=True, description="Show densitometer and ruler tools.")
    enable_comparison: bool = Field(default=True, description="Show file comparison (A/B) mode.")
    enable_layers: bool = Field(default=True, description="Show PDF layer (OCG) toggling.")
    enable_findings_panel: bool = Field(default=True, description="Show findings side panel.")
    enable_page_thumbnails: bool = Field(default=True, description="Show page thumbnail navigator.")
    enable_zoom: bool = Field(default=True, description="Show zoom controls.")
    enable_download: bool = Field(default=True, description="Show download buttons.")
    enable_html_report_link: bool = Field(default=True, description="Show HTML report link.")

    # Verdict mode
    verdict_mode: str = Field(
        default="auto",
        description='Verdict mode: "auto" (from preflight), "manual" (user pass/fail), "disabled".',
    )

    # Defaults
    default_zoom: int = Field(default=100, ge=25, le=400, description="Default zoom percentage.")
    default_dpi: int = Field(default=150, ge=72, le=600, description="Default tile DPI.")
    default_tac_limit: float = Field(
        default=300.0, ge=100, le=500, description="Default TAC threshold (%)."
    )

    # Branding overrides (inherits from BrandProfile if not set)
    viewer_logo_url: str | None = Field(default=None, description="Override brand logo for viewer.")
    viewer_accent_color: str | None = Field(
        default=None, description="Override accent color for viewer."
    )
    toolbar_position: str = Field(default="top", description='Toolbar position: "top" or "bottom".')
    dark_mode: bool = Field(default=False, description="Enable dark mode for viewer.")


class ReportConfig(BaseModel):
    """Report generation configuration within a preflight profile."""

    default_detail_level: str = Field(
        default="standard",
        description='Default report detail level ("executive", "standard", "comprehensive").',
    )
    max_screenshot_pages: int = Field(
        default=30, ge=0, description="Max pages to render annotated screenshots for."
    )
    screenshot_dpi: int = Field(
        default=150, ge=72, le=300, description="DPI for page screenshot rendering."
    )
    top_findings_limit: int = Field(
        default=10, ge=1, le=50, description="Max findings shown in executive summary."
    )


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
    report: ReportConfig = Field(default_factory=ReportConfig)

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
