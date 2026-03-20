"""Voyage Plan schema - configurable preflight profile.

A Voyage Plan defines which checks to run, severity overrides,
threshold configuration, and optional conformance standard.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CheckConfig(BaseModel):
    """Controls which checks are enabled and severity overrides."""

    enabled: list[str] = Field(
        default_factory=lambda: ["GRD_*", "PDFX4-*"],
        description="Check ID patterns to enable (glob-style). Default: all.",
    )
    disabled: list[str] = Field(
        default_factory=list,
        description="Check ID patterns to disable (takes precedence over enabled).",
    )
    severity_overrides: dict[str, str] = Field(
        default_factory=dict,
        description='Map of check ID to severity override (e.g. {"GRD_IMG_002": "ignore"}).',
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


class AIFeatureConfig(BaseModel):
    """Configuration for AI-powered inspections within a Voyage Plan."""

    enabled: bool = Field(default=False, description="Enable AI inspections for this voyage plan.")
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


class VoyagePlan(BaseModel):
    """A complete preflight configuration profile.

    Voyage Plans configure the preflight pipeline: which checks run,
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

    def is_check_enabled(self, check_id: str) -> bool:
        """Determine if a check ID is enabled by this voyage plan."""
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
