"""Color Quality Score — 0-100 weighted composite score for PDF color readiness.

This score aggregates findings from all color-related analyzers into a single
quality metric. No competitor offers this.

Score interpretation:
    90-100: Excellent — press-ready with confidence
    75-89:  Good — minor issues, likely printable
    50-74:  Fair — review needed before production
    25-49:  Poor — significant color issues
    0-24:   Critical — not suitable for production
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from grounded.analyzers.finding import Finding, Severity


@dataclass(frozen=True)
class ColorQualityScore:
    """Result of color quality score computation."""

    score: float  # 0-100
    grade: str  # "Excellent", "Good", "Fair", "Poor", "Critical"
    breakdown: dict[str, float]  # category -> category_score
    deductions: list[dict[str, Any]]  # individual deduction details
    critical_floor: float | None  # if a floor was applied, the floor value


# Deduction points per check ID pattern
_CRITICAL_FLOORS: dict[str, float] = {
    # Wrong color space entirely (RGB in CMYK workflow)
    "GRD_COLOR_013": 20.0,
    # Missing output intent
    "GRD_COLOR_006": 25.0,
    # Corrupt ICC profiles
    "GRD_ICC_003": 30.0,
    # Invalid ICC profile structure
    "GRD_ICC_001": 30.0,
}

_MAJOR_DEDUCTIONS: dict[str, float] = {
    # TAC exceeding threshold
    "GRD_COLOR_004": 10.0,
    # Out-of-gamut objects
    "GRD_GAMUT_001": 8.0,
    # Spot color inconsistencies
    "GRD_SPOT_001": 7.0,  # only for SQUALL severity
    # Spot color naming issues
    "GRD_SPOT_003": 5.0,
    # DeviceN structural errors
    "GRD_SPOT_004": 10.0,
    # Missing ICC on ICCBased objects
    "GRD_ICC_003": 8.0,
}

_MODERATE_DEDUCTIONS: dict[str, float] = {
    # Overprint issues
    "GRD_OVER_001": 3.0,
    "GRD_OVER_002": 3.0,
    "GRD_OVER_003": 2.0,
    "GRD_OVER_004": 5.0,
    "GRD_OVER_006": 5.0,
    "GRD_OVER_008": 5.0,
    # Rich black issues
    "GRD_ADV_005": 3.0,
    "GRD_COLOR_008": 3.0,
    # Black generation inconsistency
    "GRD_ADV_001": 2.0,
    # Device-dependent color spaces
    "GRD_COLOR_015": 2.0,
    "GRD_COLOR_002": 3.0,
}

_MINOR_DEDUCTIONS: dict[str, float] = {
    # TAC approaching limit (handled via GRD_INK_001 advisory)
    "GRD_INK_001": 1.0,
    # Non-standard spot naming
    "GRD_SPOT_002": 0.5,
    # Trapping risk
    "GRD_ADV_003": 1.5,
    # Ink channel count advisory
    "GRD_INK_003": 0.5,
    # Color space inventory (informational, minor)
    "GRD_COLOR_014": 0.0,
}

# Category mapping for breakdown
_CHECK_CATEGORIES: dict[str, str] = {
    "GRD_COLOR_": "color_spaces",
    "GRD_ICC_": "profiles",
    "GRD_SPOT_": "spot_colors",
    "GRD_OVER_": "overprint",
    "GRD_INK_": "ink_coverage",
    "GRD_ADV_": "ink_coverage",
    "GRD_GAMUT_": "profiles",
    "GRD_STD_": "color_spaces",
    "GRD_ECG_": "color_spaces",
    "GRD_EPM_": "ink_coverage",
}


def _get_category(check_id: str) -> str:
    """Map a check ID to its score category."""
    for prefix, category in _CHECK_CATEGORIES.items():
        if check_id.startswith(prefix):
            return category
    return "color_spaces"  # default


def _get_grade(score: float) -> str:
    """Convert numeric score to grade label."""
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 50:
        return "Fair"
    if score >= 25:
        return "Poor"
    return "Critical"


def compute_color_quality_score(
    findings: list[Finding],
    weights: dict[str, float] | None = None,
) -> ColorQualityScore:
    """Compute the Color Quality Score from color-related findings.

    Args:
        findings: All findings from the preflight run (will be filtered to color-related).
        weights: Optional category weights (must sum to 100). Keys:
            color_spaces, ink_coverage, profiles, spot_colors, overprint.

    Returns:
        ColorQualityScore with score, grade, breakdown, and deduction details.
    """
    if weights is None:
        weights = {
            "color_spaces": 25.0,
            "ink_coverage": 25.0,
            "profiles": 20.0,
            "spot_colors": 15.0,
            "overprint": 15.0,
        }

    # Filter to color-related findings only
    color_prefixes = tuple(_CHECK_CATEGORIES.keys())
    color_findings = [f for f in findings if f.inspection_id.startswith(color_prefixes)]

    if not color_findings:
        # No color findings = perfect score
        return ColorQualityScore(
            score=100.0,
            grade="Excellent",
            breakdown={k: weights[k] for k in weights},
            deductions=[],
            critical_floor=None,
        )

    # Track deductions per category
    category_deductions: dict[str, float] = {k: 0.0 for k in weights}
    deduction_details: list[dict[str, Any]] = []
    critical_floor: float | None = None

    # Apply deductions
    seen_checks: set[str] = set()
    for finding in color_findings:
        check_id = finding.inspection_id
        category = _get_category(check_id)

        # Critical floors (apply worst floor)
        if check_id in _CRITICAL_FLOORS and finding.severity == Severity.AGROUND:
            floor = _CRITICAL_FLOORS[check_id]
            if critical_floor is None or floor < critical_floor:
                critical_floor = floor

        # Only deduct once per unique check ID (avoid double-counting
        # multiple instances of same check)
        if check_id in seen_checks:
            continue
        seen_checks.add(check_id)

        # Find deduction amount
        deduction = 0.0
        if check_id in _MAJOR_DEDUCTIONS and finding.severity in (
            Severity.AGROUND,
            Severity.SQUALL,
        ):
            deduction = _MAJOR_DEDUCTIONS[check_id]
        elif check_id in _MODERATE_DEDUCTIONS and finding.severity in (
            Severity.AGROUND,
            Severity.SQUALL,
        ):
            deduction = _MODERATE_DEDUCTIONS[check_id]
        elif check_id in _MINOR_DEDUCTIONS:
            deduction = _MINOR_DEDUCTIONS[check_id]

        if deduction > 0:
            category_deductions[category] = category_deductions.get(category, 0.0) + deduction
            deduction_details.append(
                {
                    "check_id": check_id,
                    "severity": finding.severity.value,
                    "deduction": deduction,
                    "category": category,
                    "message": finding.message,
                }
            )

    # Compute per-category scores
    breakdown: dict[str, float] = {}
    for cat, weight in weights.items():
        max_deduction = weight  # Category score can't go below 0
        actual_deduction = min(category_deductions.get(cat, 0.0), max_deduction)
        breakdown[cat] = round(weight - actual_deduction, 1)

    # Total score
    score = sum(breakdown.values())
    score = max(0.0, min(100.0, score))

    # Apply critical floor
    if critical_floor is not None:
        score = min(score, critical_floor)

    score = round(score, 1)

    return ColorQualityScore(
        score=score,
        grade=_get_grade(score),
        breakdown=breakdown,
        deductions=deduction_details,
        critical_floor=critical_floor,
    )
