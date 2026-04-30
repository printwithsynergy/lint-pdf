"""Alcohol labeling compliance analyzer (TTB, EU wine/spirits).

Detects whether the document is an alcohol label (auto-detection via
ABV pattern or product-class keyword), then verifies the required TTB
27 CFR / EU 1169-2011 elements:

- ABV declaration
- TTB Government Warning (US labels)
- Country of origin / "Product of"

AI_ALC_001 aggregates missing elements into a single finding so labels
missing two or three things still produce one row, not three.

AI_ALC_002 flags ABV-format violations (precision, plausibility,
preferred TTB notation).

Read-only. Silent when neither ABV nor a class keyword is present.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.ai.types import AIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


_ABV_PATTERN = re.compile(
    r"\b(\d{1,2}(?:\.\d+)?)\s*%\s*"
    r"(ALC(?:OHOL)?\.?(?:\s*BY\s*VOL(?:UME)?)?|ABV|ALC/VOL|VOL/ALC)\b",
    re.IGNORECASE,
)

_ALC_CLASS_PATTERN = re.compile(
    r"\b("
    r"beer|ale|lager|stout|porter|pilsner|"
    r"wine|champagne|prosecco|cava|sparkling\s+wine|"
    r"cider|mead|sake|"
    r"vodka|gin|rum|tequila|mezcal|"
    r"whisky|whiskey|bourbon|scotch|rye|"
    r"cognac|armagnac|brandy|"
    r"liqueur|vermouth|absinthe|aperitif|digestif"
    r")\b",
    re.IGNORECASE,
)

_GOV_WARNING_PATTERN = re.compile(r"\bGOVERNMENT\s+WARNING\b", re.IGNORECASE)
_ORIGIN_PATTERN = re.compile(
    r"\b(Product\s+of|Imported\s+from|Made\s+in|Bottled\s+in|Distilled\s+in|"
    r"Brewed\s+in|Produced\s+in)\b",
    re.IGNORECASE,
)

_WINE_KEYWORDS = re.compile(
    r"\b(wine|champagne|prosecco|cava|sparkling\s+wine|chardonnay|merlot|"
    r"cabernet|riesling|pinot|syrah|sauvignon|grenache|tempranillo|sangiovese|"
    r"chianti|bordeaux|burgundy|rioja|barolo|brunello|porto|sherry)\b",
    re.IGNORECASE,
)
_SPIRITS_KEYWORDS = re.compile(
    r"\b(vodka|gin|rum|tequila|mezcal|whisky|whiskey|bourbon|scotch|rye|"
    r"cognac|armagnac|brandy|liqueur|vermouth|absinthe)\b",
    re.IGNORECASE,
)
_SULFITES_PATTERN = re.compile(
    r"\b(contains\s+sulfites|may\s+contain\s+sulfites|contains\s+sulphites|"
    r"sulfite[s]?\s+added)\b",
    re.IGNORECASE,
)
_PROOF_PATTERN = re.compile(r"\b\d{2,3}\s*proof\b", re.IGNORECASE)
_ESTATE_BOTTLED_PATTERN = re.compile(r"\bestate\s+bottled\b", re.IGNORECASE)
_VINTAGE_PATTERN = re.compile(r"\bvintage\s+\d{4}\b", re.IGNORECASE)
_APPELLATION_PATTERN = re.compile(
    r"\b(Napa\s+Valley|Sonoma|Champagne|Bordeaux|Burgundy|Rioja|"
    r"Chianti|Tuscany|Mosel|Rheingau|Tokaj|Mendoza|Marlborough|"
    r"Stellenbosch|Barossa|Yarra)\b",
    re.IGNORECASE,
)


@register_ai_analyzer
class AlcoholLabelingAnalyzer(BaseAIAnalyzer):
    """Validates alcohol labeling per TTB (US) and EU wine/spirits regulations.

    Check IDs:
        AI_ALC_001: Missing required alcohol labeling elements (ABV, government
                    warning, country of origin).
        AI_ALC_002: TTB COLA or EU wine/spirits label format violations.
    """

    category = "regulatory_compliance"
    feature_slug = "alcohol_labeling"
    tier = "cpu"
    credits_per_run = 1

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: AIConfig = None,
    ) -> list[Finding]:
        text = _collect_text(document)
        abv_match = _ABV_PATTERN.search(text)
        class_match = _ALC_CLASS_PATTERN.search(text)
        if not (abv_match or class_match):
            return []

        findings: list[Finding] = []
        missing: list[str] = []
        if not abv_match:
            missing.append("abv_declaration")
        if not _GOV_WARNING_PATTERN.search(text):
            missing.append("ttb_government_warning")
        if not _ORIGIN_PATTERN.search(text):
            missing.append("country_of_origin")

        detected_class = class_match.group(1).lower() if class_match else None
        abv_pct: float | None = None
        if abv_match:
            try:
                abv_pct = float(abv_match.group(1))
            except (TypeError, ValueError):
                abv_pct = None

        if missing:
            findings.append(
                self._make_finding(
                    inspection_id="AI_ALC_001",
                    severity=Severity.WARNING,
                    message=(f"Alcohol label missing required elements: {', '.join(missing)}."),
                    details={
                        "missing_elements": missing,
                        "detected_class": detected_class,
                        "abv_pct": abv_pct,
                        "regulation": "TTB 27 CFR 4.36 / 5.37 / 7.71 / 16.21; EU 1169/2011",
                    },
                )
            )

        if abv_match and abv_pct is not None:
            format_issues: list[str] = []
            if abv_pct < 0.5 or abv_pct > 95.0:
                format_issues.append(f"abv_out_of_range:{abv_pct}")
            unit = abv_match.group(2).upper().replace(" ", "")
            if unit not in {"ALC/VOL", "ABV", "ALCBYVOL", "ALCOHOLBYVOL", "ALCOHOLBYVOLUME"}:
                format_issues.append(f"non_preferred_abv_unit:{abv_match.group(2)}")
            decimal_part = abv_match.group(1).split(".")[1] if "." in abv_match.group(1) else ""
            if len(decimal_part) > 1:
                format_issues.append(f"abv_excess_precision:{abv_match.group(1)}")
            if format_issues:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_ALC_002",
                        severity=Severity.ADVISORY,
                        message=(f"Alcohol label format issues: {', '.join(format_issues)}."),
                        details={
                            "format_issues": format_issues,
                            "abv_pct": abv_pct,
                            "abv_unit": abv_match.group(2),
                            "regulation": "TTB 27 CFR 4.36(b)(1)",
                        },
                    )
                )

        # T5-N05 — wine / spirits-specific TTB 27 CFR 4 + EU 1308/2013
        # checks that the broader AI_ALC_001 doesn't catch.
        wine_match = _WINE_KEYWORDS.search(text)
        spirits_match = _SPIRITS_KEYWORDS.search(text)

        wine_issues: list[str] = []
        if wine_match and not _SULFITES_PATTERN.search(text):
            # TTB 27 CFR 4.32(e) requires "CONTAINS SULFITES" on wine
            # labels with > 10 ppm SO2 (nearly all commercial wines).
            wine_issues.append("missing_contains_sulfites")
        if _ESTATE_BOTTLED_PATTERN.search(text) and not _APPELLATION_PATTERN.search(text):
            # "Estate Bottled" requires an appellation per TTB 27 CFR 4.26.
            wine_issues.append("estate_bottled_without_appellation")
        if _VINTAGE_PATTERN.search(text) and not _APPELLATION_PATTERN.search(text):
            # Vintage claims need an appellation per TTB 27 CFR 4.27.
            wine_issues.append("vintage_without_appellation")

        spirits_issues: list[str] = []
        if spirits_match and abv_pct is not None and not _PROOF_PATTERN.search(text):
            # TTB 27 CFR 5.37 allows ABV alone, but proof is the
            # historical norm and must be plausible relative to ABV
            # (proof = 2 × ABV in the US system). Soft advisory when
            # spirits omit proof entirely.
            spirits_issues.append("missing_proof_statement")

        if wine_issues:
            findings.append(
                self._make_finding(
                    inspection_id="AI_ALC_003",
                    severity=Severity.WARNING,
                    message=(
                        f"Wine label has TTB 27 CFR 4 / EU 1308/2013 issues: "
                        f"{', '.join(wine_issues)}."
                    ),
                    details={
                        "issues": wine_issues,
                        "product_type": "wine",
                        "regulation": "TTB 27 CFR 4 / EU 1308/2013",
                    },
                )
            )
        if spirits_issues:
            findings.append(
                self._make_finding(
                    inspection_id="AI_ALC_003",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Spirits label has TTB 27 CFR 5 issues: {', '.join(spirits_issues)}."
                    ),
                    details={
                        "issues": spirits_issues,
                        "product_type": "spirits",
                        "regulation": "TTB 27 CFR 5.37",
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
