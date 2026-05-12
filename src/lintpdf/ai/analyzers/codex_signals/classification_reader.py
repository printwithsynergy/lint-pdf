"""Read codex's document_classification probability map and surface it."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.ai.analyzers.codex_signals._common import (
    codex_ai_skipped,
    codex_payload,
)
from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext


@register_ai_analyzer
class CodexClassificationReader(BaseAIAnalyzer):
    """Emit one document-level finding describing codex's classification map.

    Classification is document-scoped (not per page) so this analyzer
    emits a single page_num=0 finding with the top labels surfaced.
    """

    category = "codex_signals"
    feature_slug = "codex_classification"
    tier = "cpu"
    credits_per_run = 0

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        payload = codex_payload(ctx)
        if payload is None or codex_ai_skipped(payload):
            return []
        classification = payload.get("document_classification")
        if not isinstance(classification, dict) or not classification:
            return []
        # Sort by descending probability for a stable top-3 surface.
        ordered = sorted(
            (
                (label, float(score))
                for label, score in classification.items()
                if isinstance(label, str)
            ),
            key=lambda kv: kv[1],
            reverse=True,
        )
        top = ordered[:3]
        summary = ", ".join(f"{label} ({score:.2f})" for label, score in top)
        return [
            self._make_finding(
                inspection_id="CODEX_CLASSIFICATION",
                severity=Severity.ADVISORY,
                message=f"Document classification: {summary}",
                page_num=0,
                details={"classification": dict(classification)},
            )
        ]
