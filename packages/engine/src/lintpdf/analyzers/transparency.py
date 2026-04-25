"""TransparencyAnalyzer — blend modes, soft masks, and conflict detection.

Processes OpacityChangedEvent events to detect risky transparency usage.

Blend modes are classified as safe or risky per GWG 2022 guidelines:
- Safe: Normal, Multiply, Screen, Overlay, Darken, Lighten, ColorDodge, ColorBurn
- Risky: HardLight, SoftLight, Difference, Exclusion, Hue, Saturation, Color, Luminosity

Check IDs:
    LPDF_TRANS_001 — Risky blend mode used
    LPDF_TRANS_002 — Transparency with overprint conflict
    LPDF_TRANS_003 — Soft mask detected (rendering complexity)
    LPDF_TRANS_004 — Low opacity (<0.5) on visible content
    LPDF_TRANS_005 — Transparency group with non-CMYK color space
    LPDF_TRANS_006 — Knockout transparency group
    LPDF_TRANS_007 — Shading pattern with banding risk
    LPDF_TRANS_BLEND_CS_MISMATCH — Transparency-group blending CS
        differs from OutputIntent destination CS (T2-TRN04)
    LPDF_TRANS_ON_SPOT — Transparency applied while a Separation /
        DeviceN colour space is on a page (T2-TRN05)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument, SemanticPage

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
        from lintpdf.semantic.events import (
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

                # LPDF_TRANS_004: Low opacity on visible content
                if event.non_stroking_alpha is not None and event.non_stroking_alpha < 0.5:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_TRANS_004",
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

                # LPDF_TRANS_001: Risky blend mode
                if event.blend_mode and event.blend_mode not in _SAFE_BLEND_MODES:
                    if event.blend_mode not in seen_blend_modes:
                        seen_blend_modes.add(event.blend_mode)
                        findings.append(
                            Finding(
                                inspection_id="LPDF_TRANS_001",
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

            # LPDF_TRANS_003: Soft mask on images
            elif isinstance(event, ImagePlacedEvent):
                if event.has_soft_mask:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_TRANS_003",
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

        # LPDF_TRANS_005 & LPDF_TRANS_006: Page-level transparency group checks
        for page in document.pages:
            if page.transparency_group is not None:
                group = page.transparency_group
                # LPDF_TRANS_005: Non-CMYK color space in transparency group
                cs = group.get("/CS", "")
                cs_str = str(cs).lstrip("/") if cs else ""
                if cs_str and cs_str not in ("DeviceCMYK", ""):
                    findings.append(
                        Finding(
                            inspection_id="LPDF_TRANS_005",
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

                # LPDF_TRANS_006: Knockout transparency group
                knockout = group.get("/K", False)
                if knockout:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_TRANS_006",
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

        # T2-TRN04 — transparency group /CS vs OutputIntent /S.
        findings.extend(self._check_blend_cs_mismatch(document))

        # T2-TRN05 — transparency on pages whose resources include a
        # Separation / DeviceN colour space.
        findings.extend(self._check_transparency_on_spot(document, events))

        # LPDF_TRANS_007: Shading patterns with potential banding risk
        for page in document.pages:
            shading = page.resources.get("/Shading") or page.resources.get("Shading")
            if shading and isinstance(shading, dict) and len(shading) > 0:
                findings.append(
                    Finding(
                        inspection_id="LPDF_TRANS_007",
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
            inspection_id="LPDF_TRANS_002",
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

    @staticmethod
    def _output_intent_cs(document: SemanticDocument) -> str:
        """Return a normalised label for the OutputIntent destination
        colour space, or empty string when no OutputIntent is set."""
        for oi in document.output_intents or []:
            s = str(oi.get("/S", "")).lstrip("/")
            if s == "GTS_PDFX":
                # PDF/X output intents target the destination ICC's CS.
                # Pick the device class out of /DestOutputProfileRef
                # subtype if present; otherwise default to CMYK because
                # PDF/X-1a / X-3 / X-4 are CMYK-anchored families.
                profile = oi.get("/DestOutputProfile")
                if isinstance(profile, dict):
                    n = profile.get("/N")
                    if n == 4:
                        return "DeviceCMYK"
                    if n == 3:
                        return "DeviceRGB"
                    if n == 1:
                        return "DeviceGray"
                return "DeviceCMYK"
            if s == "GTS_PDFA1":
                return "DeviceCMYK"
        return ""

    def _check_blend_cs_mismatch(self, document: SemanticDocument) -> list[Finding]:
        """T2-TRN04 — flag pages whose transparency group declares a
        blending colour space that disagrees with the OutputIntent's
        destination colour space."""
        oi_cs = self._output_intent_cs(document)
        if not oi_cs:
            return []
        findings: list[Finding] = []
        for page in document.pages:
            if page.transparency_group is None:
                continue
            cs = page.transparency_group.get("/CS")
            cs_str = str(cs).lstrip("/") if cs else ""
            if not cs_str:
                continue
            if cs_str != oi_cs:
                findings.append(
                    Finding(
                        inspection_id="LPDF_TRANS_BLEND_CS_MISMATCH",
                        severity=Severity.WARNING,
                        message=(
                            f"Transparency-group blending CS '{cs_str}' on page "
                            f"{page.page_num} differs from OutputIntent destination "
                            f"'{oi_cs}'; flatteners may produce unexpected colour"
                        ),
                        page_num=page.page_num,
                        details={
                            "blend_cs": cs_str,
                            "output_intent_cs": oi_cs,
                        },
                        iso_clause="ISO 32000-2 §11.4.7 / ISO 15930-7 §6.2.4",
                    )
                )
        return findings

    @staticmethod
    def _has_spot_color_resource(page: SemanticPage) -> bool:  # type: ignore[name-defined]
        """Heuristic: page resources include at least one Separation /
        DeviceN colour space entry."""
        cs_dict = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace") or {}
        if not isinstance(cs_dict, dict):
            return False
        for value in cs_dict.values():
            try:
                first = str(value[0]).lstrip("/") if hasattr(value, "__getitem__") else ""
            except Exception:
                first = ""
            if first in ("Separation", "DeviceN"):
                return True
        return False

    def _check_transparency_on_spot(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],  # type: ignore[name-defined]
    ) -> list[Finding]:
        """T2-TRN05 — when a page declares a Separation / DeviceN
        colour space AND has any transparency event (alpha < 1.0 or
        non-Normal blend mode), emit one advisory per page."""
        from lintpdf.semantic.events import OpacityChangedEvent

        spot_pages: dict[int, SemanticPage] = {  # type: ignore[name-defined]
            p.page_num: p for p in document.pages if self._has_spot_color_resource(p)
        }
        if not spot_pages:
            return []

        flagged: set[int] = set()
        for event in events:
            if event.page_num not in spot_pages or event.page_num in flagged:
                continue
            if not isinstance(event, OpacityChangedEvent):
                continue
            has_alpha = (event.stroking_alpha is not None and event.stroking_alpha < 1.0) or (
                event.non_stroking_alpha is not None and event.non_stroking_alpha < 1.0
            )
            has_blend = event.blend_mode and event.blend_mode != "Normal"
            if has_alpha or has_blend:
                flagged.add(event.page_num)

        findings: list[Finding] = []
        for page_num in sorted(flagged):
            findings.append(
                Finding(
                    inspection_id="LPDF_TRANS_ON_SPOT",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Transparency applied on page {page_num} where Separation / "
                        f"DeviceN spot colour spaces are declared; some RIPs flatten "
                        f"this to process colour and lose the spot"
                    ),
                    page_num=page_num,
                    details={"page_num": page_num},
                    iso_clause="ISO 32000-2 §11.7 / GWG 2022 transparency-on-spot guidance",
                )
            )
        return findings
