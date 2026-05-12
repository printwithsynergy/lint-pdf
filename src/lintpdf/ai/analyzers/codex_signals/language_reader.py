"""Read codex's per-page detected_language and surface it as a finding."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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

logger = logging.getLogger(__name__)


@register_ai_analyzer
class CodexLanguageReader(BaseAIAnalyzer):
    """Emit one finding per page recording codex's detected language."""

    category = "codex_signals"
    feature_slug = "codex_language"
    tier = "cpu"
    credits_per_run = 0  # codex's call; lint reads from cache

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        payload = codex_payload(ctx)
        if payload is None or codex_ai_skipped(payload):
            return []
        findings: list[Finding] = []
        for page in codex_pages(payload):
            language = page.get("detected_language")
            if not isinstance(language, dict):
                continue
            code = language.get("code")
            if not isinstance(code, str) or not code:
                continue
            try:
                confidence = float(language.get("confidence", 1.0))
            except (TypeError, ValueError):
                confidence = 1.0
            page_num = page.get("page_num") if isinstance(page.get("page_num"), int) else 0
            findings.append(
                self._make_finding(
                    inspection_id="CODEX_LANGUAGE",
                    severity=Severity.ADVISORY,
                    message=f"Detected language: {code} (confidence {confidence:.2f})",
                    page_num=page_num,
                    details={
                        "code": code,
                        "confidence": confidence,
                        "source": language.get("source"),
                    },
                )
            )
        return findings
