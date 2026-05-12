"""Read codex's detected_barcodes and surface them as findings."""

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
class CodexBarcodesReader(BaseAIAnalyzer):
    """Emit findings for each barcode codex decoded on a page."""

    category = "codex_signals"
    feature_slug = "codex_barcodes"
    tier = "cpu"
    credits_per_run = 0

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        payload = codex_payload(ctx)
        if payload is None or codex_ai_skipped(payload):
            return []
        findings: list[Finding] = []
        for page in codex_pages(payload):
            barcodes = page.get("detected_barcodes")
            if not isinstance(barcodes, list):
                continue
            page_num = page.get("page_num") if isinstance(page.get("page_num"), int) else 0
            for bc in barcodes:
                if not isinstance(bc, dict):
                    continue
                fmt = bc.get("format") or "unknown"
                value = bc.get("value") or ""
                findings.append(
                    self._make_finding(
                        inspection_id="CODEX_BARCODE",
                        severity=Severity.INFO,
                        message=f"Decoded barcode ({fmt}): {value}",
                        page_num=page_num,
                        details={
                            "format": fmt,
                            "value": value,
                            "source": bc.get("source"),
                        },
                        bbox=_bbox_tuple(bc.get("bbox")),
                    )
                )
        return findings
