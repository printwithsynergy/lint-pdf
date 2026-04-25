"""Cosmetics labeling compliance analyzer (EU 1223/2009, FDA 21 CFR 700-740).

Detects whether the document is a cosmetic label (auto-detection via
INCI ingredient header or cosmetic-class keyword), then verifies the
required EU + FDA elements:

- Ingredient list (INCI header + tokens)
- Net quantity (weight or volume declaration)
- PAO symbol (period-after-opening token)
- Batch / lot code

AI_COSM_001 aggregates missing items into one finding.

AI_COSM_002 flags INCI nomenclature/ordering issues — first non-water
token suggests a reorder violation; mixed case suggests non-INCI
nomenclature.

Read-only. Silent on non-cosmetic documents.
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


_INGREDIENTS_HEADER = re.compile(
    r"\b(INGREDIENTS|INGRÉDIENTS|INGREDIENTES|INCI)\s*[:\-]\s*", re.IGNORECASE
)

_COSM_CLASS_PATTERN = re.compile(
    r"\b("
    r"shampoo|conditioner|lotion|moisturi[sz]er|serum|cream|balm|"
    r"mascara|lipstick|lip\s+gloss|foundation|concealer|blush|"
    r"eyeshadow|eyeliner|cleanser|toner|deodorant|antiperspirant|"
    r"perfume|fragrance|eau\s+de\s+toilette|eau\s+de\s+parfum|cologne|"
    r"sunscreen|aftershave|body\s+wash|shower\s+gel|hand\s+soap"
    r")\b",
    re.IGNORECASE,
)

_NET_QTY_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(g|ml|fl\s*oz|oz|l|kg|mg)\b(?:\s*(?:e|net|net\s+wt))?",
    re.IGNORECASE,
)

_PAO_PATTERN = re.compile(
    r"\b(\d+\s*M)\b(?=\s*(?:month|after\s+opening|period\s+after\s+opening|$|\W))",
    re.IGNORECASE,
)

_BATCH_PATTERN = re.compile(
    r"\b(BATCH|LOT|LOT\s+NO\.?|BATCH\s+CODE|LOT\s+CODE)\b[\s:]*[A-Za-z0-9-]{2,}",
    re.IGNORECASE,
)


@register_ai_analyzer
class CosmeticsLabelingAnalyzer(BaseAIAnalyzer):
    """Validates cosmetics labeling per EU 1223/2009 and FDA 21 CFR 701.

    Check IDs:
        AI_COSM_001: Missing required cosmetics labeling elements (ingredients list,
                     PAO symbol, batch code).
        AI_COSM_002: INCI ingredient nomenclature or ordering violations.
    """

    category = "regulatory_compliance"
    feature_slug = "cosmetics_labeling"
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
        ingredient_match = _INGREDIENTS_HEADER.search(text)
        class_match = _COSM_CLASS_PATTERN.search(text)
        if not (ingredient_match or class_match):
            return []

        findings: list[Finding] = []
        missing: list[str] = []
        if not ingredient_match:
            missing.append("ingredient_list")
        if not _NET_QTY_PATTERN.search(text):
            missing.append("net_quantity")
        if not _PAO_PATTERN.search(text):
            missing.append("pao_symbol")
        if not _BATCH_PATTERN.search(text):
            missing.append("batch_code")

        if missing:
            findings.append(
                self._make_finding(
                    inspection_id="AI_COSM_001",
                    severity=Severity.WARNING,
                    message=(f"Cosmetic label missing required elements: {', '.join(missing)}."),
                    details={
                        "missing_elements": missing,
                        "regulation": "EU 1223/2009 Article 19; FDA 21 CFR 701",
                    },
                )
            )

        if ingredient_match:
            tail = text[ingredient_match.end() : ingredient_match.end() + 1500]
            tokens = [t.strip() for t in re.split(r"[,;]", tail) if t.strip()]
            tokens = tokens[:30]
            format_issues: list[str] = []
            if tokens:
                first_clean = re.sub(r"[^A-Za-zÀ-ÿ\s]", "", tokens[0]).strip().upper()
                first_word = first_clean.split(" ", 1)[0] if first_clean else ""
                if first_word and first_word not in {"AQUA", "WATER", "EAU", "AGUA"}:
                    format_issues.append(f"first_token_not_water:{tokens[0][:40]}")

                lower_count = sum(
                    1
                    for tok in tokens
                    if any(c.islower() for c in tok) and any(c.isalpha() for c in tok)
                )
                if lower_count > len(tokens) * 0.30:
                    format_issues.append(
                        f"non_inci_nomenclature:{lower_count}/{len(tokens)}_lowercase"
                    )
            if format_issues:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_COSM_002",
                        severity=Severity.ADVISORY,
                        message=(f"Cosmetic ingredient list issues: {', '.join(format_issues)}."),
                        details={
                            "format_issues": format_issues,
                            "token_sample": tokens[:5],
                            "regulation": "EU 1223/2009 Article 19(1)(g) — INCI",
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
