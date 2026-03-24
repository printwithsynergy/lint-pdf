"""EcgAnalyzer — Expanded Color Gamut (ECG / CMYKOGV) checks.

Validates PDF documents for ECG printing readiness by inspecting
DeviceN color spaces, spot color usage, 7-channel TAC, and ink build
constraints.

Check IDs:
    GRD_ECG_001 — ECG readiness assessment
    GRD_ECG_002 — Per-spot ECG achievability placeholder
    GRD_ECG_003 — 7-channel TAC verification
    GRD_ECG_004 — DeviceN colorant consistency for CMYKOGV
    GRD_ECG_005 — Max 3-ink build validation
    GRD_ECG_006 — Spot color convertible to ECG process
    GRD_ECG_007 — ECG color out of build range
    GRD_ECG_008 — Gray balance drift risk
    GRD_ECG_009 — Overinking in expanded gamut
    GRD_ECG_010 — Missing ECG characterization data
    GRD_ECG_011 — Non-uniform ink limits
    GRD_ECG_012 — Gamut boundary mapping required
    GRD_ECG_013 — K-only text in ECG
    GRD_ECG_014 — Rich black recipe for ECG
    GRD_ECG_015 — Trap zone width recommendation
    GRD_ECG_016 — ECG profile ICC version
    GRD_ECG_017 — Multicolor DeviceN ordering
    GRD_ECG_018 — Total ink limit per channel
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Optional numpy for gamut boundary computation
try:
    import numpy as _np

    _HAS_NUMPY = True
except ImportError:
    _np = None
    _HAS_NUMPY = False

# ── FOGRA55 gamut boundary helpers ──────────────────────────────────

# Representative FOGRA55 ECG gamut boundary points in CIE Lab.
# These are the approximate outer-gamut vertices of a CMYKOGV color space
# under the FOGRA55 characterization (ISO 12647-2:2013 supplement).
_FOGRA55_GAMUT_BOUNDARY_LAB: list[tuple[float, float, float]] = [
    # (L*, a*, b*)  — key anchor points around the gamut hull
    (97.0, -1.0, 3.0),  # paper white
    (0.0, 0.0, 0.0),  # solid K
    (55.0, -38.0, -43.0),  # solid Cyan
    (47.0, 74.0, -5.0),  # solid Magenta
    (89.0, -5.0, 93.0),  # solid Yellow
    (62.0, 55.0, 68.0),  # solid Orange
    (50.0, -70.0, 28.0),  # solid Green
    (24.0, 22.0, -46.0),  # solid Violet
    (30.0, 50.0, -13.0),  # Magenta+K deep
    (39.0, -35.0, -30.0),  # Cyan+K deep
    (78.0, -60.0, 75.0),  # Yellow+Green
    (74.0, 30.0, 82.0),  # Yellow+Orange
    (35.0, 15.0, -50.0),  # Violet+K
    (65.0, 60.0, 40.0),  # Orange+Magenta
    (45.0, -55.0, -10.0),  # Cyan+Green
    (16.0, 0.0, 0.0),  # near-K
]


def _delta_e_2000(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    """Compute CIE Delta-E 2000 between two Lab colors (simplified).

    Implements the CIEDE2000 formula per CIE 142:2001.
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    Lbar = (L1 + L2) / 2.0
    C1 = math.sqrt(a1 * a1 + b1 * b1)
    C2 = math.sqrt(a2 * a2 + b2 * b2)
    Cbar = (C1 + C2) / 2.0

    Cbar7 = Cbar**7
    G = 0.5 * (1.0 - math.sqrt(Cbar7 / (Cbar7 + 25.0**7)))
    a1p = a1 * (1.0 + G)
    a2p = a2 * (1.0 + G)

    C1p = math.sqrt(a1p * a1p + b1 * b1)
    C2p = math.sqrt(a2p * a2p + b2 * b2)
    Cbarp = (C1p + C2p) / 2.0

    h1p = math.degrees(math.atan2(b1, a1p)) % 360.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360.0

    if abs(h1p - h2p) <= 180.0:
        Hbarp = (h1p + h2p) / 2.0
    elif h1p + h2p < 360.0:
        Hbarp = (h1p + h2p + 360.0) / 2.0
    else:
        Hbarp = (h1p + h2p - 360.0) / 2.0

    T = (
        1.0
        - 0.17 * math.cos(math.radians(Hbarp - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * Hbarp))
        + 0.32 * math.cos(math.radians(3.0 * Hbarp + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * Hbarp - 63.0))
    )

    if abs(h2p - h1p) <= 180.0:
        dhp = h2p - h1p
    elif h2p - h1p > 180.0:
        dhp = h2p - h1p - 360.0
    else:
        dhp = h2p - h1p + 360.0

    dLp = L2 - L1
    dCp = C2p - C1p
    dHp = 2.0 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2.0))

    SL = 1.0 + 0.015 * (Lbar - 50.0) ** 2 / math.sqrt(20.0 + (Lbar - 50.0) ** 2)
    SC = 1.0 + 0.045 * Cbarp
    SH = 1.0 + 0.015 * Cbarp * T

    Cbarp7 = Cbarp**7
    RC = 2.0 * math.sqrt(Cbarp7 / (Cbarp7 + 25.0**7))
    dtheta = 30.0 * math.exp(-(((Hbarp - 275.0) / 25.0) ** 2))
    RT = -math.sin(2.0 * math.radians(dtheta)) * RC

    dE = math.sqrt(
        (dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH)
    )
    return dE


