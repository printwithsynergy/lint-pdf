"""SoloSpotVerifyAnalyzer — flags single-Separation jobs where the
sole spot has a non-dieline-like name. Asks the operator to confirm
the spot is intended as a decorative ink plate vs. accidentally being
used as a cut/perf indicator.

Audit closure (PR-CC): Opus 4.7 flagged Pavette_Pride_v99 — the file
declares exactly one Separation (``/rose pink``) and uses it for
visible decorative artwork (frame, bullets, rule lines). Without an
explicit confirmation, downstream operators can't tell whether the
press should mount a pink ink plate or treat it as a technical layer.

Check ID:
    LPDF_SPOT_SOLO_VERIFY — Single-Separation document with a
        non-dieline spot name. Severity: ADVISORY.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from siftpdf.analyzers.base import BaseAnalyzer
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument


# Tokens that mark a spot as a dieline / processing-step ink. If the
# sole spot matches these we suppress — the user clearly intended it
# as a technical layer.
_DIELINE_TOKENS: frozenset[str] = frozenset(
    {
        "die",
        "dieline",
        "die_line",
        "die-line",
        "cut",
        "cutting",
        "cut_contour",
        "cutcontour",
        "kiss_cut",
        "kisscut",
        "trim",
        "perf",
        "perforating",
        "perforation",
        "score",
        "scoring",
        "crease",
        "creasing",
        "fold",
        "foldline",
        "fold_line",
        "tear",
        "tear_line",
        "tearline",
        "registration",
        "varnish",
        "varnishing",
    }
)


def _normalise_name(raw: str | None) -> str:
    if not raw:
        return ""
    return str(raw).strip().lstrip("/").lower().replace("-", "_").replace(" ", "_")


def _is_dieline_token(name: str) -> bool:
    norm = _normalise_name(name)
    if not norm:
        return False
    if norm in _DIELINE_TOKENS:
        return True
    # Catch compounds like "die_cut_outer" / "perf_line_1" by token search
    return any(tok in norm for tok in _DIELINE_TOKENS)


class SoloSpotVerifyAnalyzer(BaseAnalyzer):
    """Flag single-Separation jobs with a non-dieline spot name."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        # Collect distinct Separation/DeviceN colorant names across the
        # document — skip /All, /None, and process names.
        names: set[str] = set()
        for page in getattr(document, "pages", None) or []:
            for cs in (getattr(page, "color_spaces", None) or {}).values():
                if getattr(cs, "cs_type", None) not in (
                    "Separation",
                    "DeviceN",
                    "NChannel",
                ):
                    continue
                for raw in getattr(cs, "colorant_names", None) or ():
                    if not raw:
                        continue
                    norm = _normalise_name(raw)
                    if norm in {"all", "none", "cyan", "magenta", "yellow", "black"}:
                        continue
                    names.add(str(raw))

        if len(names) != 1:
            return []

        sole = next(iter(names))
        if _is_dieline_token(sole):
            return []  # operator clearly intended a technical layer

        return [
            Finding(
                inspection_id="LPDF_SPOT_SOLO_VERIFY",
                severity=Severity.ADVISORY,
                message=(
                    f"Document declares a single Separation '{sole}' that does not "
                    "look like a dieline / cutter / processing-step name. Confirm "
                    "with the printer that this spot is intended as a decorative "
                    "ink plate (e.g. a brand spot) and not accidentally being "
                    "used to indicate a die/cut. If it's a technical layer, "
                    "rename to follow ISO 19593-1 (Cutting / Perforating / "
                    "Scoring / Creasing)."
                ),
                details={
                    "colorant_name": sole,
                    "distinct_spot_count": 1,
                },
                category="color",
                object_type="document",
            )
        ]
