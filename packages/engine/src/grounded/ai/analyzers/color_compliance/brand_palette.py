"""Brand palette compliance analyzer.

Extracts fill/stroke colors from PDF content stream events and compares
them against the tenant's brand palette using CIEDE2000 Delta-E distance.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from grounded.ai.base import BaseAIAnalyzer
from grounded.ai.registry import register_ai_analyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.api.models import TenantAIConfig
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Optional dependency for CIEDE2000
try:
    import colour as colour_science

    _HAS_COLOUR = True
except ImportError:
    colour_science = None
    _HAS_COLOUR = False

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:
    np = None
    _HAS_NUMPY = False


def _srgb_to_lab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert sRGB [0..1] to CIELAB using colour-science library."""
    rgb = np.array([r, g, b])
    xyz = colour_science.sRGB_to_XYZ(rgb)
    lab = colour_science.XYZ_to_Lab(xyz)
    return (float(lab[0]), float(lab[1]), float(lab[2]))


def _delta_e_2000(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    """Compute CIEDE2000 Delta-E between two CIELAB colors."""
    a1 = np.array(lab1)
    a2 = np.array(lab2)
    return float(colour_science.delta_E(a1, a2, method="CIE 2000"))


def _cmyk_to_srgb(c: float, m: float, y: float, k: float) -> tuple[float, float, float]:
    """Naive CMYK to sRGB conversion (no ICC profile)."""
    r = (1.0 - c) * (1.0 - k)
    g = (1.0 - m) * (1.0 - k)
    b = (1.0 - y) * (1.0 - k)
    return (r, g, b)


def _gray_to_srgb(g: float) -> tuple[float, float, float]:
    """Convert DeviceGray to sRGB."""
    return (g, g, g)


def _parse_color_value(value: str) -> tuple[float, float, float] | None:  # skipcq: PY-R1000
    """Parse a palette color value string to sRGB tuple.

    Supports:
    - Hex: #RRGGBB or #RGB
    - RGB tuple: rgb(R, G, B) where R,G,B are 0-255
    - CMYK tuple: cmyk(C, M, Y, K) where values are 0-1 or 0-100
    """
    value = value.strip()

    # Hex color
    if value.startswith("#"):
        hex_str = value[1:]
        if len(hex_str) == 3:
            hex_str = "".join(c * 2 for c in hex_str)
        if len(hex_str) == 6:
            r = int(hex_str[0:2], 16) / 255.0
            g = int(hex_str[2:4], 16) / 255.0
            b = int(hex_str[4:6], 16) / 255.0
            return (r, g, b)

    # Parse RGB functional notation
    if value.lower().startswith("rgb(") and value.endswith(")"):
        parts = value[4:-1].split(",")
        if len(parts) == 3:
            r, g, b = (float(p.strip()) for p in parts)
            if r > 1 or g > 1 or b > 1:
                r, g, b = r / 255.0, g / 255.0, b / 255.0
            return (r, g, b)

    # Parse CMYK functional notation
    if value.lower().startswith("cmyk(") and value.endswith(")"):
        parts = value[5:-1].split(",")
        if len(parts) == 4:
            c, m, y, k = (float(p.strip()) for p in parts)
            if c > 1 or m > 1 or y > 1 or k > 1:
                c, m, y, k = c / 100.0, m / 100.0, y / 100.0, k / 100.0
            return _cmyk_to_srgb(c, m, y, k)

    return None


def _extract_document_colors(  # skipcq: PY-R1000
    events: list[ContentStreamEvent],
) -> list[dict[str, Any]]:
    """Extract unique fill/stroke colors from content stream events."""
    from grounded.semantic.events import ColorChangedEvent, PathPaintingEvent, TextRenderedEvent

    unique_colors: dict[str, dict[str, Any]] = {}

    for event in events:
        color_entries: list[tuple[str, str, tuple[float, ...]]] = []

        if isinstance(event, ColorChangedEvent):
            role = "stroke" if event.stroking else "fill"
            color_entries.append((role, event.color_space, event.color_values))
        elif isinstance(event, PathPaintingEvent):
            if event.fill and event.fill_color_values:
                color_entries.append(("fill", event.fill_color_space, event.fill_color_values))
            if event.stroke and event.stroke_color_values:
                color_entries.append(
                    ("stroke", event.stroke_color_space, event.stroke_color_values)
                )
        elif isinstance(event, TextRenderedEvent):
            color_entries.append(("text", event.color_space, event.color_values))

        for role, cs, values in color_entries:
            # Convert to sRGB for comparison
            srgb: tuple[float, float, float] | None = None

            if cs in ("DeviceRGB", "CalRGB") and len(values) == 3:
                srgb = (values[0], values[1], values[2])
            elif cs == "DeviceCMYK" and len(values) == 4:
                srgb = _cmyk_to_srgb(values[0], values[1], values[2], values[3])
            elif cs == "DeviceGray" and len(values) >= 1:
                srgb = _gray_to_srgb(values[0])
            else:
                # Skip color spaces we cannot convert without ICC profiles
                continue

            key = f"{cs}:{','.join(f'{v:.4f}' for v in values)}"
            if key not in unique_colors:
                unique_colors[key] = {
                    "color_space": cs,
                    "values": values,
                    "srgb": srgb,
                    "role": role,
                    "page_num": event.page_num,
                }

    return list(unique_colors.values())


@register_ai_analyzer
class BrandPaletteAnalyzer(BaseAIAnalyzer):
    """Check that document colors conform to the tenant's brand palette."""

    category = "color_compliance"
    feature_slug = "brand_palette_check"
    tier = "cpu"
    credits_per_run = 1

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        if not _HAS_COLOUR or not _HAS_NUMPY:
            logger.debug("colour-science or numpy not installed — skipping brand palette check")
            return []

        # Get brand palette from config
        if ai_config is None or not ai_config.brand_palette:
            return [
                self._make_finding(
                    inspection_id="AI_BRAND_001",
                    severity=Severity.ADVISORY,
                    message="No brand palette configured — skipping palette compliance check.",
                    details={"reason": "no_palette"},
                )
            ]

        # Parse palette colors to Lab
        palette_lab: list[tuple[str, tuple[float, float, float]]] = []
        for entry in ai_config.brand_palette:
            value = entry.get("value", "")
            srgb = _parse_color_value(value)
            if srgb is not None:
                lab = _srgb_to_lab(*srgb)
                palette_lab.append((value, lab))

        if not palette_lab:
            return [
                self._make_finding(
                    inspection_id="AI_BRAND_002",
                    severity=Severity.ADVISORY,
                    message="Brand palette configured but no parseable color values found.",
                    details={"reason": "unparseable_palette"},
                )
            ]

        # Thresholds
        squall_threshold = float(getattr(ai_config, "delta_e_squall_threshold", 2.0) or 2.0)
        aground_threshold = float(getattr(ai_config, "delta_e_aground_threshold", 5.0) or 5.0)

        # Extract document colors
        doc_colors = _extract_document_colors(events)
        if not doc_colors:
            return []

        findings: list[Finding] = []
        for color_info in doc_colors:
            srgb = color_info["srgb"]

            # Skip near-black and near-white (common registration/background colors)
            if all(c < 0.05 for c in srgb) or all(c > 0.95 for c in srgb):
                continue

            doc_lab = _srgb_to_lab(*srgb)

            # Find closest palette color
            min_delta_e = float("inf")
            closest_palette = ""
            for palette_value, palette_lab_val in palette_lab:
                de = _delta_e_2000(doc_lab, palette_lab_val)
                if de < min_delta_e:
                    min_delta_e = de
                    closest_palette = palette_value

            min_delta_e = round(min_delta_e, 2)

            if min_delta_e > aground_threshold:
                severity = Severity.AGROUND
                message = (
                    f"Color {color_info['color_space']} {color_info['values']} "
                    f"is out of brand palette (ΔE={min_delta_e:.2f}, "
                    f"nearest palette: {closest_palette}, threshold: {aground_threshold})"
                )
            elif min_delta_e > squall_threshold:
                severity = Severity.SQUALL
                message = (
                    f"Color {color_info['color_space']} {color_info['values']} "
                    f"deviates from brand palette (ΔE={min_delta_e:.2f}, "
                    f"nearest palette: {closest_palette}, threshold: {squall_threshold})"
                )
            else:
                continue

            findings.append(
                self._make_finding(
                    inspection_id="AI_BRAND_003",
                    severity=severity,
                    message=message,
                    page_num=color_info.get("page_num", 0),
                    details={
                        "color_space": color_info["color_space"],
                        "color_values": list(color_info["values"]),
                        "srgb": list(srgb),
                        "delta_e": min_delta_e,
                        "closest_palette": closest_palette,
                        "role": color_info["role"],
                    },
                )
            )

        return findings
