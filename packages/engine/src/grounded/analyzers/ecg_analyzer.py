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
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

# Expected CMYKOGV colorant names (case-insensitive matching)
_CMYKOGV_NAMES = frozenset({
    "cyan", "magenta", "yellow", "black",
    "orange", "green", "violet",
})

# Alternative CMYKOGV abbreviations
_CMYKOGV_ABBREVS = frozenset({
    "c", "m", "y", "k", "o", "g", "v",
})

# Threshold for significant ink coverage
_SIGNIFICANT_INK = 0.05  # 5%


class EcgAnalyzer(BaseAnalyzer):
    """Analyzer for Expanded Color Gamut (ECG) printing readiness.

    Args:
        tac_limit: Maximum allowed 7-channel TAC percentage (default 300).
    """

    def __init__(self, tac_limit: float = 300.0) -> None:
        self.tac_limit = tac_limit

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze document for ECG readiness and compliance."""
        from grounded.semantic.events import (
            ColorChangedEvent,
            PathPaintingEvent,
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
                    colorant_list = [
                        c for c in cs.colorant_names if c not in ("All", "None")
                    ]
                    devicen_spaces.append({
                        "cs_name": cs_name,
                        "colorants": colorant_list,
                        "components": cs.components,
                        "page_num": page.page_num,
                    })
                    for colorant in colorant_list:
                        if colorant not in spot_colors:
                            spot_colors[colorant] = []
                        if page.page_num not in spot_colors[colorant]:
                            spot_colors[colorant].append(page.page_num)

        # Collect DeviceN color values from events for TAC and ink build checks
        devicen_color_events: list[dict[str, object]] = []

        for event in events:
            if isinstance(event, ColorChangedEvent):
                if event.color_space == "DeviceN" and len(event.color_values) > 4:
                    devicen_color_events.append({
                        "page_num": event.page_num,
                        "color_values": event.color_values,
                        "components": len(event.color_values),
                    })
            elif isinstance(event, PathPaintingEvent):
                if event.fill and event.fill_color_space == "DeviceN":
                    vals = event.fill_color_values
                    if len(vals) > 4:
                        devicen_color_events.append({
                            "page_num": event.page_num,
                            "color_values": vals,
                            "components": len(vals),
                        })
                if event.stroke and event.stroke_color_space == "DeviceN":
                    vals = event.stroke_color_values
                    if len(vals) > 4:
                        devicen_color_events.append({
                            "page_num": event.page_num,
                            "color_values": vals,
                            "components": len(vals),
                        })

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
        """GRD_ECG_002: Per-spot ECG achievability placeholder."""
        findings: list[Finding] = []

        for colorant, pages in sorted(spot_colors.items()):
            findings.append(
                Finding(
                    inspection_id="GRD_ECG_002",
                    severity=Severity.ADVISORY,
                    message=(
                        f"ECG achievability: Spot color '{colorant}' would need to be "
                        f"tested against FOGRA55 gamut boundary for ECG reproducibility "
                        f"(found on page(s) {pages})"
                    ),
                    details={
                        "colorant_name": colorant,
                        "pages": pages,
                        "note": (
                            "Actual Delta-E computation requires the FOGRA55 "
                            "gamut boundary mesh; this is a placeholder finding"
                        ),
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
                        severity=Severity.SQUALL,
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
                        severity=Severity.SQUALL,
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
                        severity=Severity.SQUALL,
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
