"""GamutAnalyzer — gamut boundary checking against target output conditions.

Processes ColorChangedEvent events and checks color values against
precomputed gamut boundaries to detect out-of-gamut colors.

Check IDs:
    GRD_GAMUT_001 — Per-object gamut check
    GRD_GAMUT_002 — Gamut volume comparison
    GRD_GAMUT_003 — Out-of-gamut summary
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity
from grounded.profiles.icc.profile_manager import get_gamut_boundary

if TYPE_CHECKING:
    from grounded.profiles.icc.gamut_boundary import GamutBoundary
    from grounded.semantic.events import ColorChangedEvent, ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# sRGB to XYZ D65 matrix (IEC 61966-2-1)
_SRGB_TO_XYZ = [
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
]

# D65 white point
_D65_XN = 0.95047
_D65_YN = 1.00000
_D65_ZN = 1.08883

# CMYK color space identifiers
_CMYK_SPACES = frozenset({"DeviceCMYK", "CMYK"})

# RGB color space identifiers
_RGB_SPACES = frozenset({"DeviceRGB", "RGB", "CalRGB"})


def _srgb_linearize(v: float) -> float:
    """Linearize an sRGB component (0-1 range)."""
    if v <= 0.04045:
        return v / 12.92
    return ((v + 0.055) / 1.055) ** 2.4


def _lab_f(t: float) -> float:
    """CIE Lab forward transform helper."""
    delta = 6.0 / 29.0
    if t > delta**3:
        return t ** (1.0 / 3.0)
    return t / (3.0 * delta**2) + 4.0 / 29.0


def srgb_to_lab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert sRGB (0-1) to CIELab D65.

    Uses the standard sRGB linearization and D65 white point.
    """
    # Linearize
    rl = _srgb_linearize(r)
    gl = _srgb_linearize(g)
    bl = _srgb_linearize(b)

    # sRGB to XYZ
    x = _SRGB_TO_XYZ[0][0] * rl + _SRGB_TO_XYZ[0][1] * gl + _SRGB_TO_XYZ[0][2] * bl
    y = _SRGB_TO_XYZ[1][0] * rl + _SRGB_TO_XYZ[1][1] * gl + _SRGB_TO_XYZ[1][2] * bl
    z = _SRGB_TO_XYZ[2][0] * rl + _SRGB_TO_XYZ[2][1] * gl + _SRGB_TO_XYZ[2][2] * bl

    # XYZ to Lab
    fx = _lab_f(x / _D65_XN)
    fy = _lab_f(y / _D65_YN)
    fz = _lab_f(z / _D65_ZN)

    l_star = 116.0 * fy - 16.0
    a_star = 500.0 * (fx - fy)
    b_star = 200.0 * (fy - fz)

    return (l_star, a_star, b_star)


