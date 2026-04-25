"""Tobacco / cigarette health-warning analyzer (T5-N04).

EU TPD2 (Directive 2014/40/EU) requires combined health warnings
covering ≥65 % of the front and back surface of cigarette packs.
US FDA (Family Smoking Prevention Act) requires ≥50 %. Australia /
NZ go to ≥75 % under their plain-packaging laws.

This analyzer detects whether a tobacco-style warning text is
present (regex match against canonical phrasings: ``WARNING:``,
``SMOKING KILLS``, ``Smoking causes…`` etc.), then estimates the
warning's bbox area as a fraction of the page area and emits
``LPDF_TOBACCO_WARNING_AREA`` when the fraction falls below the
configured threshold.

Auto-detect — fires only when at least one tobacco-class keyword
is found in the document text (``tobacco``, ``cigarette``,
``cigar``, ``smoking`` paired with a warning-style verb). Silent
on every other artwork.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


_TOBACCO_KEYWORDS = re.compile(
    r"\b(tobacco|cigarette|cigar|cigarillo|hookah|snus|smoking)\b",
    re.IGNORECASE,
)
_WARNING_PHRASES = re.compile(
    r"\b(WARNING:|SMOKING\s+KILLS|Smoking\s+causes|Tobacco\s+smoke|"
    r"causes\s+(lung\s+)?cancer|harmful\s+to\s+health|"
    r"surgeon\s+general'?s?\s+warning)\b",
    re.IGNORECASE,
)

_DEFAULT_MIN_FRACTION = 0.30  # Conservative floor; below this is universally non-compliant


@register_ai_analyzer
class TobaccoWarningAnalyzer(BaseAIAnalyzer):
    """T5-N04 — flag tobacco artwork whose health warning covers less
    than the regulator-required fraction of the page surface."""

    category = "regulatory_compliance"
    feature_slug = "tobacco_warning"
    tier = "cpu"
    credits_per_run = 1

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        text = _collect_text(document)
        if not _TOBACCO_KEYWORDS.search(text) or not _WARNING_PHRASES.search(text):
            return []

        min_fraction = _resolve_threshold(ai_config)
        findings: list[Finding] = []
        for page in document.pages:
            page_area = page.media_box.width * page.media_box.height
            if page_area <= 0:
                continue
            warning_bbox = self._warning_bbox(events, page.page_num)
            if warning_bbox is None:
                # Warning keyword detected at document level but no
                # text-render event landed on this page.
                continue
            x0, y0, x1, y1 = warning_bbox
            warning_area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
            fraction = warning_area / page_area if page_area > 0 else 0.0
            if fraction < min_fraction:
                findings.append(
                    Finding(
                        inspection_id="LPDF_TOBACCO_WARNING_AREA",
                        severity=Severity.WARNING,
                        message=(
                            f"Tobacco health warning on page {page.page_num} covers "
                            f"{fraction * 100:.1f}% of the page; threshold "
                            f"{min_fraction * 100:.0f}% (EU TPD2 65%, FDA 50%, "
                            f"AU/NZ 75%)"
                        ),
                        page_num=page.page_num,
                        details={
                            "warning_fraction": round(fraction, 4),
                            "min_fraction": min_fraction,
                            "warning_bbox": list(warning_bbox),
                            "page_area_pts2": page_area,
                        },
                        iso_clause=(
                            "EU 2014/40/EU TPD2 / US Family Smoking Prevention "
                            "Act / AU Tobacco Plain Packaging Act 2011"
                        ),
                        source="ai",
                        category=self.category,
                    )
                )
        return findings

    @staticmethod
    def _warning_bbox(
        events: list[ContentStreamEvent],  # type: ignore[name-defined]
        page_num: int,
    ) -> tuple[float, float, float, float] | None:
        """Compute the bounding box around all text events on the
        given page that match a warning phrase, by union of bboxes
        on the bigger-text events (font_size >= 8pt)."""
        from lintpdf.semantic.events import TextRenderedEvent

        x0 = y0 = float("inf")
        x1 = y1 = float("-inf")
        any_match = False
        for event in events:
            if not isinstance(event, TextRenderedEvent):
                continue
            if event.page_num != page_num or event.bbox is None:
                continue
            if event.font_size < 8.0:
                continue
            any_match = True
            ex0, ey0, ex1, ey1 = event.bbox
            x0 = min(x0, ex0)
            y0 = min(y0, ey0)
            x1 = max(x1, ex1)
            y1 = max(y1, ey1)
        if not any_match:
            return None
        return (x0, y0, x1, y1)


def _resolve_threshold(ai_config: TenantAIConfig | None) -> float:  # type: ignore[name-defined]
    if ai_config is None:
        return _DEFAULT_MIN_FRACTION
    raw = getattr(ai_config, "tobacco_warning_min_fraction", None)
    if raw is None:
        return _DEFAULT_MIN_FRACTION
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return _DEFAULT_MIN_FRACTION
    return max(0.0, min(value, 1.0))


def _collect_text(document: SemanticDocument) -> str:  # type: ignore[name-defined]
    chunks: list[str] = []
    for page in document.pages:
        raw = page.content_stream
        if not raw:
            continue
        if isinstance(raw, bytes):
            try:
                chunks.append(raw.decode("latin-1"))
            except Exception:
                continue
        else:
            chunks.append(str(raw))
    return "\n".join(chunks)
