"""HairlineAnalyzer — thin stroke, zero-width, and small text detection.

Processes PathPaintingEvent and TextRenderedEvent events to detect
hairlines and small text that may not reproduce in print.

Check IDs:
    GRD_STROKE_001 — Hairline stroke (<0.25pt effective)
    GRD_STROKE_002 — Zero-width stroke
    GRD_STROKE_003 — Butt cap on thin stroke (<0.5pt)
    GRD_STROKE_004 — Multi-ink thin stroke (<0.5pt, >1 CMYK separation)
    GRD_STROKE_005 — Invisible line art (zero opacity stroke)
    GRD_STROKE_006 — Flatness tolerance override
    GRD_PATH_001 — Excessive path points (>10,000)
    GRD_PATH_002 — White fill detected on paths
    GRD_TEXT_001 — Small text (<6pt effective)
    GRD_TEXT_002 — Very small text (<4pt effective)
    GRD_TEXT_003 — Invisible text (rendering mode 3)
    GRD_TEXT_004 — White text detected
    GRD_TEXT_005 — Text on registration color
    GRD_TEXT_006 — Small multi-ink text (<8pt, >1 separation)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent, PathPaintingEvent, TextRenderedEvent
    from grounded.semantic.model import SemanticDocument

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
        from grounded.semantic.events import PathPaintingEvent, TextRenderedEvent

        findings: list[Finding] = []

        white_fill_pages: set[int] = set()

        for event in events:
            if isinstance(event, PathPaintingEvent):
                if event.stroke:
                    findings.extend(self._check_stroke(event))

                # GRD_PATH_002: White fill detected on paths
                if event.page_num not in white_fill_pages:
                    result = self._check_white_fill(event)
                    if result:
                        findings.append(result)
                        white_fill_pages.add(event.page_num)

                # GRD_PATH_001: Excessive path points
                if event.point_count > 10000:
                    findings.append(
                        Finding(
                            inspection_id="GRD_PATH_001",
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
                        )
                    )
            elif isinstance(event, TextRenderedEvent):
                findings.extend(self._check_text_size(event))

        return findings

    def _check_stroke(self, event: PathPaintingEvent) -> list[Finding]:  # skipcq: PY-R1000
        """Check stroke width for hairline issues."""
        findings: list[Finding] = []
        line_width = event.line_width

        # GRD_STROKE_002: Zero-width stroke
        if line_width <= 0.0:
            findings.append(
                Finding(
                    inspection_id="GRD_STROKE_002",
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
                )
            )
            return findings

        # GRD_STROKE_001: Hairline stroke
        if line_width < self.hairline_threshold:
            findings.append(
                Finding(
                    inspection_id="GRD_STROKE_001",
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
                )
            )

        # GRD_STROKE_003: Butt cap on thin stroke
        if line_width < THIN_STROKE_THRESHOLD and event.line_cap == 0:
            findings.append(
                Finding(
                    inspection_id="GRD_STROKE_003",
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
                )
            )

        # GRD_STROKE_004: Multi-ink thin stroke (<0.5pt, >1 CMYK separation)
        if (
            line_width < THIN_STROKE_THRESHOLD
            and event.stroke_color_space == "DeviceCMYK"
            and len(event.stroke_color_values) == 4
        ):
            non_zero = sum(1 for v in event.stroke_color_values if v > 0.01)
            if non_zero > 1:
                findings.append(
                    Finding(
                        inspection_id="GRD_STROKE_004",
                        severity=Severity.WARNING,
                        message=(
                            f"Multi-ink thin stroke ({line_width:.3f}pt, "
                            f"{non_zero} inks) on page {event.page_num} "
                            f"(risk of misregistration on thin lines)"
                        ),
                        page_num=event.page_num,
                        details={
                            "line_width": line_width,
                            "stroke_color_values": list(event.stroke_color_values),
                            "non_zero_inks": non_zero,
                        },
                        object_type="path",
                    )
                )

        # GRD_STROKE_005: Invisible line art (zero opacity stroke)
        stroke_alpha = getattr(event, "stroke_alpha", None)
        if stroke_alpha is not None and abs(stroke_alpha) < 1e-6:
            findings.append(
                Finding(
                    inspection_id="GRD_STROKE_005",
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
                        inspection_id="GRD_STROKE_005",
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
                    )
                )

        # GRD_STROKE_006: Flatness tolerance override
        flatness = getattr(event, "flatness", None)
        if flatness is not None and flatness != 0 and flatness != 1.0:
            findings.append(
                Finding(
                    inspection_id="GRD_STROKE_006",
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
                )
            )

        return findings

    def _check_white_fill(self, event: PathPaintingEvent) -> Finding | None:
        """Check if a path has a white fill (GRD_PATH_002)."""
        if not getattr(event, "fill", False):
            return None
        fill_cs = getattr(event, "fill_color_space", None)
        fill_cv = getattr(event, "fill_color_values", None)
        if fill_cs is None or fill_cv is None:
            return None
        if self._is_white_color(fill_cs, tuple(fill_cv)):
            return Finding(
                inspection_id="GRD_PATH_002",
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

    def _check_text_size(self, event: TextRenderedEvent) -> list[Finding]:  # skipcq: PY-R1000
        """Check effective text size for small text issues."""
        findings: list[Finding] = []

        # GRD_TEXT_003: Invisible text (rendering mode 3 = neither fill nor stroke)
        if event.rendering_mode == 3:
            findings.append(
                Finding(
                    inspection_id="GRD_TEXT_003",
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
                )
            )

        # GRD_TEXT_004: White text
        if self._is_white_color(event.color_space, event.color_values):
            findings.append(
                Finding(
                    inspection_id="GRD_TEXT_004",
                    severity=Severity.ADVISORY,
                    message=f"White text detected on page {event.page_num}",
                    page_num=event.page_num,
                    details={
                        "font_name": event.font_name,
                        "color_space": event.color_space,
                        "color_values": list(event.color_values),
                    },
                    object_type="text",
                )
            )

        # GRD_TEXT_005: Text on registration color (all CMYK at 100%)
        if (
            event.color_space == "DeviceCMYK"
            and len(event.color_values) == 4
            and all(abs(v - 1.0) < 0.01 for v in event.color_values)
        ):
            findings.append(
                Finding(
                    inspection_id="GRD_TEXT_005",
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
                )
            )

        # Calculate effective font size: font_size * text_matrix scale * CTM scale
        tm_scale_y = math.sqrt(event.text_matrix.b**2 + event.text_matrix.d**2)
        ctm_scale_y = math.sqrt(event.ctm.b**2 + event.ctm.d**2)
        effective_size = event.font_size * tm_scale_y * ctm_scale_y

        if effective_size <= 0:
            return findings

        # GRD_TEXT_006: Small multi-ink text (<8pt, >1 separation)
        if (
            effective_size < 8.0
            and event.color_space == "DeviceCMYK"
            and len(event.color_values) == 4
        ):
            non_zero = sum(1 for v in event.color_values if v > 0.01)
            if non_zero > 1:
                findings.append(
                    Finding(
                        inspection_id="GRD_TEXT_006",
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
                    )
                )

        # GRD_TEXT_002: Very small text (check first — more severe)
        if effective_size < self.very_small_text_threshold:
            findings.append(
                Finding(
                    inspection_id="GRD_TEXT_002",
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
                )
            )
        # GRD_TEXT_001: Small text
        elif effective_size < self.small_text_threshold:
            findings.append(
                Finding(
                    inspection_id="GRD_TEXT_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Small text ({effective_size:.1f}pt effective) "
                        f"on page {event.page_num} "
                        f"(below {self.small_text_threshold}pt)"
                    ),
                    page_num=event.page_num,
                    details={
                        "font_name": event.font_name,
                        "font_size": event.font_size,
                        "effective_size": effective_size,
                        "threshold": self.small_text_threshold,
                    },
                    object_id=event.font_name,
                    object_type="text",
                )
            )

        return findings
