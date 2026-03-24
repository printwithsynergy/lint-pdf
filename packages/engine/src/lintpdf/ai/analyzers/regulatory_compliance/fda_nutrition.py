"""FDA Nutrition Facts label compliance analyzer.

Validates Nutrition Facts panels per 21 CFR 101.9 (2016 final rule),
checking font sizes, bold requirements, element ordering, and required
label elements.
"""

from __future__ import annotations

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

# 2016 FDA rule mandated minimum font sizes (points)
_FDA_FONT_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "Nutrition Facts": {"min_pt": 13.0, "bold": True, "description": "heading"},
    "Calories": {"min_pt": 22.0, "bold": True, "description": "calorie declaration"},
    "Serving size": {"min_pt": 10.0, "bold": True, "description": "serving size"},
    "Servings per container": {
        "min_pt": 8.0,
        "bold": False,
        "description": "servings per container",
    },
    "Amount per serving": {"min_pt": 8.0, "bold": False, "description": "amount per serving"},
    "% Daily Value": {"min_pt": 8.0, "bold": True, "description": "% DV header"},
}

# Required nutrient elements per 2016 rule (in order)
_REQUIRED_NUTRIENTS_2016: list[str] = [
    "Total Fat",
    "Saturated Fat",
    "Trans Fat",
    "Cholesterol",
    "Sodium",
    "Total Carbohydrate",
    "Dietary Fiber",
    "Total Sugars",
    "Added Sugars",
    "Protein",
    "Vitamin D",
    "Calcium",
    "Iron",
    "Potassium",
]

# Patterns to detect nutrition facts panel text
_NUTRITION_FACTS_PATTERN = re.compile(r"nutrition\s*facts", re.IGNORECASE)
_CALORIES_PATTERN = re.compile(r"\bcalories\b", re.IGNORECASE)
_SERVING_SIZE_PATTERN = re.compile(r"serving\s*size", re.IGNORECASE)


def _extract_text_events_for_page(
    events: list[ContentStreamEvent], page_num: int
) -> list[dict[str, Any]]:
    """Extract text rendering events for a specific page."""
    from lintpdf.semantic.events import TextRenderedEvent

    text_events: list[dict[str, Any]] = []
    for event in events:
        if isinstance(event, TextRenderedEvent) and event.page_num == page_num:
            text_events.append(
                {
                    "font_name": event.font_name,
                    "font_size": abs(event.font_size),
                    "page_num": event.page_num,
                    "bbox": event.bbox,
                    "rendering_mode": event.rendering_mode,
                }
            )
    return text_events


def _is_bold_font(font_name: str) -> bool:
    """Check if font name indicates bold weight."""
    lower = font_name.lower()
    return "bold" in lower or "black" in lower or "heavy" in lower


def _find_nutrition_panel_pages(
    document: SemanticDocument,
) -> list[int]:
    """Identify pages that likely contain a Nutrition Facts panel."""
    panel_pages: list[int] = []
    for page in document.pages:
        if page.content_stream:
            raw = page.content_stream
            if isinstance(raw, bytes):
                try:
                    decoded = raw.decode("latin-1")
                except Exception:
                    decoded = ""
            else:
                decoded = str(raw)

            if _NUTRITION_FACTS_PATTERN.search(decoded):
                panel_pages.append(page.page_num)

    return panel_pages


