"""Read codex's per-page spell_candidates and surface them as findings."""

from __future__ import annotations

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

_MAX_CANDIDATES_REPORTED = 10


@register_ai_analyzer
class CodexSpellReader(BaseAIAnalyzer):
    """One finding per page summarising codex's spell candidates.

    Codex doesn't apply the tenant dictionary policy — that's still
    lint's job. This reader surfaces the raw candidate list so a
    follow-up analyzer (or the consumer's UI) can decide which
    candidates are real misspellings vs valid brand-y words.
    """

    category = "codex_signals"
    feature_slug = "codex_spell"
    tier = "cpu"
    credits_per_run = 0

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        payload = codex_payload(ctx)
        if payload is None or codex_ai_skipped(payload):
            return []
        findings: list[Finding] = []
        for page in codex_pages(payload):
            candidates = page.get("spell_candidates")
            if not isinstance(candidates, list) or not candidates:
                continue
            page_num = page.get("page_num") if isinstance(page.get("page_num"), int) else 0
            preview = ", ".join(str(c) for c in candidates[:_MAX_CANDIDATES_REPORTED])
            extra = (
                f" (+{len(candidates) - _MAX_CANDIDATES_REPORTED} more)"
                if len(candidates) > _MAX_CANDIDATES_REPORTED
                else ""
            )
            findings.append(
                self._make_finding(
                    inspection_id="CODEX_SPELL",
                    severity=Severity.ADVISORY,
                    message=f"{len(candidates)} spell candidate(s): {preview}{extra}",
                    page_num=page_num,
                    details={"candidates": list(candidates)},
                )
            )
        return findings