def _distance_to_fogra55_gamut(lab: tuple[float, float, float]) -> float:
    """Compute minimum Delta-E 2000 distance from a Lab color to the FOGRA55 gamut boundary."""
    min_de = float("inf")
    for boundary_lab in _FOGRA55_GAMUT_BOUNDARY_LAB:
        de = _delta_e_2000(lab, boundary_lab)
        if de < min_de:
            min_de = de
    return min_de


# Common spot color name → approximate CIE Lab mapping
_SPOT_NAME_TO_LAB: dict[str, tuple[float, float, float]] = {
    "pantone reflex blue": (22.0, 13.0, -59.0),
    "reflex blue": (22.0, 13.0, -59.0),
    "pantone warm red": (49.0, 66.0, 48.0),
    "warm red": (49.0, 66.0, 48.0),
    "pantone rubine red": (40.0, 68.0, -2.0),
    "rubine red": (40.0, 68.0, -2.0),
    "pantone rhodamine red": (52.0, 70.0, -18.0),
    "rhodamine red": (52.0, 70.0, -18.0),
    "pantone purple": (28.0, 46.0, -48.0),
    "purple": (28.0, 46.0, -48.0),
    "pantone green": (55.0, -60.0, 26.0),
    "green": (55.0, -60.0, 26.0),
    "pantone process blue": (50.0, -20.0, -50.0),
    "process blue": (50.0, -20.0, -50.0),
    "pantone orange 021": (62.0, 55.0, 72.0),
    "orange 021": (62.0, 55.0, 72.0),
    "pantone yellow": (89.0, -5.0, 93.0),
    "pantone yellow 012": (90.0, -2.0, 88.0),
    "pantone black": (3.0, 0.0, 0.0),
    "pantone cool gray 11": (42.0, 0.0, -1.0),
    "pantone cool gray 7": (58.0, 0.0, -1.0),
    "pantone warm gray 11": (42.0, 2.0, 5.0),
    "pantone 485": (47.0, 68.0, 54.0),
    "pantone 186": (42.0, 64.0, 30.0),
    "pantone 032": (47.0, 70.0, 48.0),
    "pantone 185": (46.0, 70.0, 36.0),
    "pantone 200": (36.0, 55.0, 24.0),
    "pantone 281": (14.0, 10.0, -40.0),
    "pantone 286": (26.0, 16.0, -58.0),
    "pantone 300": (38.0, -4.0, -50.0),
    "pantone 349": (33.0, -35.0, 15.0),
    "pantone 354": (48.0, -58.0, 35.0),
    "pantone 376": (68.0, -40.0, 65.0),
    "pantone 1795": (47.0, 65.0, 45.0),
    "pantone 2935": (30.0, 6.0, -60.0),
    "pantone 7462": (28.0, -8.0, -32.0),
    "pantone 7687": (22.0, 20.0, -52.0),
    "pantone 877": (72.0, 0.0, 2.0),  # metallic silver approx
    "pantone 871": (55.0, 5.0, 35.0),  # metallic gold approx
    "gold": (55.0, 5.0, 35.0),
    "silver": (72.0, 0.0, 2.0),
    "red": (53.0, 80.0, 67.0),
    "blue": (32.0, 79.0, -108.0),
    "orange": (62.0, 55.0, 72.0),
    "violet": (24.0, 22.0, -46.0),
    "spot1": None,  # unmapped generic
    "spot2": None,
}


def _spot_name_to_lab(name: str) -> tuple[float, float, float] | None:
    """Map a spot color name to approximate CIE Lab values."""
    key = name.strip().lower()
    # Direct match
    result = _SPOT_NAME_TO_LAB.get(key)
    if result is not None:
        return result
    # Try prefix match (e.g. "PANTONE 485 C" → "pantone 485")
    for known, lab in _SPOT_NAME_TO_LAB.items():
        if lab is not None and key.startswith(known):
            return lab
    return None


# Expected CMYKOGV colorant names (case-insensitive matching)
_CMYKOGV_NAMES = frozenset(
    {
        "cyan",
        "magenta",
        "yellow",
        "black",
        "orange",
        "green",
        "violet",
    }
)

# Alternative CMYKOGV abbreviations
_CMYKOGV_ABBREVS = frozenset(
    {
        "c",
        "m",
        "y",
        "k",
        "o",
        "g",
        "v",
    }
)

# Threshold for significant ink coverage
_SIGNIFICANT_INK = 0.05  # 5%

# Spot colors that can be replaced by ECG process colors (Orange, Green, Violet)
_ECG_CONVERTIBLE_SPOTS = {
    "pantone orange 021": "orange",
    "pantone orange 021 c": "orange",
    "pantone orange 021 u": "orange",
    "pantone green": "green",
    "pantone green c": "green",
    "pantone green u": "green",
    "pantone violet": "violet",
    "pantone violet c": "violet",
    "pantone violet u": "violet",
    "pantone 021": "orange",
    "pantone 354": "green",
    "pantone 2685": "violet",
}

# Expected CMYKOGV ordering convention
_CMYKOGV_ORDER = ["cyan", "magenta", "yellow", "black", "orange", "green", "violet"]

# Gray balance threshold for ECG (high absolute values)
_ECG_GRAY_HIGH_THRESHOLD = 0.60  # 60%
_ECG_GRAY_TOLERANCE = 0.05  # 5%

