"""Read codex's detected_symbols and surface them as findings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lintpdf.ai.analyzers.codex_signals._common import (
    codex_ai_skipped,
    codex_pages,
    codex_payload,
)
from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext


def _bbox_tuple(bbox: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(bbox, dict):
        return None
    try:
        return (
            float(bbox.get("x0", 0)),
            float(bbox.get("y0", 0)),
            float(bbox.get("x1", 0)),
            float(bbox.get("y1", 0)),
        )
    except (TypeError, ValueError):
        return None


@register_ai_analyzer
class CodexSymbolsReader(BaseAIAnalyzer):
    """Emit findings for regulatory / packaging symbols codex spotted."""

    category = "codex_signals"
    feature_slug = "codex_symbols"
    tier = "cpu"
    credits_per_run = 0

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        payload = codex_payload(ctx)
        if payload is None or codex_ai_skipped(payload):
            return []
        findings: list[Finding] = []
        for page in codex_pages(payload):
            symbols = page.get("detected_symbols")
            if not isinstance(symbols, list):
                continue
            page_num = page.get("page_num") if isinstance(page.get("page_num"), int) else 0
            for sym in symbols:
                if not isinstance(sym, dict):
                    continue
                kind = sym.get("kind")
                if not isinstance(kind, str) or not kind:
                    continue
                try:
                    confidence = float(sym.get("confidence", 1.0))
                except (TypeError, ValueError):
                    confidence = 1.0
                findings.append(
                    self._make_finding(
                        inspection_id="CODEX_SYMBOL",
                        severity=Severity.ADVISORY,
                        message=f"Detected symbol: {kind} (confidence {confidence:.2f})",
                        page_num=page_num,
                        details={
                            "kind": kind,
                            "confidence": confidence,
                            "source": sym.get("source"),
                        },
                        bbox=_bbox_tuple(sym.get("bbox")),
                    )
                )
        return findings
