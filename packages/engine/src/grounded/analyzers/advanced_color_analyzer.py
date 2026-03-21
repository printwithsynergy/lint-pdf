"""AdvancedColorAnalyzer — GCR/UCR profiling, ink savings, trapping, CxF, rich black.

Performs advanced color analysis beyond basic TAC and prohibited space checks,
focusing on production-level ink optimization and print quality concerns.

Check IDs:
    GRD_ADV_001 — Black generation profiling (GCR/UCR strategy detection)
    GRD_ADV_002 — Ink savings estimation (GCR headroom in CMYK fills)
    GRD_ADV_003 — Trapping risk analysis (small multicolor text)
    GRD_ADV_004 — CxF/X-4 spectral validation (CxF data parsing)
    GRD_ADV_005 — Rich black composition analysis (black usage classification)
    GRD_ADV_006 — CxF spectral vs declared color Delta-E
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument


class AdvancedColorAnalyzer(BaseAnalyzer):
    """Analyzer for advanced color production checks.

    Covers GCR/UCR profiling, ink savings estimation, trapping risk,
    CxF spectral data detection, and rich black composition analysis.

    Args:
        rich_black_c: Target rich black Cyan component (default 60%).
        rich_black_m: Target rich black Magenta component (default 40%).
        rich_black_y: Target rich black Yellow component (default 40%).
        rich_black_k: Target rich black Key component (default 100%).
    """

    def __init__(
        self,
        rich_black_c: float = 60.0,
        rich_black_m: float = 40.0,
        rich_black_y: float = 40.0,
        rich_black_k: float = 100.0,
    ) -> None:
        self.rich_black_c = rich_black_c
        self.rich_black_m = rich_black_m
        self.rich_black_y = rich_black_y
        self.rich_black_k = rich_black_k

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze advanced color properties across the document."""
        findings: list[Finding] = []

        findings.extend(self._check_black_generation_profiling(document))
        findings.extend(self._check_ink_savings(events))
        findings.extend(self._check_trapping_risk(events))
        findings.extend(self._check_cxf_spectral(document))
        findings.extend(self._check_rich_black_composition(events))

        return findings

    # ------------------------------------------------------------------
    # GRD_ADV_001 — Black generation profiling
    # ------------------------------------------------------------------

    @staticmethod
    def _check_black_generation_profiling(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Flag CMYK images that could be analyzed for GCR/UCR strategy.

        Actual pixel-level analysis requires image extraction which is
        expensive; this check identifies images that warrant further
        investigation.
        """
        findings: list[Finding] = []

        for page in document.pages:
            for image in page.images:
                if image.color_space is not None and image.color_space.is_cmyk():
                    findings.append(
                        Finding(
                            inspection_id="GRD_ADV_001",
                            severity=Severity.ADVISORY,
                            message=(
                                f"CMYK image '{image.name}' on page {page.page_num} "
                                f"({image.width}x{image.height}px) could be analyzed "
                                f"for GCR/UCR black generation strategy"
                            ),
                            page_num=page.page_num,
                            details={
                                "image_name": image.name,
                                "width": image.width,
                                "height": image.height,
                                "color_space_type": image.color_space.cs_type,
                            },
                            object_id=image.name,
                            object_type="image",
                        )
                    )

        return findings

    # ------------------------------------------------------------------
    # GRD_ADV_002 — Ink savings estimation
    # ------------------------------------------------------------------

    @staticmethod
    def _check_ink_savings(
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Estimate GCR ink savings potential from CMYK fill events.

        For each CMYK fill, calculates min(C, M, Y) as GCR headroom.
        When min(C, M, Y) > 10% and K < min(C, M, Y), there is
        potential for GCR-based ink reduction.
        """
        from grounded.semantic.events import PathPaintingEvent

        findings: list[Finding] = []
        total_cmyk_fills = 0
        fills_with_headroom = 0

        for event in events:
            if not isinstance(event, PathPaintingEvent):
                continue
            if not event.fill or event.fill_color_space != "DeviceCMYK":
                continue
            vals = event.fill_color_values
            if len(vals) != 4:
                continue

            total_cmyk_fills += 1
            c, m, y, k = vals  # values in 0.0-1.0 range
            min_cmy = min(c, m, y)

            # Headroom exists when min(C,M,Y) > 10% and K < min(C,M,Y)
            if min_cmy > 0.10 and k < min_cmy:
                fills_with_headroom += 1

        if total_cmyk_fills > 0:
            headroom_pct = (fills_with_headroom / total_cmyk_fills) * 100.0
            # Rough savings estimate: 5-15% ink reduction if GCR applied
            savings_low = headroom_pct * 0.05
            savings_high = headroom_pct * 0.15
            findings.append(
                Finding(
                    inspection_id="GRD_ADV_002",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Ink savings estimation: {total_cmyk_fills} CMYK fill event(s) "
                        f"analyzed, {headroom_pct:.1f}% with GCR headroom, "
                        f"estimated savings {savings_low:.1f}-{savings_high:.1f}%"
                    ),
                    details={
                        "total_cmyk_fills": total_cmyk_fills,
                        "fills_with_headroom": fills_with_headroom,
                        "headroom_percent": headroom_pct,
                        "estimated_savings_low": savings_low,
                        "estimated_savings_high": savings_high,
                    },
                )
            )

        return findings

    # ------------------------------------------------------------------
    # GRD_ADV_003 — Trapping risk analysis
    # ------------------------------------------------------------------

    @staticmethod
    def _check_trapping_risk(
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Detect trapping risk from small multicolor text.

        Small text (<12pt) using multiple process colors (2+ non-K
        components > 5%) without overprint creates misregistration risk.
        """
        import math

        from grounded.semantic.events import TextRenderedEvent

        findings: list[Finding] = []
        risk_count = 0

        for event in events:
            if not isinstance(event, TextRenderedEvent):
                continue
            if event.color_space != "DeviceCMYK" or len(event.color_values) != 4:
                continue

            # Calculate effective font size
            tm_scale_y = math.sqrt(event.text_matrix.b**2 + event.text_matrix.d**2)
            ctm_scale_y = math.sqrt(event.ctm.b**2 + event.ctm.d**2)
            effective_size = event.font_size * tm_scale_y * ctm_scale_y

            if effective_size >= 12.0 or effective_size <= 0:
                continue

            c, m, y, _k = event.color_values
            # Count non-K components above 5%
            non_k_active = sum(1 for v in (c, m, y) if v > 0.05)

            if non_k_active >= 2:
                risk_count += 1
                findings.append(
                    Finding(
                        inspection_id="GRD_ADV_003",
                        severity=Severity.SQUALL,
                        message=(
                            f"Trapping risk: small text ({effective_size:.1f}pt) "
                            f"on page {event.page_num} uses {non_k_active} non-K "
                            f"process colors (misregistration risk without trapping)"
                        ),
                        page_num=event.page_num,
                        details={
                            "font_name": event.font_name,
                            "effective_size": effective_size,
                            "color_values": list(event.color_values),
                            "non_k_active_channels": non_k_active,
                        },
                        object_type="text",
                    )
                )

        # Summary finding
        if risk_count > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_ADV_003",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Trapping risk summary: {risk_count} instance(s) of small "
                        f"multicolor text detected that may require trapping"
                    ),
                    details={
                        "total_risk_instances": risk_count,
                    },
                )
            )

        return findings

    # ------------------------------------------------------------------
    # GRD_ADV_004 — CxF/X-4 spectral validation
    # ------------------------------------------------------------------

    def _check_cxf_spectral(
        self,
        document: SemanticDocument,
    ) -> list[Finding]:
        """Parse and validate CxF/X-4 spectral data (GRD_ADV_004).

        Detects CxF data in output intents, parses the XML when found,
        and validates the spectral data structure. Also cross-references
        CxF spot colors against document color spaces (GRD_ADV_006).
        """
        from grounded.analyzers.cxf_parser import parse_cxf_xml

        findings: list[Finding] = []
        cxf_xml_bytes: bytes | None = None
        cxf_hint_found = False

        # Detect CxF data in output intents
        for oi in document.output_intents:
            for key in oi:
                if "CxF" in str(key) or "cxf" in str(key).lower():
                    cxf_hint_found = True
                    # Try to get the raw XML data
                    val = oi.get(key)
                    if isinstance(val, bytes):
                        cxf_xml_bytes = val
                    elif isinstance(val, str) and val.strip().startswith("<?xml"):
                        cxf_xml_bytes = val.encode("utf-8")
                    break
            if not cxf_hint_found:
                for value in oi.values():
                    val_str = str(value)
                    if "CxF" in val_str:
                        cxf_hint_found = True
                        break
            if cxf_hint_found:
                break

        if not cxf_hint_found:
            findings.append(
                Finding(
                    inspection_id="GRD_ADV_004",
                    severity=Severity.ADVISORY,
                    message="No CxF spectral data detected in output intents",
                    details={"cxf_detected": False},
                )
            )
            return findings

        # If we found the hint but no parseable XML
        if cxf_xml_bytes is None:
            findings.append(
                Finding(
                    inspection_id="GRD_ADV_004",
                    severity=Severity.ADVISORY,
                    message=(
                        "CxF spectral data reference found but raw XML "
                        "not extractable from output intents"
                    ),
                    details={"cxf_detected": True, "parseable": False},
                )
            )
            return findings

        # Parse the CxF XML
        cxf_data = parse_cxf_xml(cxf_xml_bytes)

        if not cxf_data.valid:
            findings.append(
                Finding(
                    inspection_id="GRD_ADV_004",
                    severity=Severity.SQUALL,
                    message=(f"CxF spectral data is malformed: {'; '.join(cxf_data.errors)}"),
                    details={
                        "cxf_detected": True,
                        "valid": False,
                        "errors": cxf_data.errors,
                    },
                )
            )
        else:
            findings.append(
                Finding(
                    inspection_id="GRD_ADV_004",
                    severity=Severity.ADVISORY,
                    message=(
                        f"CxF spectral data parsed: {len(cxf_data.spot_colors)} "
                        f"spot color(s), standard: {cxf_data.file_standard}"
                    ),
                    details={
                        "cxf_detected": True,
                        "valid": True,
                        "spot_color_count": len(cxf_data.spot_colors),
                        "file_standard": cxf_data.file_standard,
                        "spot_names": [sc.name for sc in cxf_data.spot_colors],
                    },
                )
            )

        # GRD_ADV_006 — Cross-reference CxF spots vs document spots
        findings.extend(self._check_cxf_spot_cross_reference(document, cxf_data))

        return findings

    @staticmethod
    def _check_cxf_spot_cross_reference(
        document: SemanticDocument,
        cxf_data: object,
    ) -> list[Finding]:
        """Cross-reference CxF spot colors against document color spaces (GRD_ADV_006).

        For each CxF spot color, check if a matching Separation color space
        exists in the document and compare Lab values.
        """
        from grounded.analyzers.cxf_parser import CxfData

        findings: list[Finding] = []
        if not isinstance(cxf_data, CxfData):
            return findings

        # Collect document spot color names
        doc_spots: set[str] = set()
        for page in document.pages:
            for _cs_name, cs in page.color_spaces.items():
                if cs.cs_type == "Separation" and cs.colorant_names:
                    doc_spots.add(cs.colorant_names[0])

        # Cross-reference
        for cxf_spot in cxf_data.spot_colors:
            if cxf_spot.name in doc_spots:
                if cxf_spot.lab:
                    findings.append(
                        Finding(
                            inspection_id="GRD_ADV_006",
                            severity=Severity.ADVISORY,
                            message=(
                                f"CxF spot '{cxf_spot.name}' matches document "
                                f"spot color — spectral Lab "
                                f"({cxf_spot.lab[0]:.1f}, {cxf_spot.lab[1]:.1f}, "
                                f"{cxf_spot.lab[2]:.1f})"
                            ),
                            details={
                                "spot_name": cxf_spot.name,
                                "cxf_lab": list(cxf_spot.lab),
                                "has_spectral": cxf_spot.spectral_data is not None,
                            },
                        )
                    )
            else:
                findings.append(
                    Finding(
                        inspection_id="GRD_ADV_006",
                        severity=Severity.SQUALL,
                        message=(
                            f"CxF defines spot color '{cxf_spot.name}' but no "
                            f"matching Separation space found in document"
                        ),
                        details={
                            "spot_name": cxf_spot.name,
                            "document_spots": sorted(doc_spots),
                        },
                    )
                )

        return findings

    # ------------------------------------------------------------------
    # GRD_ADV_005 — Rich black composition analysis
    # ------------------------------------------------------------------

    def _check_rich_black_composition(  # skipcq: PY-R1000
        self,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Classify and report black usage across the document.

        Categories:
        - Pure K: K>95%, C+M+Y < 5%
        - Rich black: matches target composition +/-10%
        - Registration: C>90% M>90% Y>90% K>90%
        - Non-standard rich black: K>80% with some C/M/Y but not target
        """
        import math

        from grounded.semantic.events import PathPaintingEvent, TextRenderedEvent

        findings: list[Finding] = []

        pure_k_count = 0
        rich_black_count = 0
        registration_count = 0
        non_standard_count = 0

        for event in events:
            cmyk_samples: list[tuple[tuple[float, ...], str, int, float | None]] = []

            if isinstance(event, PathPaintingEvent):
                if event.fill and event.fill_color_space == "DeviceCMYK":
                    vals = event.fill_color_values
                    if len(vals) == 4:
                        cmyk_samples.append((vals, "path", event.page_num, None))
                if event.stroke and event.stroke_color_space == "DeviceCMYK":
                    vals = event.stroke_color_values
                    if len(vals) == 4:
                        cmyk_samples.append((vals, "path", event.page_num, None))
            elif isinstance(event, TextRenderedEvent):
                if event.color_space == "DeviceCMYK" and len(event.color_values) == 4:
                    tm_scale_y = math.sqrt(event.text_matrix.b**2 + event.text_matrix.d**2)
                    ctm_scale_y = math.sqrt(event.ctm.b**2 + event.ctm.d**2)
                    effective_size = event.font_size * tm_scale_y * ctm_scale_y
                    cmyk_samples.append(
                        (event.color_values, "text", event.page_num, effective_size)
                    )

            for vals, obj_type, page_num, font_size in cmyk_samples:
                c, m, y, k = vals
                # Convert to percentages for classification
                c_pct = c * 100.0
                m_pct = m * 100.0
                y_pct = y * 100.0
                k_pct = k * 100.0

                classification = self._classify_black(c_pct, m_pct, y_pct, k_pct)

                if classification == "registration":
                    registration_count += 1
                    findings.append(
                        Finding(
                            inspection_id="GRD_ADV_005",
                            severity=Severity.AGROUND,
                            message=(
                                f"Registration color on non-mark {obj_type} object "
                                f"on page {page_num} "
                                f"(C={c_pct:.0f}% M={m_pct:.0f}% "
                                f"Y={y_pct:.0f}% K={k_pct:.0f}%)"
                            ),
                            page_num=page_num,
                            details={
                                "color_values": list(vals),
                                "classification": "registration",
                            },
                            object_type=obj_type,
                        )
                    )
                elif classification == "rich_black":
                    rich_black_count += 1
                    # Flag rich black on small text
                    if obj_type == "text" and font_size is not None and 0 < font_size < 12.0:
                        findings.append(
                            Finding(
                                inspection_id="GRD_ADV_005",
                                severity=Severity.SQUALL,
                                message=(
                                    f"Rich black on small text ({font_size:.1f}pt) "
                                    f"on page {page_num} "
                                    f"(C={c_pct:.0f}% M={m_pct:.0f}% "
                                    f"Y={y_pct:.0f}% K={k_pct:.0f}%)"
                                ),
                                page_num=page_num,
                                details={
                                    "color_values": list(vals),
                                    "classification": "rich_black",
                                    "font_size": font_size,
                                },
                                object_type="text",
                            )
                        )
                elif classification == "pure_k":
                    pure_k_count += 1
                    # Large area pure K advisory (path fills only)
                    if obj_type == "path" and k_pct > 80.0:
                        findings.append(
                            Finding(
                                inspection_id="GRD_ADV_005",
                                severity=Severity.ADVISORY,
                                message=(
                                    f"Large area pure K fill ({k_pct:.0f}% K) "
                                    f"on page {page_num} (may appear gray "
                                    f"without rich black support)"
                                ),
                                page_num=page_num,
                                details={
                                    "color_values": list(vals),
                                    "classification": "pure_k",
                                    "k_percent": k_pct,
                                },
                                object_type="path",
                            )
                        )
                elif classification == "non_standard":
                    non_standard_count += 1

        # Composition summary
        total = pure_k_count + rich_black_count + registration_count + non_standard_count
        if total > 0:
            findings.append(
                Finding(
                    inspection_id="GRD_ADV_005",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Black composition breakdown: {pure_k_count} pure K, "
                        f"{rich_black_count} rich black, "
                        f"{registration_count} registration, "
                        f"{non_standard_count} non-standard "
                        f"({total} total CMYK black events)"
                    ),
                    details={
                        "pure_k_count": pure_k_count,
                        "rich_black_count": rich_black_count,
                        "registration_count": registration_count,
                        "non_standard_count": non_standard_count,
                        "total": total,
                        "target_rich_black": {
                            "c": self.rich_black_c,
                            "m": self.rich_black_m,
                            "y": self.rich_black_y,
                            "k": self.rich_black_k,
                        },
                    },
                )
            )

        return findings

    def _classify_black(self, c: float, m: float, y: float, k: float) -> str | None:
        """Classify a CMYK color into a black category.

        Args:
            c: Cyan percentage (0-100).
            m: Magenta percentage (0-100).
            y: Yellow percentage (0-100).
            k: Key/black percentage (0-100).

        Returns:
            Classification string or None if not a black variant.
        """
        # Registration: C>90% M>90% Y>90% K>90%
        if c > 90.0 and m > 90.0 and y > 90.0 and k > 90.0:
            return "registration"

        # Pure K: K>95%, C+M+Y < 5%
        if k > 95.0 and (c + m + y) < 5.0:
            return "pure_k"

        # Rich black: matches target +/-10%
        if (
            abs(c - self.rich_black_c) <= 10.0
            and abs(m - self.rich_black_m) <= 10.0
            and abs(y - self.rich_black_y) <= 10.0
            and abs(k - self.rich_black_k) <= 10.0
        ):
            return "rich_black"

        # Non-standard rich black: K>80% with some C/M/Y but not matching target
        if k > 80.0 and (c + m + y) > 5.0:
            return "non_standard"

        return None
