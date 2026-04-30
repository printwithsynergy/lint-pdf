"""AdvancedColorAnalyzer — GCR/UCR profiling, ink savings, trapping, CxF, rich black.

Performs advanced color analysis beyond basic TAC and prohibited space checks,
focusing on production-level ink optimization and print quality concerns.

Check IDs:
    LPDF_ADV_001 — Black generation profiling (GCR/UCR strategy detection)
    LPDF_ADV_002 — Ink savings estimation (GCR headroom in CMYK fills)
    LPDF_ADV_003 — Trapping risk analysis (small multicolor text)
    LPDF_ADV_004 — CxF/X-4 spectral validation (CxF data parsing)
    LPDF_ADV_005 — Rich black composition analysis (black usage classification)
    LPDF_ADV_006 — CxF spectral vs declared color Delta-E
    LPDF_ADV_007 — CxF data present (informational)
    LPDF_ADV_008 — CxF spectral range incomplete (380-730nm coverage)
    LPDF_ADV_009 — CxF measurement geometry missing
    LPDF_ADV_010 — CxF illuminant mismatch with output intent
    LPDF_ADV_011 — CxF non-standard observer angle
    LPDF_ADV_012 — Spectral vs colorimetric Delta-E exceeds threshold
    LPDF_ADV_013 — CxF color library reference detected
    LPDF_ADV_014 — CxF substrate measurement present
    LPDF_ADV_015 — CxF version compatibility check
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# WS-8: pixel threshold for the "is the declared pure-K fill
# actually visible on the rendered page?" gate. A composited
# grayscale render at 72 DPI is thresholded at ``<= 15`` (roughly
# 94% dark). If less than 2% of the page pixels are that dark,
# the declared pure-K objects aren't contributing visible ink
# and the advisory is suppressed. Calibrated against the
# 2026-04-23 Opus audit's Pink-Slush false positives where 1,256
# declared pure-K events produced no visible dark patch.
_WS8_DARK_THRESHOLD = 15
_WS8_MIN_DARK_FRACTION = 0.02
_WS8_RENDER_DPI = 72


def _dark_ink_fraction(pdf_bytes: bytes | None, page_num: int) -> float | None:
    """Return the fraction of rendered pixels that are nearly
    black (grayscale <= ``_WS8_DARK_THRESHOLD``), or ``None`` when
    the render / analysis can't run (no bytes supplied, renderer
    missing, PIL / numpy unavailable, exception). Callers treat
    ``None`` as "unknown -> emit the advisory anyway" so the
    pixel gate degrades gracefully.
    """
    if pdf_bytes is None or page_num <= 0:
        return None
    try:
        from io import BytesIO

        from PIL import Image

        from lintpdf.rendering import render_page_to_image
    except Exception:
        logger.debug("WS-8 pixel gate disabled: rendering stack unavailable")
        return None
    try:
        import numpy as np
    except Exception:
        logger.debug("WS-8 pixel gate disabled: numpy unavailable")
        return None
    try:
        png = render_page_to_image(
            pdf_bytes, page_num, dpi=_WS8_RENDER_DPI, simulate_overprint=True
        )
    except Exception:
        logger.debug(
            "WS-8 pixel gate: render_page_to_image failed for page %d",
            page_num,
        )
        return None
    try:
        img = Image.open(BytesIO(png)).convert("L")
        arr = np.asarray(img, dtype=np.uint8)
    except Exception:
        logger.debug("WS-8 pixel gate: image decode failed for page %d", page_num)
        return None
    if arr.size == 0:
        return None
    dark_mask = arr <= _WS8_DARK_THRESHOLD
    # ``.mean()`` on a boolean array returns the fraction of True
    # entries, which is exactly the "fraction of dark pixels"
    # metric the gate wants.
    return float(dark_mask.mean())


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
        spectral_delta_e_threshold: float = 2.0,
        *,
        brand_palette_present: bool = False,
        pdf_bytes: bytes | None = None,
    ) -> None:
        self.rich_black_c = rich_black_c
        self.rich_black_m = rich_black_m
        self.rich_black_y = rich_black_y
        self.rich_black_k = rich_black_k
        self._spectral_delta_e_threshold = spectral_delta_e_threshold
        # See ColorAnalyzer for the rationale -- the LPDF_ADV_005
        # "large area pure K fill" advisory is ambiguous without a
        # brand rich-black spec; suppress when the tenant hasn't
        # declared one.
        self.brand_palette_present = brand_palette_present
        # WS-8: pixel-composited large-K gate. When the page render
        # shows < 2% dark coverage the declared pure-K fills aren't
        # actually contributing visible ink (covered / knocked out
        # by other artwork), so the advisory is false-positive for
        # this page. ``pdf_bytes`` is threaded through by the
        # orchestrator; analyzers run outside the pipeline (tests)
        # pass ``None`` and get the vector-only behaviour.
        self._pdf_bytes = pdf_bytes

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
        findings.extend(self._check_cxf_data_present(document))
        findings.extend(self._check_cxf_spectral_range(document))
        findings.extend(self._check_cxf_measurement_geometry(document))
        findings.extend(self._check_cxf_illuminant_mismatch(document))
        findings.extend(self._check_cxf_observer_angle(document))
        findings.extend(self._check_spectral_colorimetric_delta_e(document))
        findings.extend(self._check_cxf_library_reference(document))
        findings.extend(self._check_cxf_substrate_measurement(document))
        findings.extend(self._check_cxf_version_compatibility(document))

        return findings

    # ------------------------------------------------------------------
    # LPDF_ADV_001 — Black generation profiling
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
                            inspection_id="LPDF_ADV_001",
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
    # LPDF_ADV_002 — Ink savings estimation
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
        from lintpdf.semantic.events import PathPaintingEvent

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
                    inspection_id="LPDF_ADV_002",
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
    # LPDF_ADV_003 — Trapping risk analysis
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

        from lintpdf.semantic.events import TextRenderedEvent

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
                        inspection_id="LPDF_ADV_003",
                        severity=Severity.WARNING,
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
                    inspection_id="LPDF_ADV_003",
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
    # LPDF_ADV_004 — CxF/X-4 spectral validation
    # ------------------------------------------------------------------

    def _check_cxf_spectral(
        self,
        document: SemanticDocument,
    ) -> list[Finding]:
        """Parse and validate CxF/X-4 spectral data (LPDF_ADV_004).

        Detects CxF data in output intents, parses the XML when found,
        and validates the spectral data structure. Also cross-references
        CxF spot colors against document color spaces (LPDF_ADV_006).
        """
        from lintpdf.analyzers.cxf_parser import parse_cxf_xml

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
                    inspection_id="LPDF_ADV_004",
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
                    inspection_id="LPDF_ADV_004",
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
                    inspection_id="LPDF_ADV_004",
                    severity=Severity.WARNING,
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
                    inspection_id="LPDF_ADV_004",
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

        # LPDF_ADV_006 — Cross-reference CxF spots vs document spots
        findings.extend(self._check_cxf_spot_cross_reference(document, cxf_data))

        return findings

    @staticmethod
    def _check_cxf_spot_cross_reference(
        document: SemanticDocument,
        cxf_data: object,
    ) -> list[Finding]:
        """Cross-reference CxF spot colors against document color spaces (LPDF_ADV_006).

        For each CxF spot color, check if a matching Separation color space
        exists in the document and compare Lab values.
        """
        from lintpdf.analyzers.cxf_parser import CxfData

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
                            inspection_id="LPDF_ADV_006",
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
                        inspection_id="LPDF_ADV_006",
                        severity=Severity.WARNING,
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
    # LPDF_ADV_005 — Rich black composition analysis
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

        from lintpdf.semantic.events import PathPaintingEvent, TextRenderedEvent

        findings: list[Finding] = []

        pure_k_count = 0
        rich_black_count = 0
        registration_count = 0
        non_standard_count = 0
        # WS-7 per-page aggregator for the large-area pure-K
        # advisory. Old emit fires one finding per matching
        # PathPaintingEvent; on vector-dense artwork that explodes
        # to 1,256 findings on a single page. Collect hits into
        # {page_num: {count, max_k_percent, bboxes}} and emit one
        # aggregate after the event loop.
        large_k_agg: dict[int, dict[str, object]] = {}

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
                            inspection_id="LPDF_ADV_005",
                            severity=Severity.ERROR,
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
                                inspection_id="LPDF_ADV_005",
                                severity=Severity.WARNING,
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
                    # Large area pure K advisory (path fills only).
                    # WS-7: accumulate per page; emit one aggregate
                    # at the end instead of one per object. Skip
                    # entirely when no brand palette is configured
                    # -- the rule is ambiguous without one.
                    if obj_type == "path" and k_pct > 80.0 and self.brand_palette_present:
                        bucket = large_k_agg.get(page_num)
                        if bucket is None:
                            bucket = {
                                "count": 0,
                                "max_k_percent": 0.0,
                                "bboxes": [],
                            }
                            large_k_agg[page_num] = bucket
                        bucket["count"] = int(bucket["count"]) + 1  # type: ignore[arg-type]
                        if k_pct > float(bucket["max_k_percent"]):  # type: ignore[arg-type]
                            bucket["max_k_percent"] = k_pct
                        bboxes = bucket["bboxes"]
                        if isinstance(bboxes, list) and len(bboxes) < 5:
                            bbox = getattr(event, "bbox", None)
                            if bbox:
                                bboxes.append(list(bbox))
                elif classification == "non_standard":
                    non_standard_count += 1

        # WS-7: emit one LPDF_ADV_005 large-K advisory per page that
        # collected any hits, with object_count + max_k_percent +
        # representative bboxes on the finding's details so callers
        # can still drill in without drowning the viewer.
        # WS-8: before emitting, re-check each candidate page against
        # the composited render. Declared pure-K fills may be
        # knocked out or covered by other artwork -- if the rendered
        # page shows < 2% dark-ink coverage there's no visible K
        # patch for the customer to act on. Gracefully degrade to
        # the vector-only emit when the pixel check isn't available
        # (no pdf_bytes, Ghostscript / pdftoppm missing, render
        # error), since over-reporting is better than silent misses.
        for page_num in sorted(large_k_agg):
            bucket = large_k_agg[page_num]
            count = int(bucket["count"])  # type: ignore[arg-type]
            if count <= 0:
                continue
            max_k = float(bucket["max_k_percent"])  # type: ignore[arg-type]
            rendered_dark_fraction = _dark_ink_fraction(self._pdf_bytes, page_num)
            if (
                rendered_dark_fraction is not None
                and rendered_dark_fraction < _WS8_MIN_DARK_FRACTION
            ):
                # Pixel check says the declared fills aren't
                # visibly dark on the final page. Suppress.
                continue
            details: dict[str, object] = {
                "classification": "pure_k",
                "object_count": count,
                "max_k_percent": max_k,
                "representative_bboxes": bucket["bboxes"],
            }
            if rendered_dark_fraction is not None:
                details["rendered_dark_fraction"] = round(rendered_dark_fraction, 4)
            findings.append(
                Finding(
                    inspection_id="LPDF_ADV_005",
                    severity=Severity.ADVISORY,
                    message=(
                        f"{count} large-area pure K fill{'s' if count != 1 else ''} "
                        f"(max {max_k:.0f}% K) on page {page_num} "
                        f"(may appear gray without rich black support)"
                    ),
                    page_num=page_num,
                    details=details,
                    object_type="path",
                )
            )

        # Composition summary
        total = pure_k_count + rich_black_count + registration_count + non_standard_count
        if total > 0:
            findings.append(
                Finding(
                    inspection_id="LPDF_ADV_005",
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

    # ------------------------------------------------------------------
    # LPDF_ADV_007 — CxF data present (informational)
    # ------------------------------------------------------------------

    @staticmethod
    def _check_cxf_data_present(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Report when CxF spectral data is embedded in the document (LPDF_ADV_007).

        Scans output intents for any CxF reference and emits an
        informational finding when detected.
        """
        findings: list[Finding] = []

        for oi in document.output_intents:
            for key in oi:
                if "CxF" in str(key) or "cxf" in str(key).lower():
                    findings.append(
                        Finding(
                            inspection_id="LPDF_ADV_007",
                            severity=Severity.ADVISORY,
                            message="CxF spectral data is embedded in the document",
                            details={"cxf_key": str(key)},
                        )
                    )
                    return findings
            for value in oi.values():
                if "CxF" in str(value):
                    findings.append(
                        Finding(
                            inspection_id="LPDF_ADV_007",
                            severity=Severity.ADVISORY,
                            message="CxF spectral data is embedded in the document",
                            details={"cxf_detected_in_value": True},
                        )
                    )
                    return findings

        return findings

    # ------------------------------------------------------------------
    # LPDF_ADV_008 — CxF spectral range incomplete
    # ------------------------------------------------------------------

    @staticmethod
    def _check_cxf_spectral_range(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Flag CxF spectral data that doesn't cover 380-730nm (LPDF_ADV_008).

        Parses CxF XML from output intents and checks that the wavelength
        range spans at least 380nm to 730nm.
        """

        findings: list[Finding] = []
        cxf_data = _extract_cxf_data(document)
        if cxf_data is None or not cxf_data.valid:
            return findings

        for spot in cxf_data.spot_colors:
            if spot.spectral_data is None:
                continue

            wavelengths = sorted(spot.spectral_data.keys())
            if not wavelengths:
                continue

            min_wl = wavelengths[0]
            max_wl = wavelengths[-1]

            if min_wl > 380 or max_wl < 730:
                findings.append(
                    Finding(
                        inspection_id="LPDF_ADV_008",
                        severity=Severity.WARNING,
                        message=(
                            f"CxF spectral range for '{spot.name}' is "
                            f"{min_wl}-{max_wl}nm, does not cover "
                            f"required 380-730nm"
                        ),
                        details={
                            "spot_name": spot.name,
                            "min_wavelength": min_wl,
                            "max_wavelength": max_wl,
                            "required_min": 380,
                            "required_max": 730,
                        },
                    )
                )

        return findings

    # ------------------------------------------------------------------
    # LPDF_ADV_009 — CxF measurement geometry missing
    # ------------------------------------------------------------------

    @staticmethod
    def _check_cxf_measurement_geometry(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Flag CxF data without measurement geometry specification (LPDF_ADV_009).

        Checks for the presence of /MeasurementGeometry or equivalent
        attribute in the CxF spectral data.
        """
        findings: list[Finding] = []
        cxf_data = _extract_cxf_data(document)
        if cxf_data is None or not cxf_data.valid:
            return findings

        if not cxf_data.measurement_geometry:
            findings.append(
                Finding(
                    inspection_id="LPDF_ADV_009",
                    severity=Severity.ADVISORY,
                    message=(
                        "CxF spectral data does not specify measurement geometry (e.g., 45/0, d/8)"
                    ),
                    details={"measurement_geometry": None},
                )
            )

        return findings

    # ------------------------------------------------------------------
    # LPDF_ADV_010 — CxF illuminant mismatch
    # ------------------------------------------------------------------

    @staticmethod
    def _check_cxf_illuminant_mismatch(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Flag CxF illuminant that doesn't match output intent (LPDF_ADV_010).

        Compares the illuminant specified in CxF data against the
        output intent's rendering condition illuminant.
        """
        findings: list[Finding] = []
        cxf_data = _extract_cxf_data(document)
        if cxf_data is None or not cxf_data.valid:
            return findings

        cxf_illuminant = cxf_data.illuminant
        if not cxf_illuminant:
            return findings

        # Extract output intent illuminant from document
        oi_illuminant: str | None = None
        for oi in document.output_intents:
            for key, value in oi.items():
                key_str = str(key).lower()
                if "illuminant" in key_str:
                    oi_illuminant = str(value)
                    break
            if oi_illuminant:
                break

        if oi_illuminant and cxf_illuminant.upper() != oi_illuminant.upper():
            findings.append(
                Finding(
                    inspection_id="LPDF_ADV_010",
                    severity=Severity.ADVISORY,
                    message=(
                        f"CxF illuminant '{cxf_illuminant}' does not match "
                        f"output intent illuminant '{oi_illuminant}'"
                    ),
                    details={
                        "cxf_illuminant": cxf_illuminant,
                        "output_intent_illuminant": oi_illuminant,
                    },
                )
            )

        return findings

    # ------------------------------------------------------------------
    # LPDF_ADV_011 — CxF non-standard observer angle
    # ------------------------------------------------------------------

    @staticmethod
    def _check_cxf_observer_angle(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Flag non-standard observer angle in CxF data (LPDF_ADV_011).

        Standard observer angles are 2 degrees and 10 degrees.
        """
        findings: list[Finding] = []
        cxf_data = _extract_cxf_data(document)
        if cxf_data is None or not cxf_data.valid:
            return findings

        observer = cxf_data.observer_angle
        if observer is None:
            return findings

        standard_angles = {2, 10}
        if observer not in standard_angles:
            findings.append(
                Finding(
                    inspection_id="LPDF_ADV_011",
                    severity=Severity.ADVISORY,
                    message=(
                        f"CxF observer angle {observer}\u00b0 is non-standard "
                        f"(expected 2\u00b0 or 10\u00b0)"
                    ),
                    details={
                        "observer_angle": observer,
                        "standard_angles": sorted(standard_angles),
                    },
                )
            )

        return findings

    # ------------------------------------------------------------------
    # LPDF_ADV_012 — Spectral vs colorimetric Delta-E exceeds threshold
    # ------------------------------------------------------------------

    def _check_spectral_colorimetric_delta_e(
        self,
        document: SemanticDocument,
    ) -> list[Finding]:
        """Flag when spectral and colorimetric values diverge (LPDF_ADV_012).

        For CxF spot colors that have both spectral data and Lab values,
        computes the Delta-E between spectral-derived Lab and declared Lab.
        """
        findings: list[Finding] = []
        cxf_data = _extract_cxf_data(document)
        if cxf_data is None or not cxf_data.valid:
            return findings

        for spot in cxf_data.spot_colors:
            if spot.spectral_data is None or spot.lab is None:
                continue
            if spot.spectral_lab is None:
                continue

            # CIEDE2000 simplified as Euclidean for structural purposes
            dL = spot.spectral_lab[0] - spot.lab[0]
            da = spot.spectral_lab[1] - spot.lab[1]
            db = spot.spectral_lab[2] - spot.lab[2]
            delta_e = (dL**2 + da**2 + db**2) ** 0.5

            if delta_e > self._spectral_delta_e_threshold:
                findings.append(
                    Finding(
                        inspection_id="LPDF_ADV_012",
                        severity=Severity.WARNING,
                        message=(
                            f"CxF spot '{spot.name}' spectral vs colorimetric "
                            f"Delta-E = {delta_e:.2f} exceeds threshold "
                            f"{self._spectral_delta_e_threshold}"
                        ),
                        details={
                            "spot_name": spot.name,
                            "delta_e": delta_e,
                            "threshold": self._spectral_delta_e_threshold,
                            "spectral_lab": list(spot.spectral_lab),
                            "declared_lab": list(spot.lab),
                        },
                    )
                )

        return findings

    # ------------------------------------------------------------------
    # LPDF_ADV_013 — CxF color library reference
    # ------------------------------------------------------------------

    @staticmethod
    def _check_cxf_library_reference(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Report CxF data that references a known color library (LPDF_ADV_013).

        Checks CxF spot color names against known library prefixes
        (PANTONE, HKS, TOYO, DIC, RAL).
        """
        findings: list[Finding] = []
        cxf_data = _extract_cxf_data(document)
        if cxf_data is None or not cxf_data.valid:
            return findings

        known_prefixes = ("PANTONE", "HKS", "TOYO", "DIC", "RAL")

        for spot in cxf_data.spot_colors:
            # Strip leading slash / whitespace / ® / ™ before matching —
            # "/Pantone® 485 C" must still classify as PANTONE.
            upper_name = (
                str(spot.name or "")
                .strip()
                .lstrip("/")
                .strip()
                .replace(" ", " ")
                .replace("®", "")
                .replace("™", "")
                .upper()
            )
            for prefix in known_prefixes:
                if upper_name.startswith(prefix):
                    findings.append(
                        Finding(
                            inspection_id="LPDF_ADV_013",
                            severity=Severity.ADVISORY,
                            message=(
                                f"CxF spectral data references {prefix} library color '{spot.name}'"
                            ),
                            details={
                                "spot_name": spot.name,
                                "library": prefix,
                            },
                        )
                    )
                    break

        return findings

    # ------------------------------------------------------------------
    # LPDF_ADV_014 — CxF substrate measurement present
    # ------------------------------------------------------------------

    @staticmethod
    def _check_cxf_substrate_measurement(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Report when CxF data includes substrate white measurement (LPDF_ADV_014).

        Substrate measurements are used for paper-relative color
        calculations and are a quality indicator for spectral data.
        """
        findings: list[Finding] = []
        cxf_data = _extract_cxf_data(document)
        if cxf_data is None or not cxf_data.valid:
            return findings

        if cxf_data.substrate_measurement:
            findings.append(
                Finding(
                    inspection_id="LPDF_ADV_014",
                    severity=Severity.ADVISORY,
                    message=("CxF spectral data includes substrate (paper white) measurement"),
                    details={
                        "substrate_measurement": True,
                    },
                )
            )

        return findings

    # ------------------------------------------------------------------
    # LPDF_ADV_015 — CxF version compatibility
    # ------------------------------------------------------------------

    @staticmethod
    def _check_cxf_version_compatibility(
        document: SemanticDocument,
    ) -> list[Finding]:
        """Check CxF version for compatibility (LPDF_ADV_015).

        Validates that the CxF version is compatible with processing
        software (supports CxF/X-4 a.k.a. CxF3).
        """
        findings: list[Finding] = []
        cxf_data = _extract_cxf_data(document)
        if cxf_data is None or not cxf_data.valid:
            return findings

        version = cxf_data.version
        if not version:
            findings.append(
                Finding(
                    inspection_id="LPDF_ADV_015",
                    severity=Severity.ADVISORY,
                    message="CxF data does not specify a version number",
                    details={"version": None},
                )
            )
            return findings

        supported_versions = {"3", "3.0", "CxF3"}
        if version not in supported_versions:
            findings.append(
                Finding(
                    inspection_id="LPDF_ADV_015",
                    severity=Severity.ADVISORY,
                    message=(
                        f"CxF version '{version}' may not be fully "
                        f"compatible (supported: {', '.join(sorted(supported_versions))})"
                    ),
                    details={
                        "version": version,
                        "supported_versions": sorted(supported_versions),
                    },
                )
            )

        return findings


def _extract_cxf_data(document: SemanticDocument) -> object | None:
    """Extract and parse CxF data from document output intents.

    Returns a CxfData object if CxF XML is found and parseable, else None.
    """
    from lintpdf.analyzers.cxf_parser import parse_cxf_xml

    for oi in document.output_intents:
        for key in oi:
            if "CxF" in str(key) or "cxf" in str(key).lower():
                val = oi.get(key)
                if isinstance(val, bytes):
                    return parse_cxf_xml(val)
                if isinstance(val, str) and val.strip().startswith("<?xml"):
                    return parse_cxf_xml(val.encode("utf-8"))
        for value in oi.values():
            val_str = str(value)
            if "CxF" in val_str and val_str.strip().startswith("<?xml"):
                return parse_cxf_xml(val_str.encode("utf-8"))

    return None
