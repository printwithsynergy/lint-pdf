"""ColorAnalyzer — TAC calculation, prohibited spaces, ICC validation.

Processes ColorChangedEvent and PathPaintingEvent events plus
SemanticDocument color space data to detect color-related preflight issues.

TAC (Total Area Coverage) = sum of CMYK component values as percentages.
For example, C=100% M=80% Y=70% K=30% = TAC 280%.

Check IDs:
    LPDF_COLOR_001 — Prohibited color space used
    LPDF_COLOR_002 — DeviceRGB used without ICC profile
    LPDF_COLOR_003 — Spot color with no backing color space
    LPDF_COLOR_004 — TAC exceeds limit
    LPDF_COLOR_005 — Registration color (all CMYK at 100%)
    LPDF_COLOR_006 — Output intent missing from document
    LPDF_COLOR_007 — Spot color detected (informational catalog)
    LPDF_COLOR_008 — Rich black on small text (<12pt, >1 ink)
    LPDF_COLOR_009 — 100% K not overprinting (knockout black)
    LPDF_COLOR_010 — Pure K-only on large fill area
    LPDF_COLOR_011 — Spot color name conflict (same name, different alternate)
    LPDF_COLOR_012 — Minimum printing dot below threshold (scum dot risk)
    LPDF_COLOR_013 — Gamut warning / out-of-gamut color (RGB in CMYK workflow)
    LPDF_COLOR_014 — Full color space inventory
    LPDF_COLOR_015 — Device-dependent color space warning
    LPDF_COLOR_016 — Impure gray (CMY used for gray)
    LPDF_COLOR_017 — Impure black (CMY contamination on K)
    LPDF_COLOR_018 — Lab color space detected
    LPDF_COLOR_019 — Indexed color space detected
    LPDF_COLOR_020 — Default color space used
    LPDF_COLOR_021 — Rich black text (any size, >1 CMYK ink) — advisory
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from siftpdf.analyzers.base import BaseAnalyzer
from siftpdf.analyzers.finding import Finding, Severity
from siftpdf.primitives import ink as ink_primitives

if TYPE_CHECKING:
    from siftpdf.semantic.events import (
        ColorChangedEvent,
        ContentStreamEvent,
        PathPaintingEvent,
        TextRenderedEvent,
    )
    from siftpdf.semantic.model import SemanticDocument

# Default TAC limits by print method
DEFAULT_TAC_LIMIT = 300.0  # Conservative default
TAC_LIMIT_SHEETFED = 330.0
TAC_LIMIT_WEB = 260.0

# Color spaces prohibited in PDF/X-4
_PROHIBITED_SPACES = frozenset({"CalGray", "CalRGB"})


class ColorAnalyzer(BaseAnalyzer):
    """Analyzer for color space usage and TAC compliance.

    Args:
        tac_limit: Maximum allowed TAC percentage (default 300).
    """

    def __init__(
        self,
        tac_limit: float = DEFAULT_TAC_LIMIT,
        *,
        brand_palette_present: bool = False,
    ) -> None:
        self.tac_limit = tac_limit
        # When the tenant hasn't declared a brand color palette we
        # have no ground truth for whether a pure-K fill or knockout
        # black was intentional. The rules still have noise value on
        # brand-configured tenants, but on an uncategorised tenant
        # they generate only "might be wrong, can't tell" findings
        # -- Opus rated 3,054 such findings as needs_context on one
        # Pink-Slush page. Suppress both outright in that case.
        self.brand_palette_present = brand_palette_present

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze color usage across the document."""
        from siftpdf.semantic.events import (
            ColorChangedEvent,
            OverprintChangedEvent,
            PathPaintingEvent,
            TextRenderedEvent,
        )

        findings: list[Finding] = []
        seen_spaces: set[tuple[int, str]] = set()
        overprint_non_stroking = False

        # WS-7 per-page aggregation: LPDF_COLOR_009 (knockout black)
        # and LPDF_COLOR_010 (pure K-only) fire once per matching
        # path event in the old implementation, producing ~1,000
        # findings per page on vector-dense artwork. Collect hits
        # into these dicts and emit one aggregate per (rule, page)
        # at the end of the analyze() pass.
        knockout_agg: dict[int, dict[str, object]] = {}
        pure_k_agg: dict[int, dict[str, object]] = {}

        # LPDF_COLOR_014: Color space inventory tracking
        cs_inventory: dict[str, dict[str, int | list[int]]] = {}

        for event in events:
            if isinstance(event, OverprintChangedEvent):
                if event.overprint_non_stroking is not None:
                    overprint_non_stroking = event.overprint_non_stroking
            elif isinstance(event, ColorChangedEvent):
                findings.extend(self._check_color_event(event, seen_spaces))
                # LPDF_COLOR_014: Track color space inventory
                cs_type = event.color_space
                if cs_type not in cs_inventory:
                    cs_inventory[cs_type] = {"count": 0, "pages": []}
                cs_inventory[cs_type]["count"] += 1  # type: ignore[operator]
                page_list: list[int] = cs_inventory[cs_type]["pages"]  # type: ignore[assignment]
                if event.page_num not in page_list:
                    page_list.append(event.page_num)
            elif isinstance(event, PathPaintingEvent):
                findings.extend(self._check_path_tac(event))
                findings.extend(self._check_registration_color(event))
                if self.brand_palette_present:
                    self._accumulate_knockout_black(event, overprint_non_stroking, knockout_agg)
                    self._accumulate_pure_k_fill(event, pure_k_agg)
                findings.extend(self._check_impure_gray(event))
                findings.extend(self._check_impure_black(event))
            elif isinstance(event, TextRenderedEvent):
                findings.extend(self._check_rich_black_text(event))

        # LPDF_COLOR_006: Output intent missing
        if not document.output_intents:
            findings.append(
                Finding(
                    inspection_id="LPDF_COLOR_006",
                    severity=Severity.WARNING,
                    message="No Output Intent defined in document",
                    iso_clause="ISO 15930-7:2010 6.2.3",
                )
            )

        # LPDF_COLOR_011: Spot color name conflicts
        findings.extend(self._check_spot_color_conflicts(document))

        # LPDF_COLOR_012: Minimum printing dot below threshold
        findings.extend(self._check_minimum_dot(document))

        # LPDF_COLOR_013: Gamut warning — RGB values in CMYK workflow
        findings.extend(self._check_gamut_warning(document))

        # Check page-level color spaces from SemanticDocument
        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                key = (page.page_num, cs.cs_type)
                if key not in seen_spaces:
                    seen_spaces.add(key)
                    if cs.cs_type in _PROHIBITED_SPACES:
                        findings.append(
                            Finding(
                                inspection_id="LPDF_COLOR_001",
                                severity=Severity.ERROR,
                                message=(
                                    f"Prohibited color space '{cs.cs_type}' "
                                    f"defined in page {page.page_num} resources"
                                ),
                                page_num=page.page_num,
                                details={
                                    "color_space_name": cs_name,
                                    "color_space_type": cs.cs_type,
                                },
                                iso_clause="ISO 15930-7:2010 6.2.4",
                            )
                        )

                    # LPDF_COLOR_002: DeviceRGB without ICC
                    if cs.cs_type == "DeviceRGB" and cs.icc_profile_ref is None:
                        findings.append(
                            Finding(
                                inspection_id="LPDF_COLOR_002",
                                severity=Severity.WARNING,
                                message=(
                                    f"DeviceRGB color space '{cs_name}' "
                                    f"used without ICC profile on page {page.page_num}"
                                ),
                                page_num=page.page_num,
                                details={
                                    "color_space_name": cs_name,
                                },
                                iso_clause="ISO 15930-7:2010 6.2.3",
                            )
                        )

                    # LPDF_COLOR_003: Separation without alternate
                    if cs.cs_type in ("Separation", "DeviceN") and cs.alternate is None:
                        findings.append(
                            Finding(
                                inspection_id="LPDF_COLOR_003",
                                severity=Severity.WARNING,
                                message=(
                                    f"Spot color '{cs_name}' ({cs.cs_type}) "
                                    f"has no alternate color space on page {page.page_num}"
                                ),
                                page_num=page.page_num,
                                details={
                                    "color_space_name": cs_name,
                                    "color_space_type": cs.cs_type,
                                },
                                iso_clause="ISO 32000-2:2020 8.6.6.4",
                            )
                        )

                    # LPDF_COLOR_007: Spot color catalog
                    if cs.cs_type in ("Separation", "DeviceN") and cs.colorant_names:
                        for colorant in cs.colorant_names:
                            if colorant and colorant not in ("All", "None"):
                                findings.append(
                                    Finding(
                                        inspection_id="LPDF_COLOR_007",
                                        severity=Severity.ADVISORY,
                                        message=(
                                            f"Spot color '{colorant}' used on page {page.page_num}"
                                        ),
                                        page_num=page.page_num,
                                        details={
                                            "colorant_name": colorant,
                                            "color_space_name": cs_name,
                                            "color_space_type": cs.cs_type,
                                        },
                                    )
                                )

                    # LPDF_COLOR_018: Lab color space detected
                    if cs.cs_type == "Lab":
                        findings.append(
                            Finding(
                                inspection_id="LPDF_COLOR_018",
                                severity=Severity.ADVISORY,
                                message=(
                                    f"Lab color space '{cs_name}' used on page "
                                    f"{page.page_num} (CIE Lab is uncommon in print workflows)"
                                ),
                                page_num=page.page_num,
                                details={
                                    "color_space_name": cs_name,
                                    "color_space_type": cs.cs_type,
                                },
                                iso_clause="ISO 32000-2:2020 8.6.5.4",
                            )
                        )

                    # LPDF_COLOR_019: Indexed color space detected
                    if cs.cs_type == "Indexed":
                        findings.append(
                            Finding(
                                inspection_id="LPDF_COLOR_019",
                                severity=Severity.ADVISORY,
                                message=(
                                    f"Indexed color space '{cs_name}' on page "
                                    f"{page.page_num} (limited color precision)"
                                ),
                                page_num=page.page_num,
                                details={
                                    "color_space_name": cs_name,
                                    "color_space_type": cs.cs_type,
                                },
                                iso_clause="ISO 32000-2:2020 8.6.6.3",
                            )
                        )

        # LPDF_COLOR_014: Full color space inventory
        if cs_inventory:
            findings.append(
                Finding(
                    inspection_id="LPDF_COLOR_014",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Color space inventory: {len(cs_inventory)} unique "
                        f"color space type(s) used in document"
                    ),
                    details={
                        "inventory": cs_inventory,
                    },
                )
            )

        # LPDF_COLOR_015: Device-dependent color space warning
        _DEVICE_DEPENDENT = {"DeviceRGB", "DeviceCMYK", "DeviceGray"}
        if document.output_intents:
            for page in document.pages:
                for cs_name, cs in page.color_spaces.items():
                    if cs.cs_type in _DEVICE_DEPENDENT:
                        # For PDF/X-4: DeviceGray and DeviceCMYK are allowed;
                        # DeviceRGB is not
                        if cs.cs_type == "DeviceRGB":
                            findings.append(
                                Finding(
                                    inspection_id="LPDF_COLOR_015",
                                    severity=Severity.ADVISORY,
                                    message=(
                                        f"Device-dependent color space '{cs.cs_type}' "
                                        f"on page {page.page_num} with OutputIntent present "
                                        f"(DeviceRGB is not allowed in PDF/X-4; "
                                        f"use ICC-based alternative)"
                                    ),
                                    page_num=page.page_num,
                                    details={
                                        "color_space_name": cs_name,
                                        "color_space_type": cs.cs_type,
                                        "recommendation": "Use ICC-based color space",
                                    },
                                    iso_clause="ISO 15930-7:2010 6.2.4",
                                )
                            )
                        elif cs.cs_type in ("DeviceCMYK", "DeviceGray"):
                            findings.append(
                                Finding(
                                    inspection_id="LPDF_COLOR_015",
                                    severity=Severity.ADVISORY,
                                    message=(
                                        f"Device-dependent color space '{cs.cs_type}' "
                                        f"on page {page.page_num} with OutputIntent present "
                                        f"(ICC-based alternative recommended)"
                                    ),
                                    page_num=page.page_num,
                                    details={
                                        "color_space_name": cs_name,
                                        "color_space_type": cs.cs_type,
                                        "recommendation": "Use ICC-based color space",
                                    },
                                )
                            )

        # LPDF_COLOR_020: Default color space overrides
        findings.extend(self._check_default_color_spaces(document))

        # WS-7: emit one aggregate finding per (rule, page) for the
        # per-object rules that previously exploded on dense artwork.
        findings.extend(self._emit_knockout_aggregates(knockout_agg))
        findings.extend(self._emit_pure_k_aggregates(pure_k_agg))

        return findings

    @staticmethod
    def _check_color_event(
        event: ColorChangedEvent,
        seen_spaces: set[tuple[int, str]],
    ) -> list[Finding]:
        """Check a color change event for prohibited spaces."""
        findings: list[Finding] = []
        key = (event.page_num, event.color_space)

        if key not in seen_spaces:
            seen_spaces.add(key)
            if event.color_space in _PROHIBITED_SPACES:
                findings.append(
                    Finding(
                        inspection_id="LPDF_COLOR_001",
                        severity=Severity.ERROR,
                        message=(
                            f"Prohibited color space '{event.color_space}' "
                            f"used on page {event.page_num}"
                        ),
                        page_num=event.page_num,
                        details={
                            "color_space": event.color_space,
                            "stroking": event.stroking,
                        },
                        iso_clause="ISO 15930-7:2010 6.2.4",
                    )
                )

        return findings

    def _check_path_tac(self, event: PathPaintingEvent) -> list[Finding]:
        """Check TAC for CMYK colors in path painting events."""
        findings: list[Finding] = []

        if event.fill and event.fill_color_space == "DeviceCMYK":
            tac = self._calculate_tac(event.fill_color_values)
            if tac > self.tac_limit:
                findings.append(
                    Finding(
                        inspection_id="LPDF_COLOR_004",
                        severity=Severity.WARNING,
                        message=(
                            f"TAC {tac:.0f}% exceeds limit {self.tac_limit:.0f}% "
                            f"(fill color on page {event.page_num})"
                        ),
                        page_num=event.page_num,
                        details={
                            "tac": tac,
                            "tac_limit": self.tac_limit,
                            "color_values": list(event.fill_color_values),
                            "stroking": False,
                        },
                        iso_clause="GWG 2022 6.3",
                    )
                )

        if event.stroke and event.stroke_color_space == "DeviceCMYK":
            tac = self._calculate_tac(event.stroke_color_values)
            if tac > self.tac_limit:
                findings.append(
                    Finding(
                        inspection_id="LPDF_COLOR_004",
                        severity=Severity.WARNING,
                        message=(
                            f"TAC {tac:.0f}% exceeds limit {self.tac_limit:.0f}% "
                            f"(stroke color on page {event.page_num})"
                        ),
                        page_num=event.page_num,
                        details={
                            "tac": tac,
                            "tac_limit": self.tac_limit,
                            "color_values": list(event.stroke_color_values),
                            "stroking": True,
                        },
                        iso_clause="GWG 2022 6.3",
                    )
                )

        return findings

    @staticmethod
    def _check_registration_color(event: PathPaintingEvent) -> list[Finding]:
        """Check for registration color (all CMYK components at 100%).

        LPDF_COLOR_005: Registration color is usually an error unless
        intentionally used for registration marks.
        """
        findings: list[Finding] = []

        def _is_registration(cs: str, vals: tuple[float, ...]) -> bool:
            if cs != "DeviceCMYK" or len(vals) != 4:
                return False
            return all(abs(v - 1.0) < 0.01 for v in vals)

        if event.fill and _is_registration(event.fill_color_space, event.fill_color_values):
            findings.append(
                Finding(
                    inspection_id="LPDF_COLOR_005",
                    severity=Severity.WARNING,
                    message=(
                        f"Registration color (100% all CMYK) used as fill on page {event.page_num}"
                    ),
                    page_num=event.page_num,
                    details={"color_values": list(event.fill_color_values), "stroking": False},
                    object_type="path",
                )
            )

        if event.stroke and _is_registration(event.stroke_color_space, event.stroke_color_values):
            findings.append(
                Finding(
                    inspection_id="LPDF_COLOR_005",
                    severity=Severity.WARNING,
                    message=(
                        f"Registration color (100% all CMYK) used as stroke "
                        f"on page {event.page_num}"
                    ),
                    page_num=event.page_num,
                    details={"color_values": list(event.stroke_color_values), "stroking": True},
                    object_type="path",
                )
            )

        return findings

    @staticmethod
    def _check_rich_black_text(event: TextRenderedEvent) -> list[Finding]:
        """Check for rich black on text.

        Two findings emit from one condition: a CMYK fill with
        more than one non-zero ink channel on a text event.

        * ``LPDF_COLOR_008`` — warning for text < 12pt, same
          historical behaviour.
        * ``LPDF_COLOR_021`` — advisory for any text size, fires
          alongside LPDF_COLOR_008 on small text and on its own
          for display type. Captures the "Text should NEVER be
          rich black" print-production principle regardless of
          the point size.

        Neither is gated on the brand-palette flag — rich-black
        text is a universal misregistration risk and should show
        up in the findings panel on every preflight.
        """
        import math

        findings: list[Finding] = []
        if event.color_space != "DeviceCMYK" or len(event.color_values) != 4:
            return findings

        tm_scale_y = math.sqrt(event.text_matrix.b**2 + event.text_matrix.d**2)
        ctm_scale_y = math.sqrt(event.ctm.b**2 + event.ctm.d**2)
        effective_size = event.font_size * tm_scale_y * ctm_scale_y
        if effective_size <= 0:
            return findings

        non_zero = sum(1 for v in event.color_values if v > 0.01)
        if non_zero <= 1:
            return findings

        details = {
            "font_name": event.font_name,
            "effective_size": effective_size,
            "color_values": list(event.color_values),
            "non_zero_inks": non_zero,
        }

        if effective_size < 12.0:
            findings.append(
                Finding(
                    inspection_id="LPDF_COLOR_008",
                    severity=Severity.WARNING,
                    message=(
                        f"Rich black on small text ({effective_size:.1f}pt) "
                        f"on page {event.page_num} "
                        f"({non_zero} ink channels — risk of misregistration)"
                    ),
                    page_num=event.page_num,
                    details=details,
                    object_type="text",
                )
            )

        findings.append(
            Finding(
                inspection_id="LPDF_COLOR_021",
                severity=Severity.ADVISORY,
                message=(
                    f"Rich black text ({effective_size:.1f}pt, "
                    f"{non_zero} ink channels) on page {event.page_num} "
                    f"— pure K (100/0/0/0) is recommended to avoid "
                    f"misregistration."
                ),
                page_num=event.page_num,
                details=details,
                object_type="text",
            )
        )
        return findings

    @staticmethod
    def _bucket_for_page(agg: dict[int, dict[str, object]], page_num: int) -> dict[str, object]:
        """Return the per-page accumulator slot, creating a fresh
        {count, max_k_percent, bboxes} dict if needed."""
        bucket = agg.get(page_num)
        if bucket is None:
            bucket = {"count": 0, "max_k_percent": 0.0, "bboxes": []}
            agg[page_num] = bucket
        return bucket

    @classmethod
    def _accumulate_knockout_black(
        cls,
        event: PathPaintingEvent,
        overprint_non_stroking: bool,
        agg: dict[int, dict[str, object]],
    ) -> None:
        """Update the LPDF_COLOR_009 accumulator for this event.

        Knockout black = 0/0/0/100% CMYK fill with overprint OFF.
        Replaces the old per-event emit -- see _emit_knockout_aggregates
        for the one-per-page flush.
        """
        if not event.fill or event.fill_color_space != "DeviceCMYK":
            return
        vals = event.fill_color_values
        if len(vals) != 4:
            return
        is_pure_k = abs(vals[3] - 1.0) < 0.01 and all(abs(v) < 0.01 for v in vals[:3])
        if not (is_pure_k and not overprint_non_stroking):
            return
        bucket = cls._bucket_for_page(agg, event.page_num)
        bucket["count"] = int(bucket["count"]) + 1  # type: ignore[arg-type]
        bboxes = bucket["bboxes"]
        if isinstance(bboxes, list) and len(bboxes) < 5 and getattr(event, "bbox", None):
            bboxes.append(list(event.bbox))

    @classmethod
    def _accumulate_pure_k_fill(
        cls,
        event: PathPaintingEvent,
        agg: dict[int, dict[str, object]],
    ) -> None:
        """Update the LPDF_COLOR_010 accumulator. Pure K-only on
        fill (K > 50%, CMY ~= 0); large areas appear washed out
        without rich-black support. Emits once per page at the end."""
        if not event.fill or event.fill_color_space != "DeviceCMYK":
            return
        vals = event.fill_color_values
        if len(vals) != 4:
            return
        if not (vals[3] > 0.50 and all(abs(v) < 0.01 for v in vals[:3])):
            return
        bucket = cls._bucket_for_page(agg, event.page_num)
        bucket["count"] = int(bucket["count"]) + 1  # type: ignore[arg-type]
        k_pct = vals[3] * 100.0
        if k_pct > float(bucket["max_k_percent"]):  # type: ignore[arg-type]
            bucket["max_k_percent"] = k_pct
        bboxes = bucket["bboxes"]
        if isinstance(bboxes, list) and len(bboxes) < 5 and getattr(event, "bbox", None):
            bboxes.append(list(event.bbox))

    @staticmethod
    def _emit_knockout_aggregates(
        agg: dict[int, dict[str, object]],
    ) -> list[Finding]:
        out: list[Finding] = []
        for page_num in sorted(agg):
            bucket = agg[page_num]
            count = int(bucket["count"])  # type: ignore[arg-type]
            if count <= 0:
                continue
            out.append(
                Finding(
                    inspection_id="LPDF_COLOR_009",
                    severity=Severity.ADVISORY,
                    message=(
                        f"{count} object{'s' if count != 1 else ''} with "
                        f"100% K fill and no overprint on page {page_num} "
                        f"(knockout black may cause white gaps)"
                    ),
                    page_num=page_num,
                    details={
                        "object_count": count,
                        "overprint": False,
                        "representative_bboxes": bucket["bboxes"],
                    },
                    object_type="path",
                )
            )
        return out

    @staticmethod
    def _emit_pure_k_aggregates(
        agg: dict[int, dict[str, object]],
    ) -> list[Finding]:
        out: list[Finding] = []
        for page_num in sorted(agg):
            bucket = agg[page_num]
            count = int(bucket["count"])  # type: ignore[arg-type]
            if count <= 0:
                continue
            max_k = float(bucket["max_k_percent"])  # type: ignore[arg-type]
            out.append(
                Finding(
                    inspection_id="LPDF_COLOR_010",
                    severity=Severity.ADVISORY,
                    message=(
                        f"{count} pure K-only fill{'s' if count != 1 else ''} "
                        f"(max {max_k:.0f}% K) on page {page_num} "
                        f"(may appear washed out on large areas)"
                    ),
                    page_num=page_num,
                    details={
                        "object_count": count,
                        "max_k_percent": max_k,
                        "representative_bboxes": bucket["bboxes"],
                    },
                    object_type="path",
                )
            )
        return out

    @staticmethod
    def _check_impure_gray(event: PathPaintingEvent) -> list[Finding]:
        """Check for impure gray built from CMY instead of K-only (LPDF_COLOR_016).

        When C, M, Y values are approximately equal (within 5%) and all > 5%,
        but K is low (< 10%), this is likely a gray built from CMY rather than
        using the K channel, wasting ink and causing registration issues.
        """
        findings: list[Finding] = []
        if not event.fill or event.fill_color_space != "DeviceCMYK":
            return findings
        vals = event.fill_color_values
        if len(vals) != 4:
            return findings
        c, m, y, k = vals
        # All CMY > 5% and K < 10%
        if c > 0.05 and m > 0.05 and y > 0.05 and k < 0.10:
            # Check if CMY values are approximately equal (within 5% of each other)
            max_cmy = max(c, m, y)
            min_cmy = min(c, m, y)
            if (max_cmy - min_cmy) < 0.05:
                findings.append(
                    Finding(
                        inspection_id="LPDF_COLOR_016",
                        severity=Severity.WARNING,
                        message=(
                            f"Impure gray detected (CMY-built gray "
                            f"C={c * 100:.0f}% M={m * 100:.0f}% "
                            f"Y={y * 100:.0f}% K={k * 100:.0f}%) "
                            f"on page {event.page_num}"
                        ),
                        page_num=event.page_num,
                        details={
                            "color_values": list(vals),
                            "c_percent": c * 100.0,
                            "m_percent": m * 100.0,
                            "y_percent": y * 100.0,
                            "k_percent": k * 100.0,
                        },
                        iso_clause="GWG 2022 6.3",
                    )
                )
        return findings

    @staticmethod
    def _check_impure_black(event: PathPaintingEvent) -> list[Finding]:
        """Check for impure black with unnecessary CMY contamination (LPDF_COLOR_017).

        When K > 90% but any of C, M, Y > 5%, the color has unnecessary CMY
        contamination that wastes ink.
        """
        findings: list[Finding] = []
        if not event.fill or event.fill_color_space != "DeviceCMYK":
            return findings
        vals = event.fill_color_values
        if len(vals) != 4:
            return findings
        c, m, y, k = vals
        if k > 0.90 and (c > 0.05 or m > 0.05 or y > 0.05):
            findings.append(
                Finding(
                    inspection_id="LPDF_COLOR_017",
                    severity=Severity.WARNING,
                    message=(
                        f"Impure black detected "
                        f"(C={c * 100:.0f}% M={m * 100:.0f}% "
                        f"Y={y * 100:.0f}% K={k * 100:.0f}%) "
                        f"on page {event.page_num} — unnecessary CMY "
                        f"in near-K-only color"
                    ),
                    page_num=event.page_num,
                    details={
                        "color_values": list(vals),
                        "c_percent": c * 100.0,
                        "m_percent": m * 100.0,
                        "y_percent": y * 100.0,
                        "k_percent": k * 100.0,
                    },
                    iso_clause="GWG 2022 6.3",
                )
            )
        return findings

    @staticmethod
    def _check_default_color_spaces(document: SemanticDocument) -> list[Finding]:
        """Check for default color space overrides (LPDF_COLOR_020).

        DefaultRGB, DefaultCMYK, or DefaultGray entries in page resources
        override device color spaces and may cause unexpected color behavior.
        """
        findings: list[Finding] = []
        _DEFAULT_CS_NAMES = frozenset({"/DefaultRGB", "/DefaultCMYK", "/DefaultGray"})

        for page in document.pages:
            resources = page.resources
            color_space_res = resources.get("/ColorSpace", {})
            if not isinstance(color_space_res, dict):
                continue
            for cs_key in color_space_res:
                if cs_key in _DEFAULT_CS_NAMES:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_COLOR_020",
                            severity=Severity.WARNING,
                            message=(
                                f"Default color space override '{cs_key}' defined "
                                f"on page {page.page_num} (may cause unexpected "
                                f"color mapping)"
                            ),
                            page_num=page.page_num,
                            details={
                                "default_color_space": cs_key,
                            },
                            iso_clause="ISO 32000-2:2020 8.6.5.6",
                        )
                    )

        return findings

    @staticmethod
    def _check_spot_color_conflicts(
        document: SemanticDocument,
    ) -> list[Finding]:  # skipcq: PY-R1000
        """Check for spot color name conflicts (LPDF_COLOR_011).

        Same colorant name defined with different alternates on different pages.
        """
        findings: list[Finding] = []
        # Collect: colorant_name -> set of alternates
        colorant_alternates: dict[str, set[str | None]] = {}
        colorant_pages: dict[str, list[int]] = {}

        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type in ("Separation", "DeviceN") and cs.colorant_names:
                    for colorant in cs.colorant_names:
                        if ink_primitives.is_reserved_name(colorant):
                            continue
                        alt = cs.alternate if hasattr(cs, "alternate") else None
                        if colorant not in colorant_alternates:
                            colorant_alternates[colorant] = set()
                            colorant_pages[colorant] = []
                        colorant_alternates[colorant].add(str(alt) if alt is not None else None)
                        if page.page_num not in colorant_pages[colorant]:
                            colorant_pages[colorant].append(page.page_num)

        for colorant, alternates in colorant_alternates.items():
            if len(alternates) > 1:
                findings.append(
                    Finding(
                        inspection_id="LPDF_COLOR_011",
                        severity=Severity.WARNING,
                        message=(
                            f"Spot color '{colorant}' has conflicting alternate "
                            f"color spaces across pages {colorant_pages[colorant]}"
                        ),
                        details={
                            "colorant_name": colorant,
                            "alternate_count": len(alternates),
                            "pages": colorant_pages[colorant],
                        },
                    )
                )

        return findings

    @staticmethod
    def _check_minimum_dot(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
        """Check for separation tint values below 2% (LPDF_COLOR_012).

        When a Separation or DeviceN color space has tint values below 2%,
        there is a risk of scum dots in flexographic printing. Looks at
        color space definitions in page resources for tint transform hints.
        """
        findings: list[Finding] = []
        min_dot_threshold = 0.02  # 2%

        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                if cs.cs_type not in ("Separation", "DeviceN"):
                    continue
                # Check the resources for tint values associated with this space
                resources = page.resources
                color_space_res = resources.get("/ColorSpace", {})
                if not isinstance(color_space_res, dict):
                    continue
                cs_array = color_space_res.get(cs_name)
                if not isinstance(cs_array, list) or len(cs_array) < 4:
                    continue
                # The tint transform is the last element; we look for sampled
                # function dictionaries that contain low values
                tint_fn = cs_array[-1]
                if isinstance(tint_fn, dict):
                    # Check /Range or /C0 for near-zero start values
                    c0 = tint_fn.get("/C0", [])
                    if isinstance(c0, list):
                        for val in c0:
                            try:
                                fval = float(val)
                            except (ValueError, TypeError):
                                continue
                            if 0 < fval < min_dot_threshold:
                                colorant = cs.colorant_names[0] if cs.colorant_names else cs_name
                                findings.append(
                                    Finding(
                                        inspection_id="LPDF_COLOR_012",
                                        severity=Severity.WARNING,
                                        message=(
                                            f"Separation '{colorant}' has tint value "
                                            f"{fval * 100:.1f}% below 2% minimum dot "
                                            f"on page {page.page_num} (scum dot risk for flexo)"
                                        ),
                                        page_num=page.page_num,
                                        details={
                                            "colorant_name": colorant,
                                            "tint_value": fval,
                                            "threshold": min_dot_threshold,
                                        },
                                    )
                                )
                                return findings  # One finding is enough
        return findings

    @staticmethod
    def _check_gamut_warning(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
        """Check for RGB color spaces used in a CMYK workflow (LPDF_COLOR_013).

        Flags when DeviceRGB or CalRGB color spaces are found on pages
        but the document has a CMYK output intent, indicating potential
        out-of-gamut colors.
        """
        findings: list[Finding] = []

        # Determine if document has a CMYK output intent
        is_cmyk_workflow = False
        for oi in document.output_intents:
            # Check output condition identifier or dest profile
            oi_subtype = oi.get("/S", "")
            dest_cs = oi.get("/DestOutputProfileRef", "")
            info = oi.get("/Info", "")
            condition = oi.get("/OutputConditionIdentifier", "")
            # Heuristic: if any output intent mentions CMYK-related terms
            for val in (str(dest_cs), str(info), str(condition), str(oi_subtype)):
                if "CMYK" in val.upper() or "FOGRA" in val.upper() or "SWOP" in val.upper():
                    is_cmyk_workflow = True
                    break
            if is_cmyk_workflow:
                break

        if not is_cmyk_workflow:
            return findings

        # Check for RGB usage on pages
        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                if cs.cs_type in ("DeviceRGB", "CalRGB"):
                    findings.append(
                        Finding(
                            inspection_id="LPDF_COLOR_013",
                            severity=Severity.ADVISORY,
                            message=(
                                f"RGB color space '{cs_name}' ({cs.cs_type}) used "
                                f"on page {page.page_num} in a CMYK workflow "
                                f"(potential out-of-gamut colors)"
                            ),
                            page_num=page.page_num,
                            details={
                                "color_space_name": cs_name,
                                "color_space_type": cs.cs_type,
                            },
                        )
                    )
                    return findings  # One finding is enough

        return findings

    @staticmethod
    def _calculate_tac(color_values: tuple[float, ...]) -> float:
        """Calculate Total Area Coverage from CMYK values.

        CMYK values are in 0.0-1.0 range. TAC is the sum as percentages.
        For example: (1.0, 0.8, 0.7, 0.3) = 280%.
        """
        return sum(color_values) * 100.0
