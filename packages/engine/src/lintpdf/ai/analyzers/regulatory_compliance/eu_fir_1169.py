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

from lintpdf.ai.analyzers.regulatory_compliance._gates import is_eu_food_applicable
from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.analyzers.text_metrics import (
    effective_font_size_pt,
    effective_x_height_mm,
)

if TYPE_CHECKING:
    from lintpdf.ai.types import AIConfig
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


# WS-5 declaration-context anchors. An allergen-name match only
# counts toward the emphasis check (AI_EU1169_002) when one of
# these phrases appears within ``_DECL_WINDOW_CHARS`` of the match.
# "Gluten Free" is excluded via the claim patterns below.
_DECL_WINDOW_CHARS = 120
_CLAIM_WINDOW_CHARS = 40
_DECLARATION_ANCHORS = (
    re.compile(r"\bingredients?\s*:", re.IGNORECASE),
    re.compile(r"\bcontains\s*:", re.IGNORECASE),
    re.compile(r"\ballergens?\s*:", re.IGNORECASE),
    re.compile(r"\bmay\s+contain\b", re.IGNORECASE),
    re.compile(r"\bwarning\s*:\s*contains\b", re.IGNORECASE),
    re.compile(r"\ballergen\s+warning\b", re.IGNORECASE),
    re.compile(r"\btraces\s+of\b", re.IGNORECASE),
)
# Claim patterns rejected as declaration context. "Gluten Free",
# "Dairy-Free", "Nut Free" etc. on the front panel are marketing
# claims, not allergen declarations.
_CLAIM_PATTERNS = (
    re.compile(r"\b(?:gluten|dairy|nut|lactose|soy|egg|wheat|peanut)[-\s]*free\b", re.IGNORECASE),
    re.compile(
        r"\bfree\s+from\s+(?:gluten|dairy|nuts?|lactose|soy|eggs?|wheat|peanuts?)\b", re.IGNORECASE
    ),
    re.compile(
        r"\bno\s+(?:added\s+)?(?:gluten|dairy|nuts?|lactose|soy|eggs?|wheat|peanuts?)\b",
        re.IGNORECASE,
    ),
)


def _in_declaration_context(text: str, start: int, end: int) -> bool:
    """True when a regex match at [start, end) in ``text`` sits
    inside an allergen-declaration context.

    Semantics:
    * At least one declaration anchor must appear within
      ``_DECL_WINDOW_CHARS`` before or after the match.
    * No claim pattern may appear within ``_CLAIM_WINDOW_CHARS``
      of the match (claim wins over declaration — "Gluten Free
      ingredients: ..." on a front panel is still a claim).
    """
    claim_left = max(0, start - _CLAIM_WINDOW_CHARS)
    claim_right = min(len(text), end + _CLAIM_WINDOW_CHARS)
    claim_window = text[claim_left:claim_right]
    for claim in _CLAIM_PATTERNS:
        if claim.search(claim_window):
            return False

    decl_left = max(0, start - _DECL_WINDOW_CHARS)
    decl_right = min(len(text), end + _DECL_WINDOW_CHARS)
    decl_window = text[decl_left:decl_right]
    return any(anchor.search(decl_window) for anchor in _DECLARATION_ANCHORS)


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
        ai_config: AIConfig = None,
    ) -> list[Finding]:
        from lintpdf.semantic.events import TextRenderedEvent

        findings: list[Finding] = []

        # Jurisdiction gate. FIR 1169 is a pure-EU food-info regulation;
        # it does not apply to US/CA/UK products. The 2026-04-27 Opus
        # audit flagged 28 false positives on Canadian + US supplement
        # labels where this rule fired despite ``regulatory_market``
        # being non-EU (or unset and the product clearly non-food-EU).
        if not is_eu_food_applicable(ai_config):
            return []

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

            page = next((p for p in document.pages if p.page_num == page_num), None)
            font = page.fonts.get(event.font_name) if page else None
            x_height_mm = effective_x_height_mm(event, font=font)
            if x_height_mm is None:
                # Invisible text (rendering_mode == 3) -- skip; no
                # ink is drawn, so legibility rules don't apply.
                continue
            # Composed on-page font size, used for the dedup key +
            # user-facing message so "1pt logo" findings go away.
            font_size_pt = effective_font_size_pt(event)
            if font_size_pt <= 0:
                continue

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

                    # WS-5: only allergen matches inside a real
                    # declaration-context window count. Claim
                    # phrases ("Gluten Free") on the front panel
                    # must not trip the emphasis rule, and stray
                    # marketing copy with an allergen name in it
                    # shouldn't either.
                    if not _in_declaration_context(page_text, match.start(), match.end()):
                        continue

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
