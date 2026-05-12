"""Read codex's detected_logos and surface them as findings."""

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
class CodexLogosReader(BaseAIAnalyzer):
    """Emit findings for each logo codex detected on a page."""

    category = "codex_signals"
    feature_slug = "codex_logos"
    tier = "cpu"
    credits_per_run = 0

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        payload = codex_payload(ctx)
        if payload is None or codex_ai_skipped(payload):
            return []
        findings: list[Finding] = []
        for page in codex_pages(payload):
            logos = page.get("detected_logos")
            if not isinstance(logos, list):
                continue
            page_num = page.get("page_num") if isinstance(page.get("page_num"), int) else 0
            for logo in logos:
                if not isinstance(logo, dict):
                    continue
                identity = logo.get("identity") or "unknown"
                try:
                    confidence = float(logo.get("confidence", 1.0))
                except (TypeError, ValueError):
                    confidence = 1.0
                bbox = _bbox_tuple(logo.get("bbox"))
                findings.append(
                    self._make_finding(
                        inspection_id="CODEX_LOGO",
                        severity=Severity.INFO,
                        message=f"Detected logo: {identity} (confidence {confidence:.2f})",
                        page_num=page_num,
                        details={
                            "identity": identity,
                            "confidence": confidence,
                            "source": logo.get("source"),
                        },
                        bbox=bbox,
                    )
                )
        return findings
