"""EU Food Information Regulation (FIR) 1169/2011 compliance analyzer.

Validates:
- Minimum x-height for mandatory food information (≥1.2mm standard,
  ≥0.9mm for small packages <80cm²)
- Allergen emphasis (bold/caps) for the 14 Annex II allergens
- Nutritional declaration element ordering
"""

from __future__ import annotations

import contextlib
import logging
import re
from typing import TYPE_CHECKING, Any

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# EU Annex II: 14 allergens requiring emphasis
_ANNEX_II_ALLERGENS: list[str] = [
    "cereals containing gluten",
    "crustaceans",
    "eggs",
    "fish",
    "peanuts",
    "soybeans",
    "milk",
    "nuts",
    "celery",
    "mustard",
    "sesame",
    "sulphur dioxide",
    "lupin",
    "molluscs",
]

# Additional allergen forms for matching
_ALLERGEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "cereals containing gluten",
        re.compile(r"\b(?:wheat|barley|rye|oats|spelt|kamut|gluten)\b", re.IGNORECASE),
    ),
    (
        "crustaceans",
        re.compile(r"\b(?:crustacean|crab|lobster|prawn|shrimp|crayfish)\b", re.IGNORECASE),
    ),
    ("eggs", re.compile(r"\beggs?\b", re.IGNORECASE)),
    ("fish", re.compile(r"\bfish\b", re.IGNORECASE)),
    ("peanuts", re.compile(r"\bpeanuts?\b", re.IGNORECASE)),
    ("soybeans", re.compile(r"\b(?:soy(?:beans?)?|soja)\b", re.IGNORECASE)),
    ("milk", re.compile(r"\b(?:milk|lactose|casein|whey)\b", re.IGNORECASE)),
    (
        "nuts",
        re.compile(
            r"\b(?:almonds?|hazelnuts?|walnuts?|cashews?|pecans?|pistachios?|macadamia|brazil\s*nuts?)\b",
            re.IGNORECASE,
        ),
    ),
    ("celery", re.compile(r"\bcelery\b", re.IGNORECASE)),
    ("mustard", re.compile(r"\bmustard\b", re.IGNORECASE)),
    ("sesame", re.compile(r"\b(?:sesame|sesame\s*seeds?)\b", re.IGNORECASE)),
    (
        "sulphur dioxide",
        re.compile(
            r"\b(?:sulph(?:ur|ite)|sulfit|SO2|E220|E221|E222|E223|E224|E225|E226|E227|E228)\b",
            re.IGNORECASE,
        ),
    ),
    ("lupin", re.compile(r"\blupins?\b", re.IGNORECASE)),
    (
        "molluscs",
        re.compile(
            r"\b(?:mollusc|mussel|oyster|squid|snail|clam|scallop|octopus)\b", re.IGNORECASE
        ),
    ),
]

# EU nutritional declaration mandatory order (Annex XV)
_EU_NUTRITION_ORDER: list[str] = [
    "energy",
    "fat",
    "saturates",
    "carbohydrate",
    "sugars",
    "protein",
    "salt",
]


def _compute_x_height_mm(
    font_size_pt: float,
    sx_height: float | None = None,
    units_per_em: float | None = None,
) -> float:
    """Compute x-height in millimetres.

    Formula: (sxHeight / unitsPerEm) * fontSize_pt * 0.3528 mm/pt

    If sxHeight/unitsPerEm are not available, use the typographic
    convention that x-height ≈ 0.48 of font size.
    """
    if sx_height is not None and units_per_em is not None and units_per_em > 0:
        x_height_ratio = sx_height / units_per_em
    else:
        # Typical Latin x-height ratio
        x_height_ratio = 0.48

    return x_height_ratio * font_size_pt * 0.3528


def _is_bold_font(font_name: str) -> bool:
    """Check if a font name indicates bold weight."""
    lower = font_name.lower()
    return "bold" in lower or "black" in lower or "heavy" in lower


