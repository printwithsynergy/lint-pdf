"""HairlineAnalyzer — thin stroke, zero-width, and small text detection.

Processes PathPaintingEvent and TextRenderedEvent events to detect
hairlines and small text that may not reproduce in print.

Check IDs:
    LPDF_STROKE_001 — Hairline stroke (<0.25pt effective)
    LPDF_STROKE_002 — Zero-width stroke
    LPDF_STROKE_003 — Butt cap on thin stroke (<0.5pt)
    LPDF_STROKE_004 — Multi-ink thin stroke (<0.5pt, >1 CMYK separation)
    LPDF_STROKE_005 — Invisible line art (zero opacity stroke)
    LPDF_STROKE_006 — Flatness tolerance override
    LPDF_STROKE_007 — Multi-ink stroke (0.5-1.0pt, >1 CMYK separation) — advisory
    LPDF_PATH_001 — Excessive path points (>10,000)
    LPDF_PATH_002 — White fill detected on paths
    LPDF_TEXT_001 — Small text (<6pt effective)
    LPDF_TEXT_002 — Very small text (<4pt effective)
    LPDF_TEXT_003 — Invisible text (rendering mode 3)
    LPDF_TEXT_004 — White text detected
    LPDF_TEXT_005 — Text on registration color
    LPDF_TEXT_006 — Small multi-ink text (<8pt, >1 separation)
    LPDF_TEXT_REVERSE_THIN — Small white (reverse / knockout) text rendered
        without a stroke; needs ≥0.5pt stroke for legibility (T2-RB02)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent, PathPaintingEvent, TextRenderedEvent
    from lintpdf.semantic.model import SemanticDocument

# Default thresholds
HAIRLINE_THRESHOLD = 0.25  # Points
THIN_STROKE_THRESHOLD = 0.5  # Points (for butt cap warning)
SMALL_TEXT_THRESHOLD = 6.0  # Points
VERY_SMALL_TEXT_THRESHOLD = 4.0  # Points


class HairlineAnalyzer(BaseAnalyzer):
    """Analyzer for thin strokes and small text.

    Args:
        hairline_threshold: Minimum stroke width in points (default 0.25).
        small_text_threshold: Text size advisory threshold (default 6.0).
        very_small_text_threshold: Text size warning threshold (default 4.0).
    """

    def __init__(
        self,
        hairline_threshold: float = HAIRLINE_THRESHOLD,
        small_text_threshold: float = SMALL_TEXT_THRESHOLD,
        very_small_text_threshold: float = VERY_SMALL_TEXT_THRESHOLD,
    ) -> None:
        self.hairline_threshold = hairline_threshold
        self.small_text_threshold = small_text_threshold
        self.very_small_text_threshold = very_small_text_threshold

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze stroke widths and text sizes."""
        from lintpdf.semantic.events import PathPaintingEvent, TextRenderedEvent

        findings: list[Finding] = []

        white_fill_pages: set[int] = set()

        # WS-14 per-page aggregation buckets. On a 10-up repeat layout
        # the same small-text defect fires ~228 times; on white text
        # it fires ~290 times. Collapse to one aggregate per (page,
        # rule) so the viewer's findings panel stays usable — the
        # underlying defect still surfaces, just with count + sample
        # bboxes inside ``details``.
        text001_agg: dict[int, dict[str, object]] = {}
        text004_agg: dict[int, dict[str, object]] = {}

        for event in events:
            if isinstance(event, PathPaintingEvent):
                if event.stroke:
                    findings.extend(self._check_stroke(event))

                # LPDF_PATH_002: White fill detected on paths
                if event.page_num not in white_fill_pages:
                    result = self._check_white_fill(event)
                    if result:
                        findings.append(result)
                        white_fill_pages.add(event.page_num)

                # LPDF_PATH_001: Excessive path points
                if event.point_count > 10000:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_PATH_001",
                            severity=Severity.WARNING,
                            message=(
                                f"Excessive path points ({event.point_count:,}) "
                                f"on page {event.page_num} "
                                f"(may cause RIP slowdown or failure)"
                            ),
                            page_num=event.page_num,
                            details={
                                "point_count": event.point_count,
                                "operator": event.operator,
                            },
                            object_type="path",
                            bbox=event.bbox,
                        )
                    )
            elif isinstance(event, TextRenderedEvent):
                findings.extend(self._check_text_size(event, text001_agg, text004_agg))

        findings.extend(self._emit_text001_aggregates(text001_agg))
        findings.extend(self._emit_text004_aggregates(text004_agg))

        return findings

    def _check_stroke(self, event: PathPaintingEvent) -> list[Finding]:  # skipcq: PY-R1000
        """Check stroke width for hairline issues."""
        findings: list[Finding] = []
        line_width = event.line_width

        # LPDF_STROKE_002: Zero-width stroke
        if line_width <= 0.0:
            findings.append(
                Finding(
                    inspection_id="LPDF_STROKE_002",
                    severity=Severity.ERROR,
                    message=(
                        f"Zero-width stroke on page {event.page_num} (will not render in print)"
                    ),
                    page_num=event.page_num,
                    details={
                        "line_width": line_width,
                        "operator": event.operator,
                    },
                    iso_clause="ISO 32000-2:2020 8.4.3.2",
                    object_type="path",
                    bbox=event.bbox,
                )
            )
            return findings

        # LPDF_STROKE_001: Hairline stroke
        if line_width < self.hairline_threshold:
            findings.append(
                Finding(
                    inspection_id="LPDF_STROKE_001",
                    severity=Severity.WARNING,
                    message=(
                        f"Hairline stroke ({line_width:.3f}pt) on page {event.page_num} "
                        f"(below {self.hairline_threshold}pt minimum)"
                    ),
                    page_num=event.page_num,
                    details={
                        "line_width": line_width,
                        "threshold": self.hairline_threshold,
                    },
                    iso_clause="ISO 32000-2:2020 8.4.3.2",
                    object_type="path",
                    bbox=event.bbox,
                )
            )

        # LPDF_STROKE_003: Butt cap on thin stroke
        if line_width < THIN_STROKE_THRESHOLD and event.line_cap == 0:
            findings.append(
                Finding(
                    inspection_id="LPDF_STROKE_003",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Butt cap on thin stroke ({line_width:.3f}pt) "
                        f"on page {event.page_num} "
                        f"(round cap recommended for thin lines)"
                    ),
                    page_num=event.page_num,
                    details={
                        "line_width": line_width,
                        "line_cap": event.line_cap,
                    },
                    object_type="path",
                    bbox=event.bbox,
                )
            )

        # LPDF_STROKE_004 / LPDF_STROKE_007 — multi-ink stroke checks
        # on CMYK paths. _004 is the warning at < 0.5pt (existing).
        # _007 is the advisory for 0.5pt–1.0pt strokes, capturing
        # the broader "thin elements shouldn't be rich black"
        # principle without drowning the findings panel on thicker
        # artwork.
        if event.stroke_color_space == "DeviceCMYK" and len(event.stroke_color_values) == 4:
            non_zero = sum(1 for v in event.stroke_color_values if v > 0.01)
            if non_zero > 1:
                multi_ink_details = {
                    "line_width": line_width,
                    "stroke_color_values": list(event.stroke_color_values),
                    "non_zero_inks": non_zero,
                }
                if line_width < THIN_STROKE_THRESHOLD:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_STROKE_004",
                            severity=Severity.WARNING,
                            message=(
                                f"Multi-ink thin stroke ({line_width:.3f}pt, "
                                f"{non_zero} inks) on page {event.page_num} "
                                f"(risk of misregistration on thin lines)"
                            ),
                            page_num=event.page_num,
                            details=multi_ink_details,
                            object_type="path",
                            bbox=event.bbox,
                        )
                    )
                elif line_width <= 1.0:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_STROKE_007",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Multi-ink stroke ({line_width:.3f}pt, "
                                f"{non_zero} inks) on page {event.page_num} "
                                f"— pure K (or a single spot) prints cleaner "
                                f"on thin lines."
                            ),
                            page_num=event.page_num,
                            details=multi_ink_details,
                            object_type="path",
                            bbox=event.bbox,
                        )
                    )

        # LPDF_STROKE_005: Invisible line art (zero opacity stroke)
        stroke_alpha = getattr(event, "stroke_alpha", None)
        if stroke_alpha is not None and abs(stroke_alpha) < 1e-6:
            findings.append(
                Finding(
                    inspection_id="LPDF_STROKE_005",
                    severity=Severity.WARNING,
                    message=(
                        f"Invisible stroke (white/zero-opacity) on page {event.page_num} "
                        f"(renders as white line art)"
                    ),
                    page_num=event.page_num,
                    details={
                        "stroke_alpha": stroke_alpha,
                        "line_width": line_width,
                    },
                    object_type="path",
                    bbox=event.bbox,
                )
            )
        elif stroke_alpha is None and line_width > 0:
            # Fallback: check if stroke is white
            stroke_cs = getattr(event, "stroke_color_space", None)
            stroke_cv = getattr(event, "stroke_color_values", None)
            if (
                stroke_cs == "DeviceGray"
                and stroke_cv is not None
                and len(stroke_cv) == 1
                and all(abs(v - 1.0) < 0.01 for v in stroke_cv)
            ):
                findings.append(
                    Finding(
                        inspection_id="LPDF_STROKE_005",
                        severity=Severity.WARNING,
                        message=(
                            f"Invisible stroke (white/zero-opacity) on page {event.page_num} "
                            f"(renders as white line art)"
                        ),
                        page_num=event.page_num,
                        details={
                            "stroke_color_space": stroke_cs,
                            "stroke_color_values": list(stroke_cv),
                            "line_width": line_width,
                        },
                        object_type="path",
                        bbox=event.bbox,
                    )
                )

        # LPDF_STROKE_006: Flatness tolerance override
        flatness = getattr(event, "flatness", None)
        if flatness is not None and flatness != 0 and flatness != 1.0:
            findings.append(
                Finding(
                    inspection_id="LPDF_STROKE_006",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Non-default flatness tolerance ({flatness}) on page {event.page_num} "
                        f"(may affect curve rendering quality)"
                    ),
                    page_num=event.page_num,
                    details={
                        "flatness": flatness,
                    },
                    object_type="path",
                    bbox=event.bbox,
                )
            )

        return findings

    def _check_white_fill(self, event: PathPaintingEvent) -> Finding | None:
        """Check if a path has a white fill (LPDF_PATH_002)."""
        if not getattr(event, "fill", False):
            return None
        fill_cs = getattr(event, "fill_color_space", None)
        fill_cv = getattr(event, "fill_color_values", None)
        if fill_cs is None or fill_cv is None:
            return None
        if self._is_white_color(fill_cs, tuple(fill_cv)):
            return Finding(
                inspection_id="LPDF_PATH_002",
                severity=Severity.ADVISORY,
                message=(
                    f"White fill path on page {event.page_num} (may knock out background content)"
                ),
                page_num=event.page_num,
                details={
                    "fill_color_space": fill_cs,
                    "fill_color_values": list(fill_cv),
                },
                object_type="path",
                bbox=event.bbox,
            )
        return None

    @staticmethod
    def _is_white_color(color_space: str, color_values: tuple[float, ...]) -> bool:
        """Check if color values represent white."""
        if color_space == "DeviceGray" and len(color_values) == 1:
            return color_values[0] > 0.99
        if color_space == "DeviceRGB" and len(color_values) == 3:
            return all(v > 0.99 for v in color_values)
        if color_space == "DeviceCMYK" and len(color_values) == 4:
            return all(v < 0.01 for v in color_values)
        return False

    def _check_text_size(
        self,
        event: TextRenderedEvent,
        text001_agg: dict[int, dict[str, object]],
        text004_agg: dict[int, dict[str, object]],
    ) -> list[Finding]:  # skipcq: PY-R1000
        """Check effective text size for small text issues."""
        findings: list[Finding] = []

        # LPDF_TEXT_003: Invisible text (rendering mode 3 = neither fill nor stroke)
        if event.rendering_mode == 3:
            findings.append(
                Finding(
                    inspection_id="LPDF_TEXT_003",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Invisible text (rendering mode 3) on page {event.page_num} "
                        f"(text is neither filled nor stroked)"
                    ),
                    page_num=event.page_num,
                    details={
                        "font_name": event.font_name,
                        "rendering_mode": event.rendering_mode,
                    },
                    object_type="text",
                    bbox=event.bbox,
                )
            )

        # LPDF_TEXT_004: White text — accumulate into per-page bucket;
        # aggregate emitted once per page in _emit_text004_aggregates.
        if self._is_white_color(event.color_space, event.color_values):
            bucket = text004_agg.setdefault(
                event.page_num,
                {
                    "count": 0,
                    "bboxes": [],
                    "font_names": set(),
                    "color_space": event.color_space,
                    "reverse_thin_count": 0,
                },
            )
            bucket["count"] = int(bucket["count"]) + 1  # type: ignore[arg-type]
            bboxes = bucket["bboxes"]
            if isinstance(bboxes, list) and len(bboxes) < 5 and event.bbox:
                bboxes.append(list(event.bbox))
            fonts = bucket["font_names"]
            if isinstance(fonts, set) and event.font_name:
                fonts.add(event.font_name)

            # T2-RB02 — reverse text rendered with rendering_mode 0
            # (fill only, no stroke) and effective size < 12pt is at
            # risk of breaking up on press; flag it.
            if event.rendering_mode == 0:
                tm_scale_y = math.sqrt(event.text_matrix.b**2 + event.text_matrix.d**2)
                ctm_scale_y = math.sqrt(event.ctm.b**2 + event.ctm.d**2)
                effective_size = event.font_size * tm_scale_y * ctm_scale_y
                if 0 < effective_size < 12.0:
                    bucket["reverse_thin_count"] = (
                        int(bucket.get("reverse_thin_count", 0)) + 1  # type: ignore[arg-type]
                    )

        # LPDF_TEXT_005: Text on registration color (all CMYK at 100%)
        if (
            event.color_space == "DeviceCMYK"
            and len(event.color_values) == 4
            and all(abs(v - 1.0) < 0.01 for v in event.color_values)
        ):
            findings.append(
                Finding(
                    inspection_id="LPDF_TEXT_005",
                    severity=Severity.WARNING,
                    message=(
                        f"Text on registration color (100% all CMYK) on page {event.page_num}"
                    ),
                    page_num=event.page_num,
                    details={
                        "font_name": event.font_name,
                        "color_values": list(event.color_values),
                    },
                    object_type="text",
                    bbox=event.bbox,
                )
            )

        # Calculate effective font size: font_size * text_matrix scale * CTM scale
        tm_scale_y = math.sqrt(event.text_matrix.b**2 + event.text_matrix.d**2)
        ctm_scale_y = math.sqrt(event.ctm.b**2 + event.ctm.d**2)
        effective_size = event.font_size * tm_scale_y * ctm_scale_y

        if effective_size <= 0:
            return findings

        # LPDF_TEXT_006: Small multi-ink text (<8pt, >1 separation)
        if (
            effective_size < 8.0
            and event.color_space == "DeviceCMYK"
            and len(event.color_values) == 4
        ):
            non_zero = sum(1 for v in event.color_values if v > 0.01)
            if non_zero > 1:
                findings.append(
                    Finding(
                        inspection_id="LPDF_TEXT_006",
                        severity=Severity.WARNING,
                        message=(
                            f"Small multi-ink text ({effective_size:.1f}pt, "
                            f"{non_zero} inks) on page {event.page_num} "
                            f"(risk of misregistration)"
                        ),
                        page_num=event.page_num,
                        details={
                            "font_name": event.font_name,
                            "effective_size": effective_size,
                            "color_values": list(event.color_values),
                            "non_zero_inks": non_zero,
                        },
                        object_type="text",
                        bbox=event.bbox,
                    )
                )

        # LPDF_TEXT_002: Very small text (check first — more severe)
        if effective_size < self.very_small_text_threshold:
            findings.append(
                Finding(
                    inspection_id="LPDF_TEXT_002",
                    severity=Severity.WARNING,
                    message=(
                        f"Very small text ({effective_size:.1f}pt effective) "
                        f"on page {event.page_num} "
                        f"(below {self.very_small_text_threshold}pt)"
                    ),
                    page_num=event.page_num,
                    details={
                        "font_name": event.font_name,
                        "font_size": event.font_size,
                        "effective_size": effective_size,
                        "threshold": self.very_small_text_threshold,
                    },
                    object_id=event.font_name,
                    object_type="text",
                    bbox=event.bbox,
                )
            )
        # LPDF_TEXT_001: Small text — accumulate per-page, emit one
        # aggregate per page in _emit_text001_aggregates.
        elif effective_size < self.small_text_threshold:
            bucket = text001_agg.setdefault(
                event.page_num,
                {
                    "count": 0,
                    "bboxes": [],
                    "font_names": set(),
                    "min_effective_size": effective_size,
                    "threshold": self.small_text_threshold,
                },
            )
            bucket["count"] = int(bucket["count"]) + 1  # type: ignore[arg-type]
            bboxes = bucket["bboxes"]
            if isinstance(bboxes, list) and len(bboxes) < 5 and event.bbox:
                bboxes.append(list(event.bbox))
            fonts = bucket["font_names"]
            if isinstance(fonts, set) and event.font_name:
                fonts.add(event.font_name)
            if effective_size < float(bucket["min_effective_size"]):  # type: ignore[arg-type]
                bucket["min_effective_size"] = effective_size

        return findings

    @staticmethod
    def _emit_text001_aggregates(
        agg: dict[int, dict[str, object]],
    ) -> list[Finding]:
        """Emit one LPDF_TEXT_001 finding per page with count + samples."""
        out: list[Finding] = []
        for page_num in sorted(agg):
            bucket = agg[page_num]
            count = int(bucket["count"])  # type: ignore[arg-type]
            if count <= 0:
                continue
            min_size = float(bucket["min_effective_size"])  # type: ignore[arg-type]
            threshold = float(bucket["threshold"])  # type: ignore[arg-type]
            fonts = bucket["font_names"]
            font_list = sorted(fonts) if isinstance(fonts, set) else []
            out.append(
                Finding(
                    inspection_id="LPDF_TEXT_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"{count} small text instance{'s' if count != 1 else ''} "
                        f"(min {min_size:.1f}pt effective) on page {page_num} "
                        f"(below {threshold}pt)"
                    ),
                    page_num=page_num,
                    details={
                        "object_count": count,
                        "min_effective_size": min_size,
                        "threshold": threshold,
                        "font_names": font_list,
                        "representative_bboxes": bucket["bboxes"],
                    },
                    object_type="text",
                )
            )
        return out

    @staticmethod
    def _emit_text004_aggregates(
        agg: dict[int, dict[str, object]],
    ) -> list[Finding]:
        """Emit one LPDF_TEXT_004 finding per page with count + samples,
        plus an LPDF_TEXT_REVERSE_THIN advisory when small fill-only
        white text was seen on the page (T2-RB02)."""
        out: list[Finding] = []
        for page_num in sorted(agg):
            bucket = agg[page_num]
            count = int(bucket["count"])  # type: ignore[arg-type]
            if count <= 0:
                continue
            fonts = bucket["font_names"]
            font_list = sorted(fonts) if isinstance(fonts, set) else []
            out.append(
                Finding(
                    inspection_id="LPDF_TEXT_004",
                    severity=Severity.ADVISORY,
                    message=(
                        f"{count} white text instance{'s' if count != 1 else ''} on page {page_num}"
                    ),
                    page_num=page_num,
                    details={
                        "object_count": count,
                        "color_space": bucket.get("color_space"),
                        "font_names": font_list,
                        "representative_bboxes": bucket["bboxes"],
                    },
                    object_type="text",
                )
            )

            reverse_thin_count = int(bucket.get("reverse_thin_count", 0) or 0)  # type: ignore[arg-type]
            if reverse_thin_count > 0:
                out.append(
                    Finding(
                        inspection_id="LPDF_TEXT_REVERSE_THIN",
                        severity=Severity.ADVISORY,
                        message=(
                            f"{reverse_thin_count} small reverse / knockout text "
                            f"instance{'s' if reverse_thin_count != 1 else ''} on page "
                            f"{page_num} rendered without a stroke; add ≥0.5pt stroke "
                            f"or use ≥12pt for legibility"
                        ),
                        page_num=page_num,
                        details={
                            "object_count": reverse_thin_count,
                            "font_names": font_list,
                        },
                        iso_clause="GWG 2022 reverse-text minimum stroke",
                        object_type="text",
                    )
                )
        return out
