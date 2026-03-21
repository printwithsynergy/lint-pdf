"""Dieline detection by spot color name in color spaces.

Scans page-level color space definitions for Separation and DeviceN entries
whose colorant names match common dieline-related naming conventions used
in packaging artwork (CutContour, Dieline, Die, Crease, Score, etc.).
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

# Case-insensitive dieline-associated colorant names
_DIELINE_NAMES: set[str] = {
    "cutcontour",
    "dieline",
    "die",
    "diecut",
    "kiss",
    "kisscut",
    "crease",
    "score",
    "perf",
    "thru-cut",
    "thrucut",
    "perforation",
    "foldline",
    "fold",
}


def _is_dieline_name(name: str) -> bool:
    """Check if a colorant name matches a known dieline-associated name."""
    return name.strip().lower() in _DIELINE_NAMES


@register_ai_analyzer
class DielineByColorNameAnalyzer(BaseAIAnalyzer):
    """Detect dieline elements by scanning spot color names in color spaces."""

    category = "dieline_detection"
    feature_slug = "dieline_by_color_name"
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
        seen: set[str] = set()

        for page in document.pages:
            for cs_name, cs in page.color_spaces.items():
                if cs.cs_type not in ("Separation", "DeviceN"):
                    continue
                if not cs.colorant_names:
                    continue

                for colorant in cs.colorant_names:
                    if not colorant or colorant in ("All", "None"):
                        continue

                    lower_name = colorant.strip().lower()
                    if lower_name in seen:
                        continue

                    if _is_dieline_name(colorant):
                        seen.add(lower_name)
                        findings.append(
                            self._make_finding(
                                inspection_id="GRD_AI_DIEL_002",
                                severity=Severity.ADVISORY,
                                message=(
                                    f"Dieline spot color detected: '{colorant}' "
                                    f"(color space '{cs_name}', type {cs.cs_type}) "
                                    f"on page {page.page_num}"
                                ),
                                page_num=page.page_num,
                                details={
                                    "colorant_name": colorant,
                                    "color_space_name": cs_name,
                                    "color_space_type": cs.cs_type,
                                },
                            )
                        )

        return findings