# Rich black ECG recipe defaults
_ECG_RICH_BLACK_C = 0.60  # 60% Cyan
_ECG_RICH_BLACK_M = 0.40  # 40% Magenta
_ECG_RICH_BLACK_Y = 0.40  # 40% Yellow
_ECG_RICH_BLACK_K = 1.00  # 100% Black

# Trap zone minimum width (pt)
_ECG_TRAP_MIN_WIDTH = 0.5  # 0.5pt

# Small text threshold for K-only check (pt)
_ECG_SMALL_TEXT_THRESHOLD = 12.0


class EcgAnalyzer(BaseAnalyzer):
    """Analyzer for Expanded Color Gamut (ECG) printing readiness.

    Args:
        tac_limit: Maximum allowed 7-channel TAC percentage (default 300).
        ecg_tac_limit: ECG-specific overinking TAC threshold (default 350).
        ecg_max_ink_per_channel: Maximum ink per individual channel (default 0.95).
    """

    def __init__(
        self,
        tac_limit: float = 300.0,
        ecg_tac_limit: float = 350.0,
        ecg_max_ink_per_channel: float = 0.95,
    ) -> None:
        self.tac_limit = tac_limit
        self.ecg_tac_limit = ecg_tac_limit
        self.ecg_max_ink_per_channel = ecg_max_ink_per_channel

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze document for ECG readiness and compliance."""
        from lintpdf.semantic.events import (
            ColorChangedEvent,
            PathPaintingEvent,
            TextRenderedEvent,
        )

        findings: list[Finding] = []

        # Collect spot colors and DeviceN spaces from document pages
        spot_colors: dict[str, list[int]] = {}  # name -> pages
        devicen_spaces: list[dict[str, object]] = []  # info about each DeviceN space

        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                if cs.cs_type == "Separation" and cs.colorant_names:
                    for colorant in cs.colorant_names:
                        if colorant not in ("All", "None"):
                            if colorant not in spot_colors:
                                spot_colors[colorant] = []
                            if page.page_num not in spot_colors[colorant]:
                                spot_colors[colorant].append(page.page_num)
                elif cs.cs_type == "DeviceN" and cs.colorant_names:
                    colorant_list = [c for c in cs.colorant_names if c not in ("All", "None")]
                    devicen_spaces.append(
                        {
                            "cs_name": cs_name,
                            "colorants": colorant_list,
                            "components": cs.components,
                            "page_num": page.page_num,
                        }
                    )
                    for colorant in colorant_list:
                        if colorant not in spot_colors:
                            spot_colors[colorant] = []
                        if page.page_num not in spot_colors[colorant]:
                            spot_colors[colorant].append(page.page_num)

        # Collect DeviceN color values from events for TAC and ink build checks
        devicen_color_events: list[dict[str, object]] = []
        # Collect CMYK color events for gray balance and rich black checks
        cmyk_color_events: list[dict[str, object]] = []
        # Collect text events for K-only text check
        text_events: list[dict[str, object]] = []
        # Collect path events for trap zone width check
        path_events: list[dict[str, object]] = []

        for event in events:
            if isinstance(event, ColorChangedEvent):
                if event.color_space == "DeviceN" and len(event.color_values) > 4:
                    devicen_color_events.append(
                        {
                            "page_num": event.page_num,
                            "color_values": event.color_values,
                            "components": len(event.color_values),
                        }
                    )
                elif event.color_space == "DeviceCMYK" and len(event.color_values) == 4:
                    cmyk_color_events.append(
                        {
                            "page_num": event.page_num,
                            "color_values": event.color_values,
                        }
                    )
            elif isinstance(event, PathPaintingEvent):
                if event.fill and event.fill_color_space == "DeviceN":
                    vals = event.fill_color_values
                    if len(vals) > 4:
                        devicen_color_events.append(
                            {
                                "page_num": event.page_num,
                                "color_values": vals,
                                "components": len(vals),
                            }
                        )
                if event.stroke and event.stroke_color_space == "DeviceN":
                    vals = event.stroke_color_values
                    if len(vals) > 4:
                        devicen_color_events.append(
                            {
                                "page_num": event.page_num,
                                "color_values": vals,
                                "components": len(vals),
                            }
                        )
                if event.fill and event.fill_color_space == "DeviceCMYK":
                    vals = event.fill_color_values
                    if len(vals) == 4:
                        cmyk_color_events.append(
                            {
                                "page_num": event.page_num,
                                "color_values": vals,
                            }
                        )
                if event.stroke and event.stroke_color_space == "DeviceCMYK":
                    vals = event.stroke_color_values
                    if len(vals) == 4:
                        cmyk_color_events.append(
                            {
                                "page_num": event.page_num,
                                "color_values": vals,
                            }
                        )
                # Collect stroke width for trap zone check
                if event.stroke and hasattr(event, "line_width"):
                    path_events.append(
                        {
                            "page_num": event.page_num,
                            "line_width": event.line_width,
                        }
                    )
            elif isinstance(event, TextRenderedEvent):
                text_events.append(
                    {
                        "page_num": event.page_num,
                        "color_space": event.color_space,
                        "color_values": event.color_values,
                        "font_size": getattr(event, "font_size", None),
                    }
                )

        # GRD_ECG_001: ECG readiness assessment
        findings.extend(self._check_ecg_readiness(spot_colors, devicen_spaces))

        # GRD_ECG_002: Per-spot ECG achievability placeholder
        findings.extend(self._check_spot_achievability(spot_colors))

        # GRD_ECG_003: 7-channel TAC verification
        findings.extend(self._check_7channel_tac(devicen_color_events))

        # GRD_ECG_004: DeviceN colorant consistency for CMYKOGV
        findings.extend(self._check_colorant_consistency(devicen_spaces))

        # GRD_ECG_005: Max 3-ink build validation
        findings.extend(self._check_ink_build(devicen_color_events))

        # GRD_ECG_006: Spot color convertible to ECG process
        findings.extend(self._check_spot_convertible(spot_colors))

        # GRD_ECG_007: ECG color out of build range
        findings.extend(self._check_ecg_build_range(devicen_color_events))

        # GRD_ECG_008: Gray balance drift risk
        findings.extend(self._check_gray_balance_drift(cmyk_color_events))

        # GRD_ECG_009: Overinking in expanded gamut
        findings.extend(self._check_ecg_overinking(devicen_color_events))

        # GRD_ECG_010: Missing ECG characterization data
        findings.extend(self._check_ecg_characterization(document))

        # GRD_ECG_011: Non-uniform ink limits
        findings.extend(self._check_ink_channel_limits(devicen_color_events))

        # GRD_ECG_012: Gamut boundary mapping required
        findings.extend(self._check_gamut_mapping(spot_colors))

        # GRD_ECG_013: K-only text in ECG
        findings.extend(self._check_k_only_text(text_events))

        # GRD_ECG_014: Rich black recipe for ECG
        findings.extend(self._check_rich_black_ecg(cmyk_color_events))

        # GRD_ECG_015: Trap zone width recommendation
        findings.extend(self._check_trap_zone_width(path_events))

        # GRD_ECG_016: ECG profile ICC version
        findings.extend(self._check_icc_version(document))

        # GRD_ECG_017: Multicolor DeviceN ordering
        findings.extend(self._check_devicen_ordering(devicen_spaces))

        # GRD_ECG_018: Total ink limit per channel
        findings.extend(self._check_channel_ink_limit(devicen_color_events))

        return findings

    @staticmethod
    def _check_ecg_readiness(
        spot_colors: dict[str, list[int]],
        devicen_spaces: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_001: Assess ECG readiness."""
        findings: list[Finding] = []

        # Check for CMYKOGV-like DeviceN spaces
        cmykogv_spaces: list[dict[str, object]] = []
        for dn in devicen_spaces:
            colorants: list[str] = dn["colorants"]  # type: ignore[assignment]
            lower_names = {c.lower() for c in colorants}
            # Check if colorant set resembles CMYKOGV
            if len(colorants) >= 7 and lower_names & {"orange", "green", "violet"}:
                cmykogv_spaces.append(dn)

        has_spots = len(spot_colors) > 0
        has_cmykogv = len(cmykogv_spaces) > 0

        spot_list = sorted(spot_colors.keys())

        findings.append(
            Finding(
                inspection_id="GRD_ECG_001",
                severity=Severity.ADVISORY,
                message=(
                    f"ECG readiness: {len(spot_colors)} spot color(s) found, "
                    f"{len(cmykogv_spaces)} CMYKOGV-like DeviceN space(s) detected. "
                    f"{'File has ECG-appropriate structure.' if has_cmykogv else 'No CMYKOGV DeviceN structure found.'}"
                ),
                details={
                    "spot_color_count": len(spot_colors),
                    "spot_colors": spot_list,
                    "cmykogv_devicen_count": len(cmykogv_spaces),
                    "has_spots": has_spots,
                    "has_cmykogv_structure": has_cmykogv,
                },
            )
        )

        return findings

    @staticmethod
    def _check_spot_achievability(
        spot_colors: dict[str, list[int]],
    ) -> list[Finding]:
        """GRD_ECG_002: Per-spot ECG achievability via FOGRA55 gamut estimate.

        Estimates whether each spot color name can be reproduced within the
        FOGRA55 ECG (CMYKOGV) gamut by mapping common spot color names to
        approximate CIE Lab values and computing Delta-E 2000 distance to the
        nearest point in the FOGRA55 gamut boundary.
        """
        findings: list[Finding] = []

        for colorant, pages in sorted(spot_colors.items()):
            lab = _spot_name_to_lab(colorant)
            if lab is None:
                findings.append(
                    Finding(
                        inspection_id="GRD_ECG_002",
                        severity=Severity.ADVISORY,
                        message=(
                            f"ECG achievability: Spot color '{colorant}' could not be "
                            f"mapped to a Lab value for gamut testing "
                            f"(found on page(s) {pages}). "
                            f"Provide an ICC profile or Pantone reference for accurate analysis."
                        ),
                        details={
                            "colorant_name": colorant,
                            "pages": pages,
                            "status": "unmapped",
                        },
                    )
                )
                continue

            delta_e = _distance_to_fogra55_gamut(lab)

            if delta_e < 3.0:
                status = "achievable"
                severity = Severity.ADVISORY
                msg = (
                    f"ECG achievability: Spot color '{colorant}' is within FOGRA55 "
                    f"gamut (Delta-E 2000 = {delta_e:.1f}, page(s) {pages})"
                )
            elif delta_e < 6.0:
                status = "marginal"
                severity = Severity.ADVISORY
                msg = (
                    f"ECG achievability: Spot color '{colorant}' is marginally "
                    f"achievable in FOGRA55 gamut (Delta-E 2000 = {delta_e:.1f}, "
                    f"page(s) {pages}). Visual proofing recommended."
                )
            else:
                status = "not_achievable"
                severity = Severity.WARNING
                msg = (
                    f"ECG achievability: Spot color '{colorant}' is outside FOGRA55 "
                    f"gamut (Delta-E 2000 = {delta_e:.1f}, page(s) {pages}). "
                    f"This color cannot be faithfully reproduced in ECG printing."
                )

            findings.append(
                Finding(
                    inspection_id="GRD_ECG_002",
                    severity=severity,
                    message=msg,
                    details={
                        "colorant_name": colorant,
                        "pages": pages,
                        "lab": list(lab),
                        "delta_e_2000": round(delta_e, 2),
                        "status": status,
                    },
                )
            )

        return findings

    def _check_7channel_tac(
        self,
        devicen_color_events: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_003: 7-channel TAC verification."""
        findings: list[Finding] = []

        for event_info in devicen_color_events:
            color_values: tuple[float, ...] = event_info["color_values"]  # type: ignore[assignment]
            page_num: int = event_info["page_num"]  # type: ignore[assignment]
            tac = sum(color_values) * 100.0

            if tac > self.tac_limit:
                findings.append(
                    Finding(
                        inspection_id="GRD_ECG_003",
                        severity=Severity.WARNING,
                        message=(
                            f"ECG TAC {tac:.0f}% exceeds {self.tac_limit:.0f}% limit "
                            f"on page {page_num} "
                            f"({len(color_values)}-channel DeviceN)"
                        ),
                        page_num=page_num,
                        details={
                            "tac": tac,
                            "tac_limit": self.tac_limit,
                            "channels": len(color_values),
                            "color_values": list(color_values),
                        },
                    )
                )

        return findings

    @staticmethod
    def _check_colorant_consistency(
        devicen_spaces: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_004: DeviceN colorant consistency for CMYKOGV."""
        findings: list[Finding] = []

        seven_channel_spaces: list[dict[str, object]] = []

        for dn in devicen_spaces:
            colorants: list[str] = dn["colorants"]  # type: ignore[assignment]
            if len(colorants) == 7:
                seven_channel_spaces.append(dn)

        if not seven_channel_spaces:
            return findings

        # Inventory all 7-colorant DeviceN spaces
        for dn in seven_channel_spaces:
            colorants: list[str] = dn["colorants"]  # type: ignore[assignment]
            lower_names = {c.lower() for c in colorants}
            page_num: int = dn["page_num"]  # type: ignore[assignment]

            # Check against expected CMYKOGV names
            missing = _CMYKOGV_NAMES - lower_names
            unexpected = lower_names - _CMYKOGV_NAMES

            # Also check abbreviations
            if missing and lower_names & _CMYKOGV_ABBREVS:
                missing_abbrev = _CMYKOGV_ABBREVS - lower_names
                if len(missing_abbrev) < len(missing):
                    # Abbreviation naming convention — still report for awareness
                    findings.append(
                        Finding(
                            inspection_id="GRD_ECG_004",
                            severity=Severity.ADVISORY,
                            message=(
                                f"DeviceN 7-colorant space '{dn['cs_name']}' on page "
                                f"{page_num} uses abbreviated names: {colorants}"
                            ),
                            page_num=page_num,
                            details={
                                "cs_name": dn["cs_name"],
                                "colorants": colorants,
                                "naming_convention": "abbreviated",
                            },
                        )
                    )
                    continue

            if missing or unexpected:
                findings.append(
                    Finding(
                        inspection_id="GRD_ECG_004",
                        severity=Severity.WARNING,
                        message=(
                            f"DeviceN 7-colorant space '{dn['cs_name']}' on page "
                            f"{page_num} has inconsistent naming: {colorants}. "
                            f"{'Missing: ' + ', '.join(sorted(missing)) + '. ' if missing else ''}"
                            f"{'Unexpected: ' + ', '.join(sorted(unexpected)) + '.' if unexpected else ''}"
                        ),
                        page_num=page_num,
                        details={
                            "cs_name": dn["cs_name"],
                            "colorants": colorants,
                            "missing": sorted(missing),
                            "unexpected": sorted(unexpected),
                        },
                    )
                )
            else:
                findings.append(
                    Finding(
                        inspection_id="GRD_ECG_004",
                        severity=Severity.ADVISORY,
                        message=(
                            f"DeviceN 7-colorant space '{dn['cs_name']}' on page "
                            f"{page_num} has consistent CMYKOGV naming: {colorants}"
                        ),
                        page_num=page_num,
                        details={
                            "cs_name": dn["cs_name"],
                            "colorants": colorants,
                        },
                    )
                )

        return findings

    @staticmethod
    def _check_ink_build(
        devicen_color_events: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_005: Max 3-ink build validation."""
        findings: list[Finding] = []

        for event_info in devicen_color_events:
            color_values: tuple[float, ...] = event_info["color_values"]  # type: ignore[assignment]
            page_num: int = event_info["page_num"]  # type: ignore[assignment]

            # Count channels with significant ink
            active_inks = sum(1 for v in color_values if v > _SIGNIFICANT_INK)

            if active_inks > 3:
                findings.append(
                    Finding(
                        inspection_id="GRD_ECG_005",
                        severity=Severity.WARNING,
                        message=(
                            f"ECG ink build: {active_inks} active inks (>{_SIGNIFICANT_INK * 100:.0f}%) "
                            f"on page {page_num} exceeds 3-ink maximum for color stability"
                        ),
                        page_num=page_num,
                        details={
                            "active_inks": active_inks,
                            "max_inks": 3,
                            "ink_threshold": _SIGNIFICANT_INK,
                            "color_values": list(color_values),
                        },
                    )
                )

        return findings

    @staticmethod
    def _check_spot_convertible(
        spot_colors: dict[str, list[int]],
    ) -> list[Finding]:
        """GRD_ECG_006: Spot color convertible to ECG process."""
        findings: list[Finding] = []

        for colorant, pages in sorted(spot_colors.items()):
            lower_name = colorant.lower().strip()
            ecg_process = _ECG_CONVERTIBLE_SPOTS.get(lower_name)
            if ecg_process is not None:
                findings.append(
                    Finding(
                        inspection_id="GRD_ECG_006",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Spot color '{colorant}' could be replaced by ECG process "
                            f"color '{ecg_process.upper()}' on page(s) {pages}"
                        ),
                        details={
                            "colorant_name": colorant,
                            "ecg_process_replacement": ecg_process,
                            "pages": pages,
                        },
                    )
                )

        return findings

    @staticmethod
    def _check_ecg_build_range(
        devicen_color_events: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_007: ECG color out of build range."""
        findings: list[Finding] = []

        for event_info in devicen_color_events:
            color_values: tuple[float, ...] = event_info["color_values"]  # type: ignore[assignment]
            page_num: int = event_info["page_num"]  # type: ignore[assignment]
            tac = sum(color_values) * 100.0

            if tac > 400.0:
                findings.append(
                    Finding(
                        inspection_id="GRD_ECG_007",
                        severity=Severity.ERROR,
                        message=(
                            f"ECG color out of build range: CMYK+OGV TAC {tac:.0f}% "
                            f"exceeds maximum allowable 400% on page {page_num}"
                        ),
                        page_num=page_num,
                        details={
                            "tac": tac,
                            "max_ecg_tac": 400.0,
                            "channels": len(color_values),
                            "color_values": list(color_values),
                        },
                    )
                )

        return findings

    @staticmethod
    def _check_gray_balance_drift(
        cmyk_color_events: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_008: Gray balance drift risk."""
        findings: list[Finding] = []
        drift_count = 0
        drift_pages: set[int] = set()

        for event_info in cmyk_color_events:
            color_values: tuple[float, ...] = event_info["color_values"]  # type: ignore[assignment]
            page_num: int = event_info["page_num"]  # type: ignore[assignment]
            c, m, y, _k = color_values

            # Near-equal CMY with high absolute values
            if (
                c > _ECG_GRAY_HIGH_THRESHOLD
                and m > _ECG_GRAY_HIGH_THRESHOLD
                and y > _ECG_GRAY_HIGH_THRESHOLD
                and abs(c - m) <= _ECG_GRAY_TOLERANCE
                and abs(c - y) <= _ECG_GRAY_TOLERANCE
                and abs(m - y) <= _ECG_GRAY_TOLERANCE
            ):
                drift_count += 1
                drift_pages.add(page_num)

        if drift_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_ECG_008",
                    severity=Severity.WARNING,
                    message=(
                        f"ECG gray balance drift risk: {drift_count} object(s) with "
                        f"near-equal C/M/Y components above {_ECG_GRAY_HIGH_THRESHOLD * 100:.0f}% "
                        f"across {len(drift_pages)} page(s) may exhibit gray balance "
                        f"instability in ECG workflow"
                    ),
                    details={
                        "drift_count": drift_count,
                        "pages": sorted(drift_pages),
                        "gray_high_threshold": _ECG_GRAY_HIGH_THRESHOLD,
                        "gray_tolerance": _ECG_GRAY_TOLERANCE,
                    },
                )
            )

        return findings

    def _check_ecg_overinking(
        self,
        devicen_color_events: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_009: Overinking in expanded gamut."""
        findings: list[Finding] = []

        for event_info in devicen_color_events:
            color_values: tuple[float, ...] = event_info["color_values"]  # type: ignore[assignment]
            page_num: int = event_info["page_num"]  # type: ignore[assignment]
            tac = sum(color_values) * 100.0

            if tac > self.ecg_tac_limit:
                findings.append(
                    Finding(
                        inspection_id="GRD_ECG_009",
                        severity=Severity.WARNING,
                        message=(
                            f"ECG overinking: TAC {tac:.0f}% exceeds ECG threshold "
                            f"{self.ecg_tac_limit:.0f}% on page {page_num}"
                        ),
                        page_num=page_num,
                        details={
                            "tac": tac,
                            "ecg_tac_limit": self.ecg_tac_limit,
                            "channels": len(color_values),
                            "color_values": list(color_values),
                        },
                    )
                )

        return findings

    @staticmethod
    def _check_ecg_characterization(
        document: SemanticDocument,
    ) -> list[Finding]:
        """GRD_ECG_010: Missing ECG characterization data."""
        findings: list[Finding] = []

        # Check output intents for ECG-specific characterization references
        ecg_references = {"fogra55", "fogra59", "cgats21-2-ecg", "ecg"}
        has_ecg_characterization = False

        if hasattr(document, "output_intents"):
            for intent in document.output_intents:
                condition = getattr(intent, "output_condition", "") or ""
                info = getattr(intent, "info", "") or ""
                registry = getattr(intent, "registry_name", "") or ""
                combined = f"{condition} {info} {registry}".lower()
                if any(ref in combined for ref in ecg_references):
                    has_ecg_characterization = True
                    break

        if not has_ecg_characterization:
            findings.append(
                Finding(
                    inspection_id="GRD_ECG_010",
                    severity=Severity.WARNING,
                    message=(
                        "Missing ECG characterization data: no ECG-specific output "
                        "intent or characterization reference (e.g., FOGRA55) found "
                        "in document metadata"
                    ),
                    details={
                        "expected_references": sorted(ecg_references),
                        "has_output_intents": hasattr(document, "output_intents"),
                    },
                )
            )

        return findings

    def _check_ink_channel_limits(
        self,
        devicen_color_events: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_011: Non-uniform ink limits."""
        findings: list[Finding] = []

        for event_info in devicen_color_events:
            color_values: tuple[float, ...] = event_info["color_values"]  # type: ignore[assignment]
            page_num: int = event_info["page_num"]  # type: ignore[assignment]

            exceeded_channels: list[int] = []
            for i, val in enumerate(color_values):
                if val > self.ecg_max_ink_per_channel:
                    exceeded_channels.append(i)

            if exceeded_channels:
                findings.append(
                    Finding(
                        inspection_id="GRD_ECG_011",
                        severity=Severity.WARNING,
                        message=(
                            f"ECG ink channel limit exceeded: channel(s) "
                            f"{exceeded_channels} above "
                            f"{self.ecg_max_ink_per_channel * 100:.0f}% on page {page_num}"
                        ),
                        page_num=page_num,
                        details={
                            "exceeded_channels": exceeded_channels,
                            "max_ink_per_channel": self.ecg_max_ink_per_channel,
                            "color_values": list(color_values),
                        },
                    )
                )

        return findings

    @staticmethod
    def _check_gamut_mapping(
        spot_colors: dict[str, list[int]],
    ) -> list[Finding]:
        """GRD_ECG_012: Gamut boundary mapping required."""
        findings: list[Finding] = []

        # Spot colors not in the ECG convertible set likely need gamut mapping
        for colorant, pages in sorted(spot_colors.items()):
            lower_name = colorant.lower().strip()
            # Skip colors that are standard CMYKOGV or known convertible
            if lower_name in _CMYKOGV_NAMES or lower_name in _ECG_CONVERTIBLE_SPOTS:
                continue

            findings.append(
                Finding(
                    inspection_id="GRD_ECG_012",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Gamut boundary mapping required: spot color '{colorant}' "
                        f"on page(s) {pages} may be out of ECG gamut and would need "
                        f"gamut mapping for accurate reproduction"
                    ),
                    details={
                        "colorant_name": colorant,
                        "pages": pages,
                    },
                )
            )

        return findings

    @staticmethod
    def _check_k_only_text(
        text_events: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_013: K-only text in ECG."""
        findings: list[Finding] = []
        multi_ink_text_count = 0
        multi_ink_text_pages: set[int] = set()

        for event_info in text_events:
            color_space: str = event_info["color_space"]  # type: ignore[assignment]
            color_values: tuple[float, ...] = event_info["color_values"]  # type: ignore[assignment]
            page_num: int = event_info["page_num"]  # type: ignore[assignment]
            font_size = event_info.get("font_size")

            # Only check small text
            if font_size is not None and font_size > _ECG_SMALL_TEXT_THRESHOLD:
                continue

            if color_space == "DeviceCMYK" and len(color_values) == 4:
                c, m, y, k = color_values
                # Small text should use K-only, not multi-ink
                if k > 0 and (c > 0.01 or m > 0.01 or y > 0.01):
                    multi_ink_text_count += 1
                    multi_ink_text_pages.add(page_num)

        if multi_ink_text_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_ECG_013",
                    severity=Severity.WARNING,
                    message=(
                        f"ECG multi-ink small text: {multi_ink_text_count} text "
                        f"object(s) below {_ECG_SMALL_TEXT_THRESHOLD:.0f}pt use "
                        f"multi-ink instead of K-only across "
                        f"{len(multi_ink_text_pages)} page(s)"
                    ),
                    details={
                        "multi_ink_text_count": multi_ink_text_count,
                        "pages": sorted(multi_ink_text_pages),
                        "small_text_threshold": _ECG_SMALL_TEXT_THRESHOLD,
                    },
                    object_type="text",
                )
            )

        return findings

    @staticmethod
    def _check_rich_black_ecg(
        cmyk_color_events: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_014: Rich black recipe for ECG."""
        findings: list[Finding] = []
        bad_recipe_count = 0
        bad_recipe_pages: set[int] = set()

        for event_info in cmyk_color_events:
            color_values: tuple[float, ...] = event_info["color_values"]  # type: ignore[assignment]
            page_num: int = event_info["page_num"]  # type: ignore[assignment]
            c, m, y, k = color_values

            # Detect rich black (K=100% with CMY)
            if abs(k - 1.0) < 0.01 and (c > 0.01 or m > 0.01 or y > 0.01):
                # Check if recipe deviates from ECG recommendation
                if (
                    abs(c - _ECG_RICH_BLACK_C) > 0.15
                    or abs(m - _ECG_RICH_BLACK_M) > 0.15
                    or abs(y - _ECG_RICH_BLACK_Y) > 0.15
                ):
                    bad_recipe_count += 1
                    bad_recipe_pages.add(page_num)

        if bad_recipe_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_ECG_014",
                    severity=Severity.ADVISORY,
                    message=(
                        f"ECG rich black recipe: {bad_recipe_count} object(s) use "
                        f"non-standard rich black recipe across "
                        f"{len(bad_recipe_pages)} page(s). ECG recommends "
                        f"C={_ECG_RICH_BLACK_C * 100:.0f}% "
                        f"M={_ECG_RICH_BLACK_M * 100:.0f}% "
                        f"Y={_ECG_RICH_BLACK_Y * 100:.0f}% "
                        f"K={_ECG_RICH_BLACK_K * 100:.0f}%"
                    ),
                    details={
                        "bad_recipe_count": bad_recipe_count,
                        "pages": sorted(bad_recipe_pages),
                        "recommended_c": _ECG_RICH_BLACK_C,
                        "recommended_m": _ECG_RICH_BLACK_M,
                        "recommended_y": _ECG_RICH_BLACK_Y,
                        "recommended_k": _ECG_RICH_BLACK_K,
                    },
                )
            )

        return findings

    @staticmethod
    def _check_trap_zone_width(
        path_events: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_015: Trap zone width recommendation."""
        findings: list[Finding] = []
        thin_count = 0
        thin_pages: set[int] = set()

        for event_info in path_events:
            line_width = event_info.get("line_width")
            page_num: int = event_info["page_num"]  # type: ignore[assignment]

            if line_width is not None and line_width < _ECG_TRAP_MIN_WIDTH:
                thin_count += 1
                thin_pages.add(page_num)

        if thin_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_ECG_015",
                    severity=Severity.ADVISORY,
                    message=(
                        f"ECG trap zone warning: {thin_count} path element(s) with "
                        f"stroke width below {_ECG_TRAP_MIN_WIDTH}pt across "
                        f"{len(thin_pages)} page(s) may need special trapping in "
                        f"ECG workflow"
                    ),
                    details={
                        "thin_element_count": thin_count,
                        "pages": sorted(thin_pages),
                        "trap_min_width": _ECG_TRAP_MIN_WIDTH,
                    },
                    object_type="path",
                )
            )

        return findings

    @staticmethod
    def _check_icc_version(
        document: SemanticDocument,
    ) -> list[Finding]:
        """GRD_ECG_016: ECG profile ICC version."""
        findings: list[Finding] = []

        if hasattr(document, "output_intents"):
            for intent in document.output_intents:
                profile = getattr(intent, "dest_output_profile", None)
                if profile is None:
                    continue
                icc_version = getattr(profile, "version", None)
                if icc_version is not None and icc_version < 4.0:
                    findings.append(
                        Finding(
                            inspection_id="GRD_ECG_016",
                            severity=Severity.WARNING,
                            message=(
                                f"ECG ICC profile version {icc_version} is below "
                                f"v4.0; ECG workflows require ICC v4 or later for "
                                f"accurate multicolor profiling"
                            ),
                            details={
                                "icc_version": icc_version,
                                "required_minimum": 4.0,
                            },
                        )
                    )

        return findings

    @staticmethod
    def _check_devicen_ordering(
        devicen_spaces: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_017: Multicolor DeviceN ordering."""
        findings: list[Finding] = []

        for dn in devicen_spaces:
            colorants: list[str] = dn["colorants"]  # type: ignore[assignment]
            page_num: int = dn["page_num"]  # type: ignore[assignment]

            if len(colorants) != 7:
                continue

            lower_names = [c.lower() for c in colorants]
            # Check if all expected CMYKOGV names are present
            if set(lower_names) != _CMYKOGV_NAMES:
                continue

            # Verify ordering matches CMYKOGV convention
            if lower_names != _CMYKOGV_ORDER:
                findings.append(
                    Finding(
                        inspection_id="GRD_ECG_017",
                        severity=Severity.WARNING,
                        message=(
                            f"DeviceN colorant order {colorants} on page {page_num} "
                            f"does not follow CMYKOGV convention "
                            f"{[n.capitalize() for n in _CMYKOGV_ORDER]}"
                        ),
                        page_num=page_num,
                        details={
                            "cs_name": dn["cs_name"],
                            "actual_order": colorants,
                            "expected_order": _CMYKOGV_ORDER,
                        },
                    )
                )

        return findings

    def _check_channel_ink_limit(
        self,
        devicen_color_events: list[dict[str, object]],
    ) -> list[Finding]:
        """GRD_ECG_018: Total ink limit per channel."""
        findings: list[Finding] = []
        high_ink_threshold = 0.90  # 90% advisory threshold

        for event_info in devicen_color_events:
            color_values: tuple[float, ...] = event_info["color_values"]  # type: ignore[assignment]
            page_num: int = event_info["page_num"]  # type: ignore[assignment]

            high_channels: list[int] = []
            for i, val in enumerate(color_values):
                if val > high_ink_threshold:
                    high_channels.append(i)

            if high_channels:
                findings.append(
                    Finding(
                        inspection_id="GRD_ECG_018",
                        severity=Severity.ADVISORY,
                        message=(
                            f"ECG high ink per channel: channel(s) {high_channels} "
                            f"exceed {high_ink_threshold * 100:.0f}% on page {page_num}"
                        ),
                        page_num=page_num,
                        details={
                            "high_channels": high_channels,
                            "threshold": high_ink_threshold,
                            "color_values": list(color_values),
                        },
                    )
                )

        return findings