@register_ai_analyzer
class EuFir1169Analyzer(BaseAIAnalyzer):
    """Validate EU FIR 1169/2011 food labelling requirements."""

    category = "regulatory_compliance"
    feature_slug = "eu_fir_1169"
    tier = "cpu"
    credits_per_run = 1

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        from lintpdf.semantic.events import TextRenderedEvent

        findings: list[Finding] = []

        # Determine if small package (surface area < 80cm²)
        surface_area_cm2: float | None = None
        if ai_config is not None:
            raw = getattr(ai_config, "default_package_surface_area_cm2", None)
            if raw is not None:
                with contextlib.suppress(TypeError, ValueError):
                    surface_area_cm2 = float(raw)

        is_small_package = surface_area_cm2 is not None and surface_area_cm2 < 80.0
        min_x_height_mm = 0.9 if is_small_package else 1.2

        # Check x-height across all text events
        x_height_violations: list[dict[str, Any]] = []
        text_events_by_page: dict[int, list[TextRenderedEvent]] = {}

        for event in events:
            if not isinstance(event, TextRenderedEvent):
                continue

            page_num = event.page_num
            if page_num not in text_events_by_page:
                text_events_by_page[page_num] = []
            text_events_by_page[page_num].append(event)

            font_size_pt = abs(event.font_size)
            if font_size_pt <= 0:
                continue

            # Try to get sxHeight and unitsPerEm from font descriptor
            sx_height: float | None = None
            units_per_em: float | None = None

            page = next((p for p in document.pages if p.page_num == page_num), None)
            if page and event.font_name in page.fonts:
                font = page.fonts[event.font_name]
                fd = font.font_descriptor
                if fd:
                    sx_height_raw = fd.get("StemH") or fd.get("XHeight") or fd.get("sxHeight")
                    if sx_height_raw is not None:
                        with contextlib.suppress(TypeError, ValueError):
                            sx_height = float(sx_height_raw)
                    # unitsPerEm is typically in the font descriptor or defaults to 1000
                    units_raw = fd.get("UnitsPerEm")
                    if units_raw is not None:
                        with contextlib.suppress(TypeError, ValueError):
                            units_per_em = float(units_raw)

            x_height_mm = _compute_x_height_mm(font_size_pt, sx_height, units_per_em)

            if x_height_mm < min_x_height_mm:
                x_height_violations.append(
                    {
                        "page_num": page_num,
                        "font_name": event.font_name,
                        "font_size_pt": font_size_pt,
                        "x_height_mm": round(x_height_mm, 3),
                        "min_required_mm": min_x_height_mm,
                        "bbox": event.bbox,
                    }
                )

        # Report x-height violations (deduplicate per page+font+size)
        reported_xh: set[str] = set()
        for violation in x_height_violations:
            key = (
                f"{violation['page_num']}:{violation['font_name']}:{violation['font_size_pt']:.1f}"
            )
            if key in reported_xh:
                continue
            reported_xh.add(key)

            findings.append(
                self._make_finding(
                    inspection_id="AI_EU1169_001",
                    severity=Severity.ERROR,
                    message=(
                        f"Text x-height {violation['x_height_mm']:.2f}mm below "
                        f"EU FIR 1169/2011 minimum ({min_x_height_mm}mm"
                        f"{' for small package' if is_small_package else ''}) "
                        f"on page {violation['page_num']} "
                        f"(font {violation['font_name']}, {violation['font_size_pt']:.1f}pt)"
                    ),
                    page_num=violation["page_num"],
                    details={
                        "x_height_mm": violation["x_height_mm"],
                        "min_required_mm": min_x_height_mm,
                        "font_name": violation["font_name"],
                        "font_size_pt": violation["font_size_pt"],
                        "is_small_package": is_small_package,
                        "surface_area_cm2": surface_area_cm2,
                        "regulation": "EU FIR 1169/2011 Article 13",
                    },
                    object_type="text",
                    bbox=violation.get("bbox"),
                )
            )

        # Check allergen emphasis
        allergen_findings = self._check_allergen_emphasis(document, events, text_events_by_page)
        findings.extend(allergen_findings)

        # Check nutritional declaration ordering
        ordering_findings = self._check_nutrition_order(document)
        findings.extend(ordering_findings)

        return findings

    def _check_allergen_emphasis(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        text_events_by_page: dict[int, list[Any]],
    ) -> list[Finding]:
        """Check that allergens are emphasised (bold, caps, or highlighted).

        EU FIR 1169/2011 Article 21 requires allergens to be emphasised
        within the ingredients list.
        """
        findings: list[Finding] = []

        # Extract full text per page for allergen detection
        for page in document.pages:
            if not page.content_stream:
                continue

            raw = page.content_stream
            if isinstance(raw, bytes):
                try:
                    page_text = raw.decode("latin-1")
                except Exception:
                    continue
            else:
                page_text = str(raw)

            # Check if this page has an ingredients list
            if not re.search(r"\bingredients?\b", page_text, re.IGNORECASE):
                continue

            # Look for allergens in the text
            for allergen_name, pattern in _ALLERGEN_PATTERNS:
                matches = list(pattern.finditer(page_text))
                if not matches:
                    continue

                for match in matches:
                    matched_text = match.group(0)

                    # Check if the allergen text is emphasised
                    # Emphasis indicators: all caps, bold font
                    is_caps = matched_text == matched_text.upper() and len(matched_text) > 1
                    is_bold = False

                    # Check text events for bold fonts near this position
                    page_events = text_events_by_page.get(page.page_num, [])
                    for te in page_events:
                        if _is_bold_font(te.font_name):
                            is_bold = True
                            break

                    if not is_caps and not is_bold:
                        findings.append(
                            self._make_finding(
                                inspection_id="AI_EU1169_002",
                                severity=Severity.WARNING,
                                message=(
                                    f"Allergen '{allergen_name}' (matched: '{matched_text}') "
                                    f"may not be emphasised on page {page.page_num} "
                                    f"(EU FIR 1169/2011 Article 21 requires bold, "
                                    f"caps, or other emphasis)"
                                ),
                                page_num=page.page_num,
                                details={
                                    "allergen": allergen_name,
                                    "matched_text": matched_text,
                                    "is_caps": is_caps,
                                    "is_bold": is_bold,
                                    "regulation": "EU FIR 1169/2011 Article 21",
                                },
                                object_type="text",
                            )
                        )
                        break  # One finding per allergen per page

        return findings

    def _check_nutrition_order(
        self, document: SemanticDocument
    ) -> list[Finding]:  # skipcq: PY-R1000
        """Check EU nutritional declaration ordering per Annex XV."""
        findings: list[Finding] = []

        for page in document.pages:
            if not page.content_stream:
                continue

            raw = page.content_stream
            if isinstance(raw, bytes):
                try:
                    page_text = raw.decode("latin-1")
                except Exception:
                    continue
            else:
                page_text = str(raw)

            # Check if this page has nutritional information
            if not re.search(r"\b(?:energy|kj|kcal)\b", page_text, re.IGNORECASE):
                continue

            # Find positions of EU nutrition elements
            found: list[tuple[str, int]] = []
            for nutrient in _EU_NUTRITION_ORDER:
                match = re.search(r"\b" + re.escape(nutrient) + r"\b", page_text, re.IGNORECASE)
                if match:
                    found.append((nutrient, match.start()))

            # Check ordering
            if len(found) >= 2:
                for i in range(len(found) - 1):
                    curr_name, curr_pos = found[i]
                    next_name, next_pos = found[i + 1]
                    if curr_pos > next_pos:
                        findings.append(
                            self._make_finding(
                                inspection_id="AI_EU1169_003",
                                severity=Severity.WARNING,
                                message=(
                                    f"Nutritional declaration order: '{curr_name}' "
                                    f"appears after '{next_name}' on page {page.page_num} "
                                    f"(EU FIR 1169/2011 Annex XV mandates specific order)"
                                ),
                                page_num=page.page_num,
                                details={
                                    "out_of_order": [curr_name, next_name],
                                    "regulation": "EU FIR 1169/2011 Annex XV",
                                },
                                object_type="text",
                            )
                        )
                        break

        return findings