@register_ai_analyzer
class FdaNutritionAnalyzer(BaseAIAnalyzer):
    """Validate FDA Nutrition Facts label per 21 CFR 101.9."""

    category = "regulatory_compliance"
    feature_slug = "fda_nutrition_facts"
    tier = "cpu"
    credits_per_run = 1

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        findings: list[Finding] = []

        panel_pages = _find_nutrition_panel_pages(document)
        if not panel_pages:
            # No Nutrition Facts panel detected — not necessarily an error
            return []

        for page_num in panel_pages:
            page_findings = self._check_panel_page(document, events, page_num)
            findings.extend(page_findings)

        return findings

    def _check_panel_page(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        page_num: int,
    ) -> list[Finding]:
        """Check a single page's Nutrition Facts panel."""
        findings: list[Finding] = []
        text_events = _extract_text_events_for_page(events, page_num)

        if not text_events:
            return []

        # Build a map of font sizes used on this page
        font_sizes: dict[str, float] = {}
        for te in text_events:
            key = te["font_name"]
            size = te["font_size"]
            if key not in font_sizes or size > font_sizes[key]:
                font_sizes[key] = size

        # Check: find the largest font size — likely "Nutrition Facts" or "Calories"
        all_sizes = [te["font_size"] for te in text_events if te["font_size"] > 0]
        if not all_sizes:
            return []

        max_size = max(all_sizes)
        min_size = min(all_sizes)

        # Check Calories font size (should be ≥22pt per 2016 rule)
        # The largest text should be either "Nutrition Facts" heading or "Calories"
        # "Calories" value should be the most prominent number

        # Identify text events near the "Calories" declaration
        _calories_events = [
            te
            for te in text_events
            if te["font_size"] >= 16.0  # Filter for larger text that might be Calories
        ]

        # Check minimum font sizes against requirements
        for label, req in _FDA_FONT_REQUIREMENTS.items():
            min_pt = req["min_pt"]
            _needs_bold = req["bold"]

            # For "Calories", check the largest font
            if label == "Calories" and max_size < min_pt:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_FDA_001",
                        severity=Severity.ERROR,
                        message=(
                            f"Calories declaration may be below minimum "
                            f"font size (largest: {max_size:.1f}pt, "
                            f"required: ≥{min_pt}pt per 21 CFR 101.9)"
                        ),
                        page_num=page_num,
                        details={
                            "element": label,
                            "found_size_pt": max_size,
                            "required_min_pt": min_pt,
                            "regulation": "21 CFR 101.9",
                        },
                        object_type="text",
                    )
                )

        # Check that body text is at minimum 6pt (absolute minimum for any NFP text)
        if 0 < min_size < 6.0:
            findings.append(
                self._make_finding(
                    inspection_id="AI_FDA_002",
                    severity=Severity.ERROR,
                    message=(
                        f"Nutrition Facts text below minimum readable size "
                        f"({min_size:.1f}pt, FDA requires ≥6pt for any NFP text)"
                    ),
                    page_num=page_num,
                    details={
                        "found_min_size_pt": min_size,
                        "required_min_pt": 6.0,
                        "regulation": "21 CFR 101.9",
                    },
                    object_type="text",
                )
            )

        # Check bold requirements — look for bold fonts in text events
        bold_fonts_used = any(_is_bold_font(te["font_name"]) for te in text_events)
        if not bold_fonts_used:
            findings.append(
                self._make_finding(
                    inspection_id="AI_FDA_003",
                    severity=Severity.WARNING,
                    message=(
                        "No bold fonts detected in Nutrition Facts panel. "
                        "21 CFR 101.9 requires bold for key headings "
                        "(Nutrition Facts, Calories, Serving size, % Daily Value)."
                    ),
                    page_num=page_num,
                    details={
                        "regulation": "21 CFR 101.9",
                        "fonts_found": list(font_sizes.keys()),
                    },
                    object_type="text",
                )
            )

        # Check for required 2016 rule elements by scanning content stream text
        page = next((p for p in document.pages if p.page_num == page_num), None)
        if page and page.content_stream:
            raw = page.content_stream
            if isinstance(raw, bytes):
                try:
                    page_text = raw.decode("latin-1")
                except Exception:
                    page_text = ""
            else:
                page_text = str(raw)

            # Check for required nutrients
            missing_nutrients: list[str] = []
            for nutrient in _REQUIRED_NUTRIENTS_2016:
                pattern = re.compile(re.escape(nutrient), re.IGNORECASE)
                if not pattern.search(page_text):
                    missing_nutrients.append(nutrient)

            if missing_nutrients:
                # "Added Sugars" was new in the 2016 rule — flag specially
                is_added_sugars_missing = "Added Sugars" in missing_nutrients

                findings.append(
                    self._make_finding(
                        inspection_id="AI_FDA_004",
                        severity=Severity.ERROR if is_added_sugars_missing else Severity.WARNING,
                        message=(
                            f"Potentially missing required nutrients in NFP: "
                            f"{', '.join(missing_nutrients)}"
                        ),
                        page_num=page_num,
                        details={
                            "missing_nutrients": missing_nutrients,
                            "regulation": "21 CFR 101.9 (2016 rule)",
                            "total_required": len(_REQUIRED_NUTRIENTS_2016),
                            "total_missing": len(missing_nutrients),
                        },
                        object_type="text",
                    )
                )

            # Check nutrient ordering (for those that are found)
            found_positions: list[tuple[str, int]] = []
            for nutrient in _REQUIRED_NUTRIENTS_2016:
                match = re.search(re.escape(nutrient), page_text, re.IGNORECASE)
                if match:
                    found_positions.append((nutrient, match.start()))

            # Verify order
            if len(found_positions) >= 2:
                for i in range(len(found_positions) - 1):
                    curr_name, curr_pos = found_positions[i]
                    next_name, next_pos = found_positions[i + 1]
                    if curr_pos > next_pos:
                        findings.append(
                            self._make_finding(
                                inspection_id="AI_FDA_005",
                                severity=Severity.WARNING,
                                message=(
                                    f"Nutrient ordering issue: '{curr_name}' appears "
                                    f"after '{next_name}' in the panel (21 CFR 101.9 "
                                    f"mandates a specific order)"
                                ),
                                page_num=page_num,
                                details={
                                    "out_of_order": [curr_name, next_name],
                                    "regulation": "21 CFR 101.9",
                                },
                                object_type="text",
                            )
                        )
                        break  # Report first ordering violation only

        return findings
