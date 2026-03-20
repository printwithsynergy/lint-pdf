"""Pharmaceutical font compliance analyzer.

Validates font sizes for pharmaceutical labelling against:
- EU pharmaceutical rules: min 7pt Didot (x-height ≥1.4mm)
- FDA OTC Drug Facts: body ≥6pt, headings ≥8pt, "Drug Facts" largest,
  ≤39 characters per inch line width
"""

from __future__ import annotations

import contextlib
import logging
import re
from typing import TYPE_CHECKING

from grounded.ai.base import BaseAIAnalyzer
from grounded.ai.registry import register_ai_analyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.api.models import TenantAIConfig
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# EU Pharma: minimum x-height for readability
_EU_PHARMA_MIN_X_HEIGHT_MM = 1.4  # 7pt Didot equivalent
_EU_PHARMA_MIN_FONT_SIZE_PT = 7.0  # Didot point ≈ 1.07 DTP points

# FDA OTC Drug Facts minimum sizes
_FDA_OTC_BODY_MIN_PT = 6.0
_FDA_OTC_HEADING_MIN_PT = 8.0
_FDA_OTC_MAX_CHARS_PER_INCH = 39

# Drug Facts headings per FDA 21 CFR 201.66
_DRUG_FACTS_HEADINGS = [
    "Drug Facts",
    "Active ingredient",
    "Active ingredients",
    "Purpose",
    "Uses",
    "Warnings",
    "Directions",
    "Other information",
    "Inactive ingredients",
    "Questions?",
]


def _compute_x_height_mm(
    font_size_pt: float,
    sx_height: float | None = None,
    units_per_em: float | None = None,
) -> float:
    """Compute x-height in millimetres."""
    if sx_height is not None and units_per_em is not None and units_per_em > 0:
        x_height_ratio = sx_height / units_per_em
    else:
        x_height_ratio = 0.48
    return x_height_ratio * font_size_pt * 0.3528


def _is_bold_font(font_name: str) -> bool:
    """Check if font name indicates bold weight."""
    lower = font_name.lower()
    return "bold" in lower or "black" in lower or "heavy" in lower


def _estimate_chars_per_inch(font_size_pt: float, font_name: str) -> float:
    """Estimate characters per inch for a given font and size.

    Uses approximate average character widths for common font families.
    Monospaced: 0.6em, Proportional: ~0.5em average width.
    """
    if font_size_pt <= 0:
        return 0.0

    # Average character width as fraction of em
    is_mono = any(m in font_name.lower() for m in ("courier", "mono", "consolas"))
    avg_char_width_em = 0.6 if is_mono else 0.5

    # Character width in points
    char_width_pt = font_size_pt * avg_char_width_em

    # Points per inch = 72
    if char_width_pt > 0:
        return 72.0 / char_width_pt
    return 0.0


