"""TransparencyAnalyzer — blend modes, soft masks, and conflict detection.

Processes OpacityChangedEvent events to detect risky transparency usage.

Blend modes are classified as safe or risky per GWG 2022 guidelines:
- Safe: Normal, Multiply, Screen, Overlay, Darken, Lighten, ColorDodge, ColorBurn
- Risky: HardLight, SoftLight, Difference, Exclusion, Hue, Saturation, Color, Luminosity

Check IDs:
    GRD_TRANS_001 — Risky blend mode used
    GRD_TRANS_002 — Transparency with overprint conflict
    GRD_TRANS_003 — Soft mask detected (rendering complexity)
    GRD_TRANS_004 — Low opacity (<0.5) on visible content
    GRD_TRANS_005 — Transparency group with non-CMYK color space
    GRD_TRANS_006 — Knockout transparency group
    GRD_TRANS_007 — Shading pattern with banding risk
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

_SAFE_BLEND_MODES = frozenset(
    {
        "Normal",
        "Multiply",
        "Screen",
        "Overlay",
        "Darken",
        "Lighten",
        "ColorDodge",
        "ColorBurn",
    }
)

_RISKY_BLEND_MODES = frozenset(
    {
        "HardLight",
        "SoftLight",
        "Difference",
        "Exclusion",
        "Hue",
        "Saturation",
        "Color",
        "Luminosity",
    }
)


class TransparencyAnalyzer(BaseAnalyzer):
    """Analyzer for transparency-related preflight issues."""

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze transparency events for risky patterns."""
        from grounded.semantic.events import (
            ImagePlacedEvent,
            OpacityChangedEvent,
            OverprintChangedEvent,
        )

        findings: list[Finding] = []
        seen_blend_modes: set[str] = set()

        # Track opacity and overprint state per page for conflict detection
        has_transparency = False
        has_overprint = False
        current_page = 0

        for event in events:
            # Reset per-page tracking
            if event.page_num != current_page:
                if has_transparency and has_overprint:
                    findings.append(self._transparency_overprint_conflict(current_page))
                has_transparency = False
                has_overprint = False
                current_page = event.page_num

            if isinstance(event, OpacityChangedEvent):
                # Check for non-trivial transparency
                if event.stroking_alpha is not None and event.stroking_alpha < 1.0:
                    has_transparency = True
                if event.non_stroking_alpha is not None and event.non_stroking_alpha < 1.0:
                    has_transparency = True

                # GRD_TRANS_004: Low opacity on visible content
                if event.non_stroking_alpha is not None and event.non_stroking_alpha < 0.5:
                    findings.append(
                        Finding(
                            inspection_id="GRD_TRANS_004",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Low non-stroking opacity ({event.non_stroking_alpha:.2f}) "
                                f"on page {event.page_num} "
                                f"(content may be nearly invisible in print)"
                            ),
                            page_num=event.page_num,
                            details={
                                "non_stroking_alpha": event.non_stroking_alpha,
                            },
                        )
                    )

                # GRD_TRANS_001: Risky blend mode
                if event.blend_mode and event.blend_mode not in _SAFE_BLEND_MODES:
                    if event.blend_mode not in seen_blend_modes:
                        seen_blend_modes.add(event.blend_mode)
                        findings.append(
                            Finding(
                                inspection_id="GRD_TRANS_001",
                                severity=Severity.WARNING,
                                message=(
                                    f"Risky blend mode '{event.blend_mode}' "
                                    f"used on page {event.page_num}"
                                ),
                                page_num=event.page_num,
                                details={
                                    "blend_mode": event.blend_mode,
                                    "is_risky": event.blend_mode in _RISKY_BLEND_MODES,
                                },
                                iso_clause="ISO 32000-2:2020 11.3.5",
                            )
                        )
                    has_transparency = True

            elif isinstance(event, OverprintChangedEvent):
                if event.overprint_stroking or event.overprint_non_stroking:
                    has_overprint = True

            # GRD_TRANS_003: Soft mask on images
            elif isinstance(event, ImagePlacedEvent):
                if event.has_soft_mask:
                    findings.append(
                        Finding(
                            inspection_id="GRD_TRANS_003",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Image '{event.image_name}' uses soft mask "
                                f"on page {event.page_num} "
                                f"(increases rendering complexity)"
                            ),
                            page_num=event.page_num,
                            details={"image_name": event.image_name},
                            iso_clause="ISO 32000-2:2020 11.6.5.3",
                        )
                    )

        # Check final page
        if has_transparency and has_overprint:
            findings.append(self._transparency_overprint_conflict(current_page))

        # GRD_TRANS_005 & GRD_TRANS_006: Page-level transparency group checks
        for page in document.pages:
            if page.transparency_group is not None:
                group = page.transparency_group
                # GRD_TRANS_005: Non-CMYK color space in transparency group
                cs = group.get("/CS", "")
                cs_str = str(cs).lstrip("/") if cs else ""
                if cs_str and cs_str not in ("DeviceCMYK", ""):
                    findings.append(
                        Finding(
                            inspection_id="GRD_TRANS_005",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Transparency group on page {page.page_num} uses "
                                f"non-CMYK color space '{cs_str}'"
                            ),
                            page_num=page.page_num,
                            details={
                                "color_space": cs_str,
                                "group": {k: str(v) for k, v in group.items()},
                            },
                            iso_clause="ISO 32000-2:2020 11.4.7",
                        )
                    )

                # GRD_TRANS_006: Knockout transparency group
                knockout = group.get("/K", False)
                if knockout:
                    findings.append(
                        Finding(
                            inspection_id="GRD_TRANS_006",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Knockout transparency group on page {page.page_num} "
                                f"(may cause unexpected rendering)"
                            ),
                            page_num=page.page_num,
                            details={
                                "knockout": True,
                                "isolated": group.get("/I", False),
                            },
                            iso_clause="ISO 32000-2:2020 11.4.7",
                        )
                    )

        # GRD_TRANS_007: Shading patterns with potential banding risk
        for page in document.pages:
            shading = page.resources.get("/Shading") or page.resources.get("Shading")
            if shading and isinstance(shading, dict) and len(shading) > 0:
                findings.append(
                    Finding(
                        inspection_id="GRD_TRANS_007",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Shading pattern detected on page {page.page_num} "
                            f"({len(shading)} shading{'s' if len(shading) > 1 else ''}, "
                            f"potential gradient banding risk)"
                        ),
                        page_num=page.page_num,
                        details={
                            "shading_count": len(shading),
                            "shading_names": list(shading.keys()),
                        },
                        iso_clause="ISO 32000-2:2020 8.7.4",
                    )
                )

        return findings

    @staticmethod
    def _transparency_overprint_conflict(page_num: int) -> Finding:
        """Create a transparency + overprint conflict finding."""
        return Finding(
            inspection_id="GRD_TRANS_002",
            severity=Severity.WARNING,
            message=(
                f"Transparency and overprint both active on page {page_num} "
                f"(may cause unpredictable rendering)"
            ),
            page_num=page_num,
            details={},
            iso_clause="ISO 32000-2:2020 11.7.4.6",
        )

    @staticmethod
    def is_safe_blend_mode(mode: str) -> bool:
        """Check if a blend mode is considered safe for print."""
        return mode in _SAFE_BLEND_MODES

    @staticmethod
    def is_risky_blend_mode(mode: str) -> bool:
        """Check if a blend mode is considered risky for print."""
        return mode in _RISKY_BLEND_MODES
