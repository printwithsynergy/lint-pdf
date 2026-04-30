"""WCAG contrast ratio analyzer.

Computes luminance contrast ratios between text foreground colors and
background, checking WCAG 2.1 AA and AAA success criteria.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext

logger = logging.getLogger(__name__)

# WCAG 2.1 minimum contrast ratios
_AA_NORMAL_TEXT = 4.5
_AA_LARGE_TEXT = 3.0
_AAA_NORMAL_TEXT = 7.0
_AAA_LARGE_TEXT = 4.5

# Large text thresholds (in points)
_LARGE_TEXT_SIZE = 18.0  # 18pt regular
_LARGE_TEXT_BOLD_SIZE = 14.0  # 14pt bold


def _srgb_component_to_linear(c: float) -> float:
    """Convert an sRGB component [0..1] to linear luminance component."""
    if c <= 0.04045:
        return c / 12.92
    return float(((c + 0.055) / 1.055) ** 2.4)


def _relative_luminance(r: float, g: float, b: float) -> float:
    """Compute WCAG relative luminance from sRGB values [0..1].

    Formula per WCAG 2.1 §1.4.3:
      L = 0.2126*R_lin + 0.7152*G_lin + 0.0722*B_lin
    """
    r_lin = _srgb_component_to_linear(r)
    g_lin = _srgb_component_to_linear(g)
    b_lin = _srgb_component_to_linear(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def _contrast_ratio(l1: float, l2: float) -> float:
    """Compute WCAG contrast ratio between two relative luminances.

    Returns the ratio (L_lighter + 0.05) / (L_darker + 0.05), always >= 1.0.
    """
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _cmyk_to_srgb(c: float, m: float, y: float, k: float) -> tuple[float, float, float]:
    """Naive CMYK to sRGB."""
    r = (1.0 - c) * (1.0 - k)
    g = (1.0 - m) * (1.0 - k)
    b = (1.0 - y) * (1.0 - k)
    return (max(0.0, min(1.0, r)), max(0.0, min(1.0, g)), max(0.0, min(1.0, b)))


def _values_to_srgb(
    color_space: str, values: tuple[float, ...]
) -> tuple[float, float, float] | None:
    """Convert color values to sRGB, or None if unsupported."""
    if color_space in ("DeviceRGB", "CalRGB") and len(values) == 3:
        return (
            max(0.0, min(1.0, values[0])),
            max(0.0, min(1.0, values[1])),
            max(0.0, min(1.0, values[2])),
        )
    if color_space == "DeviceCMYK" and len(values) == 4:
        return _cmyk_to_srgb(values[0], values[1], values[2], values[3])
    if color_space == "DeviceGray" and len(values) >= 1:
        g = max(0.0, min(1.0, values[0]))
        return (g, g, g)
    return None


def _is_bold_font(font_name: str) -> bool:
    """Heuristic check if a font name indicates bold weight."""
    lower = font_name.lower()
    return "bold" in lower or "black" in lower or "heavy" in lower


@register_ai_analyzer
class WcagContrastAnalyzer(BaseAIAnalyzer):
    """Check WCAG 2.1 contrast ratios for text elements."""

    category = "color_compliance"
    feature_slug = "wcag_contrast_check"
    tier = "cpu"
    credits_per_run = 1

    def analyze_v2(  # skipcq: PY-R1000
        self,
        ctx: AnalyzerContext,
    ) -> list[Finding]:
        # Phase 2 α-stream: signature migration. Pure deterministic
        # analyzer (no GPU). ai_config was declared but never used;
        # document is also unused — events is the only data source.
        events = ctx.events

        from lintpdf.semantic.events import TextRenderedEvent

        findings: list[Finding] = []
        # Track unique text color combos per page to avoid duplicate findings
        checked: set[str] = set()

        # Default background is white (paper)
        bg_luminance = _relative_luminance(1.0, 1.0, 1.0)

        for event in events:
            if not isinstance(event, TextRenderedEvent):
                continue

            fg_srgb = _values_to_srgb(event.color_space, event.color_values)
            if fg_srgb is None:
                continue

            # Deduplicate: one finding per unique (page, color, font_size, font) combo
            dedup_key = (
                f"{event.page_num}:{fg_srgb[0]:.3f},{fg_srgb[1]:.3f},{fg_srgb[2]:.3f}"
                f":{event.font_size:.1f}:{event.font_name}"
            )
            if dedup_key in checked:
                continue
            checked.add(dedup_key)

            fg_luminance = _relative_luminance(*fg_srgb)
            ratio = _contrast_ratio(fg_luminance, bg_luminance)
            ratio_rounded = round(ratio, 2)

            # Determine if this is "large text" per WCAG
            font_size_pt = abs(event.font_size)

            # Skip degenerate sub-2pt sizes. The 2026-04-27 Opus audit
            # flagged AI_WCAG_001 false positives where the engine
            # measured ``1.0pt`` text — invariably a stray glyph from
            # outlined paths or an artefact of a transform that
            # collapsed text height. WCAG legibility math doesn't
            # apply to text that small in any real legibility sense.
            if font_size_pt < 2.0:
                continue

            is_bold = _is_bold_font(event.font_name)
            is_large = font_size_pt >= _LARGE_TEXT_SIZE or (
                is_bold and font_size_pt >= _LARGE_TEXT_BOLD_SIZE
            )

            # Determine required thresholds
            aa_threshold = _AA_LARGE_TEXT if is_large else _AA_NORMAL_TEXT
            aaa_threshold = _AAA_LARGE_TEXT if is_large else _AAA_NORMAL_TEXT

            text_type = "large text" if is_large else "normal text"

            if ratio < aa_threshold:
                # AA failure — WARNING severity
                findings.append(
                    self._make_finding(
                        inspection_id="AI_WCAG_001",
                        severity=Severity.WARNING,
                        message=(
                            f"WCAG AA contrast failure on page {event.page_num}: "
                            f"ratio {ratio_rounded}:1 for {text_type} "
                            f"(font {event.font_name}, {font_size_pt:.1f}pt), "
                            f"required {aa_threshold}:1"
                        ),
                        page_num=event.page_num,
                        details={
                            "contrast_ratio": ratio_rounded,
                            "required_ratio": aa_threshold,
                            "wcag_level": "AA",
                            "text_type": text_type,
                            "font_name": event.font_name,
                            "font_size_pt": font_size_pt,
                            "fg_srgb": list(fg_srgb),
                            "is_bold": is_bold,
                        },
                        object_type="text",
                        bbox=event.bbox,
                    )
                )
            elif ratio < aaa_threshold:
                # AAA failure — ADVISORY severity
                findings.append(
                    self._make_finding(
                        inspection_id="AI_WCAG_002",
                        severity=Severity.ADVISORY,
                        message=(
                            f"WCAG AAA contrast shortfall on page {event.page_num}: "
                            f"ratio {ratio_rounded}:1 for {text_type} "
                            f"(font {event.font_name}, {font_size_pt:.1f}pt), "
                            f"AAA requires {aaa_threshold}:1"
                        ),
                        page_num=event.page_num,
                        details={
                            "contrast_ratio": ratio_rounded,
                            "required_ratio": aaa_threshold,
                            "wcag_level": "AAA",
                            "text_type": text_type,
                            "font_name": event.font_name,
                            "font_size_pt": font_size_pt,
                            "fg_srgb": list(fg_srgb),
                            "is_bold": is_bold,
                        },
                        object_type="text",
                        bbox=event.bbox,
                    )
                )

        return findings
