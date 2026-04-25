"""Cannabis labeling compliance analyzer (state-specific requirements).

Detects whether the document is cannabis packaging (auto-detection via
THC/CBD potency phrase or cannabis-class keyword), then verifies the
multi-state common requirements:

- "Keep out of reach of children" warning
- Cannabis warning symbol declaration
- THC/CBD potency declaration

AI_CANN_001 aggregates missing items into one finding.

AI_CANN_002 cross-checks declared per-serving x servings against
declared total mg, and flags per-serving doses above the CO 10 mg
threshold.

Read-only. Silent on non-cannabis documents.
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


_THC_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*mg\s*(?:of\s+)?(THC|delta[-\s]*9|delta[-\s]*8|tetrahydrocannabinol)\b",
    re.IGNORECASE,
)
_THC_REVERSE_PATTERN = re.compile(
    r"\b(THC|delta[-\s]*9|delta[-\s]*8)[\s:]*(\d+(?:\.\d+)?)\s*mg\b",
    re.IGNORECASE,
)
_CBD_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*mg\s*(?:of\s+)?(CBD|cannabidiol)\b",
    re.IGNORECASE,
)

_CANNABIS_KEYWORD_PATTERN = re.compile(
    r"\b(cannabis|marijuana|medical\s+marijuana|recreational\s+marijuana|"
    r"licensed\s+producer|dispensary|cultivator)\b",
    re.IGNORECASE,
)

_KEEP_OUT_PATTERN = re.compile(
    r"\bkeep\s+out\s+of\s+(the\s+)?reach\s+of\s+children\b", re.IGNORECASE
)
_SYMBOL_PATTERN = re.compile(
    r"\b(universal\s+symbol|cannabis\s+(warning\s+)?symbol|THC\s+stamp|"
    r"poison\s+control|warning\s+triangle)\b",
    re.IGNORECASE,
)

_PER_SERVING_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*mg(?:\s+(?:THC|CBD|delta[-\s]*9|delta[-\s]*8))?\s*"
    r"(?:per|/)\s*serving\b",
    re.IGNORECASE,
)
_SERVINGS_PATTERN = re.compile(r"\b(\d+)\s+servings?\b", re.IGNORECASE)
_TOTAL_THC_PATTERN = re.compile(
    r"\btotal\s+(?:THC|cannabinoids?)[\s:]*(\d+(?:\.\d+)?)\s*mg\b", re.IGNORECASE
)


@register_ai_analyzer
class CannabisLabelingAnalyzer(BaseAIAnalyzer):
    """Validates cannabis product labeling per state-specific regulations.

    Check IDs:
        AI_CANN_001: Missing required cannabis warning symbols or statements.
        AI_CANN_002: THC/CBD content declaration formatting violations.
    """

    category = "regulatory_compliance"
    feature_slug = "cannabis_labeling"
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
        thc_hits = list(_THC_PATTERN.finditer(text)) + list(_THC_REVERSE_PATTERN.finditer(text))
        cbd_hits = list(_CBD_PATTERN.finditer(text))
        keyword_hit = _CANNABIS_KEYWORD_PATTERN.search(text)
        is_cannabis = bool(thc_hits or (keyword_hit and (cbd_hits or thc_hits)))

        if not is_cannabis and not (thc_hits or keyword_hit):
            return []

        findings: list[Finding] = []
        missing: list[str] = []
        if not _KEEP_OUT_PATTERN.search(text):
            missing.append("keep_out_of_reach_of_children")
        if not _SYMBOL_PATTERN.search(text):
            missing.append("cannabis_warning_symbol")
        if not (thc_hits or cbd_hits):
            missing.append("potency_declaration")

        if missing:
            findings.append(
                self._make_finding(
                    inspection_id="AI_CANN_001",
                    severity=Severity.WARNING,
                    message=(f"Cannabis label missing required elements: {', '.join(missing)}."),
                    details={
                        "missing_elements": missing,
                        "thc_mentions": len(thc_hits),
                        "cbd_mentions": len(cbd_hits),
                        "regulation": "Multi-state cannabis labeling (CA/CO/OR/WA/etc.)",
                    },
                )
            )

        per_serving_match = _PER_SERVING_PATTERN.search(text)
        servings_match = _SERVINGS_PATTERN.search(text)
        total_match = _TOTAL_THC_PATTERN.search(text)
        format_issues: list[str] = []
        if per_serving_match:
            try:
                per_serving = float(per_serving_match.group(1))
            except (TypeError, ValueError):
                per_serving = 0.0
            if per_serving > 10.0:
                format_issues.append(f"per_serving_above_10mg:{per_serving}")
            if servings_match and total_match:
                try:
                    n_servings = int(servings_match.group(1))
                    total_mg = float(total_match.group(1))
                except (TypeError, ValueError):
                    n_servings = 0
                    total_mg = 0.0
                if n_servings > 0 and total_mg > 0:
                    expected = per_serving * n_servings
                    if abs(expected - total_mg) > 0.10 * total_mg:
                        format_issues.append(
                            f"potency_arithmetic_mismatch:expected={expected:.1f}_declared={total_mg:.1f}"
                        )
        if format_issues:
            findings.append(
                self._make_finding(
                    inspection_id="AI_CANN_002",
                    severity=Severity.ADVISORY,
                    message=(f"Cannabis potency formatting issues: {', '.join(format_issues)}."),
                    details={
                        "format_issues": format_issues,
                        "regulation": "CO MED Rule 3-1015 / multi-state dosage limits",
                    },
                )
            )

        return findings


def _collect_text(document: SemanticDocument) -> str:
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