class GamutAnalyzer(BaseAnalyzer):
    """Analyzer for gamut boundary checking against target output conditions.

    Args:
        target_condition: Condition slug from conditions.json
            (e.g., "fogra39_coated", "gracol2006_coated").
            If empty, gamut checking is skipped with an advisory.
    """

    def __init__(self, target_condition: str = "") -> None:
        self.target_condition = target_condition

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze color events for gamut compliance."""
        findings: list[Finding] = []

        # Load gamut boundary
        boundary: GamutBoundary | None = None
        if self.target_condition:
            boundary = get_gamut_boundary(self.target_condition)

        # GRD_GAMUT_001 — Per-object gamut check
        findings.extend(self._check_per_object_gamut(events, boundary))

        # GRD_GAMUT_002 — Gamut volume comparison
        findings.extend(self._check_gamut_volume(document, boundary))

        # GRD_GAMUT_003 — Out-of-gamut summary
        findings.extend(self._summarize_gamut_results(events, boundary))

        return findings

    def _check_per_object_gamut(
        self,
        events: list[ContentStreamEvent],
        boundary: GamutBoundary | None,
    ) -> list[Finding]:
        """Check each color change event against the gamut boundary (GRD_GAMUT_001)."""
        from grounded.semantic.events import ColorChangedEvent

        findings: list[Finding] = []

        if not self.target_condition:
            findings.append(
                Finding(
                    inspection_id="GRD_GAMUT_001",
                    severity=Severity.ADVISORY,
                    message="No target output condition specified; gamut checking skipped",
                    details={"target_condition": ""},
                )
            )
            return findings

        if boundary is None:
            findings.append(
                Finding(
                    inspection_id="GRD_GAMUT_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Gamut boundary not available for condition: {self.target_condition}"
                    ),
                    details={"target_condition": self.target_condition},
                )
            )
            return findings

        for event in events:
            if not isinstance(event, ColorChangedEvent):
                continue

            cs = event.color_space
            values = event.color_values

            if _is_rgb_space(cs) and len(values) >= 3:
                # Convert sRGB to Lab and test against boundary
                r, g, b = values[0], values[1], values[2]
                # Clamp to 0-1
                r = max(0.0, min(1.0, r))
                g = max(0.0, min(1.0, g))
                b = max(0.0, min(1.0, b))

                lab = srgb_to_lab(r, g, b)
                in_gamut = boundary.is_in_gamut(lab)

                if not in_gamut:
                    distance = boundary.distance_to_boundary(lab)
                    findings.append(
                        Finding(
                            inspection_id="GRD_GAMUT_001",
                            severity=Severity.SQUALL,
                            message=(
                                f"RGB color ({r:.2f}, {g:.2f}, {b:.2f}) is "
                                f"out of gamut for {boundary.condition_name} "
                                f"(Lab {lab[0]:.1f}, {lab[1]:.1f}, {lab[2]:.1f}, "
                                f"distance {distance:.2f})"
                            ),
                            page_num=event.page_num,
                            details={
                                "color_space": cs,
                                "rgb": [r, g, b],
                                "lab": list(lab),
                                "in_gamut": False,
                                "boundary_distance": round(distance, 4),
                                "condition": self.target_condition,
                                "stroking": event.stroking,
                            },
                            iso_clause="ISO 32000-2:2020 8.6",
                        )
                    )

            elif _is_cmyk_space(cs) and len(values) >= 4:
                # Precise Lab conversion for CMYK requires the actual ICC
                # profile transform; without it we can only advise.
                findings.append(
                    Finding(
                        inspection_id="GRD_GAMUT_001",
                        severity=Severity.ADVISORY,
                        message=(
                            f"CMYK color ({values[0]:.2f}, {values[1]:.2f}, "
                            f"{values[2]:.2f}, {values[3]:.2f}) — precise gamut "
                            f"check requires ICC profile transform"
                        ),
                        page_num=event.page_num,
                        details={
                            "color_space": cs,
                            "cmyk": list(values[:4]),
                            "condition": self.target_condition,
                            "stroking": event.stroking,
                            "note": "Lab conversion not available without ICC profile",
                        },
                        iso_clause="ISO 32000-2:2020 8.6",
                    )
                )

        return findings

    def _check_gamut_volume(
        self,
        document: SemanticDocument,
        boundary: GamutBoundary | None,
    ) -> list[Finding]:
        """Report gamut volume and compare source vs target (GRD_GAMUT_002)."""
        findings: list[Finding] = []

        if boundary is None:
            return findings

        details: dict[str, object] = {
            "condition": self.target_condition,
            "target_volume": round(boundary.volume, 2),
        }

        # Check if document has embedded ICC profile via output intents
        source_hint = None
        for oi in document.output_intents:
            cid = oi.get("OutputConditionIdentifier", "")
            if cid:
                source_hint = cid
                break

        if source_hint:
            details["source_condition_hint"] = source_hint

        findings.append(
            Finding(
                inspection_id="GRD_GAMUT_002",
                severity=Severity.ADVISORY,
                message=(
                    f"Target gamut volume for {boundary.condition_name}: "
                    f"{boundary.volume:.0f} Lab^3 units"
                ),
                details=details,
                iso_clause="ICC.1:2022 10",
            )
        )

        return findings

    def _summarize_gamut_results(
        self,
        events: list[ContentStreamEvent],
        boundary: GamutBoundary | None,
    ) -> list[Finding]:
        """Produce a summary finding of gamut check results (GRD_GAMUT_003)."""
        from grounded.semantic.events import ColorChangedEvent

        findings: list[Finding] = []

        if boundary is None:
            return findings

        total_rgb = 0
        out_of_gamut_rgb = 0
        total_cmyk = 0
        pages_with_oog: set[int] = set()

        for event in events:
            if not isinstance(event, ColorChangedEvent):
                continue

            cs = event.color_space
            values = event.color_values

            if _is_rgb_space(cs) and len(values) >= 3:
                total_rgb += 1
                r = max(0.0, min(1.0, values[0]))
                g = max(0.0, min(1.0, values[1]))
                b = max(0.0, min(1.0, values[2]))
                lab = srgb_to_lab(r, g, b)
                if not boundary.is_in_gamut(lab):
                    out_of_gamut_rgb += 1
                    pages_with_oog.add(event.page_num)

            elif _is_cmyk_space(cs) and len(values) >= 4:
                total_cmyk += 1

        findings.append(
            Finding(
                inspection_id="GRD_GAMUT_003",
                severity=Severity.ADVISORY,
                message=(
                    f"Gamut summary for {boundary.condition_name}: "
                    f"{out_of_gamut_rgb}/{total_rgb} RGB colors out of gamut, "
                    f"{total_cmyk} CMYK colors (profile transform needed)"
                ),
                details={
                    "condition": self.target_condition,
                    "total_rgb_colors": total_rgb,
                    "out_of_gamut_rgb": out_of_gamut_rgb,
                    "total_cmyk_colors": total_cmyk,
                    "pages_with_out_of_gamut": sorted(pages_with_oog),
                },
                iso_clause="ICC.1:2022 10",
            )
        )

        return findings


def _is_rgb_space(cs: str) -> bool:
    """Check if a color space name indicates RGB."""
    upper = cs.upper()
    return upper in {"DEVICERGB", "RGB", "CALRGB"} or "RGB" in upper


def _is_cmyk_space(cs: str) -> bool:
    """Check if a color space name indicates CMYK."""
    upper = cs.upper()
    return upper in {"DEVICECMYK", "CMYK"} or "CMYK" in upper