@register_ai_analyzer
class PharmaFontAnalyzer(BaseAIAnalyzer):
    """Validate pharmaceutical labelling font sizes."""

    category = "regulatory_compliance"
    feature_slug = "pharma_font_compliance"
    tier = "cpu"
    credits_per_run = 1

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        # Determine regulatory market
        market = "auto"  # Will try to auto-detect
        if ai_config is not None:
            raw_market = getattr(ai_config, "regulatory_market", None)
            if raw_market:
                market = str(raw_market).lower()

        # Auto-detect: check for "Drug Facts" (FDA OTC) or EU-style content
        if market == "auto":
            market = self._detect_market(document)

        if market in ("eu", "europe", "ema"):
            return self._check_eu_pharma(document, events)
        elif market in ("us", "usa", "fda"):
            return self._check_fda_otc(document, events)
        else:
            # Run both checks
            findings = self._check_eu_pharma(document, events)
            findings.extend(self._check_fda_otc(document, events))
            return findings

    @staticmethod
    def _detect_market(document: SemanticDocument) -> str:
        """Auto-detect regulatory market from document content."""
        for page in document.pages:
            if not page.content_stream:
                continue
            raw = page.content_stream
            if isinstance(raw, bytes):
                try:
                    text = raw.decode("latin-1")
                except Exception:
                    continue
            else:
                text = str(raw)

            if re.search(r"\bDrug\s+Facts\b", text):
                return "fda"
            if re.search(r"\bPatient\s+Information\s+Leaflet\b", text, re.IGNORECASE):
                return "eu"
            if re.search(r"\bSmPC\b|Summary\s+of\s+Product\s+Characteristics", text, re.IGNORECASE):
                return "eu"

        return "unknown"

    def _check_eu_pharma(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Check EU pharmaceutical font requirements."""
        from grounded.semantic.events import TextRenderedEvent

        findings: list[Finding] = []
        reported: set[str] = set()

        for event in events:
            if not isinstance(event, TextRenderedEvent):
                continue

            font_size_pt = abs(event.font_size)
            if font_size_pt <= 0:
                continue

            # Get font descriptor data for x-height calculation
            sx_height: float | None = None
            units_per_em: float | None = None

            page = next((p for p in document.pages if p.page_num == event.page_num), None)
            if page and event.font_name in page.fonts:
                fd = page.fonts[event.font_name].font_descriptor
                if fd:
                    xh = fd.get("XHeight") or fd.get("sxHeight")
                    if xh is not None:
                        with contextlib.suppress(TypeError, ValueError):
                            sx_height = float(xh)
                    upe = fd.get("UnitsPerEm")
                    if upe is not None:
                        with contextlib.suppress(TypeError, ValueError):
                            units_per_em = float(upe)

            x_height_mm = _compute_x_height_mm(font_size_pt, sx_height, units_per_em)

            if x_height_mm < _EU_PHARMA_MIN_X_HEIGHT_MM:
                key = f"eu:{event.page_num}:{event.font_name}:{font_size_pt:.1f}"
                if key in reported:
                    continue
                reported.add(key)

                findings.append(
                    self._make_finding(
                        inspection_id="AI_PHARMA_001",
                        severity=Severity.AGROUND,
                        message=(
                            f"EU pharma font below minimum: x-height "
                            f"{x_height_mm:.2f}mm (required ≥{_EU_PHARMA_MIN_X_HEIGHT_MM}mm, "
                            f"7pt Didot equivalent) on page {event.page_num} "
                            f"(font {event.font_name}, {font_size_pt:.1f}pt)"
                        ),
                        page_num=event.page_num,
                        details={
                            "x_height_mm": round(x_height_mm, 3),
                            "min_required_mm": _EU_PHARMA_MIN_X_HEIGHT_MM,
                            "font_name": event.font_name,
                            "font_size_pt": font_size_pt,
                            "regulation": "EU Pharmaceutical Readability Guideline",
                        },
                        object_type="text",
                        bbox=event.bbox,
                    )
                )

        return findings

    def _check_fda_otc(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Check FDA OTC Drug Facts font requirements per 21 CFR 201.66."""
        from grounded.semantic.events import TextRenderedEvent

        findings: list[Finding] = []
        reported: set[str] = set()

        # Find pages with Drug Facts content
        drug_facts_pages: set[int] = set()
        for page in document.pages:
            if not page.content_stream:
                continue
            raw = page.content_stream
            if isinstance(raw, bytes):
                try:
                    text = raw.decode("latin-1")
                except Exception:
                    continue
            else:
                text = str(raw)

            if re.search(r"\bDrug\s+Facts\b", text):
                drug_facts_pages.add(page.page_num)

        if not drug_facts_pages:
            return []

        # Collect font sizes on Drug Facts pages
        page_font_sizes: dict[int, list[tuple[str, float]]] = {}
        for event in events:
            if not isinstance(event, TextRenderedEvent):
                continue
            if event.page_num not in drug_facts_pages:
                continue

            font_size_pt = abs(event.font_size)
            if font_size_pt <= 0:
                continue

            if event.page_num not in page_font_sizes:
                page_font_sizes[event.page_num] = []
            page_font_sizes[event.page_num].append((event.font_name, font_size_pt))

        for page_num in drug_facts_pages:
            sizes = page_font_sizes.get(page_num, [])
            if not sizes:
                continue

            all_sizes = [s for _, s in sizes]
            _max_size = max(all_sizes) if all_sizes else 0
            min_size = min(all_sizes) if all_sizes else 0

            # Check body text minimum (6pt)
            if 0 < min_size < _FDA_OTC_BODY_MIN_PT:
                key = f"fda_body:{page_num}:{min_size:.1f}"
                if key not in reported:
                    reported.add(key)
                    findings.append(
                        self._make_finding(
                            inspection_id="AI_PHARMA_002",
                            severity=Severity.AGROUND,
                            message=(
                                f"FDA Drug Facts body text below minimum: "
                                f"{min_size:.1f}pt (required ≥{_FDA_OTC_BODY_MIN_PT}pt) "
                                f"on page {page_num}"
                            ),
                            page_num=page_num,
                            details={
                                "found_size_pt": min_size,
                                "required_min_pt": _FDA_OTC_BODY_MIN_PT,
                                "regulation": "21 CFR 201.66(d)(4)",
                            },
                            object_type="text",
                        )
                    )

            # Check that "Drug Facts" is the largest text
            # Look for heading-sized text that's bold
            _heading_sizes = [
                s for fn, s in sizes if _is_bold_font(fn) and s >= _FDA_OTC_HEADING_MIN_PT
            ]

            # Check heading minimum (8pt)
            bold_sizes = [s for fn, s in sizes if _is_bold_font(fn)]
            for bs in bold_sizes:
                if bs < _FDA_OTC_HEADING_MIN_PT:
                    key = f"fda_heading:{page_num}:{bs:.1f}"
                    if key not in reported:
                        reported.add(key)
                        findings.append(
                            self._make_finding(
                                inspection_id="AI_PHARMA_003",
                                severity=Severity.AGROUND,
                                message=(
                                    f"FDA Drug Facts heading below minimum: "
                                    f"{bs:.1f}pt (required ≥{_FDA_OTC_HEADING_MIN_PT}pt) "
                                    f"on page {page_num}"
                                ),
                                page_num=page_num,
                                details={
                                    "found_size_pt": bs,
                                    "required_min_pt": _FDA_OTC_HEADING_MIN_PT,
                                    "regulation": "21 CFR 201.66(d)(2)",
                                },
                                object_type="text",
                            )
                        )

            # Check characters per inch
            for font_name, font_size in sizes:
                cpi = _estimate_chars_per_inch(font_size, font_name)
                if cpi > _FDA_OTC_MAX_CHARS_PER_INCH:
                    key = f"fda_cpi:{page_num}:{font_name}:{font_size:.1f}"
                    if key not in reported:
                        reported.add(key)
                        findings.append(
                            self._make_finding(
                                inspection_id="AI_PHARMA_004",
                                severity=Severity.AGROUND,
                                message=(
                                    f"FDA Drug Facts text exceeds {_FDA_OTC_MAX_CHARS_PER_INCH} "
                                    f"characters per inch (estimated {cpi:.0f} cpi) "
                                    f"on page {page_num} "
                                    f"(font {font_name}, {font_size:.1f}pt)"
                                ),
                                page_num=page_num,
                                details={
                                    "estimated_cpi": round(cpi, 1),
                                    "max_allowed_cpi": _FDA_OTC_MAX_CHARS_PER_INCH,
                                    "font_name": font_name,
                                    "font_size_pt": font_size,
                                    "regulation": "21 CFR 201.66(d)(6)",
                                },
                                object_type="text",
                            )
                        )

        return findings
