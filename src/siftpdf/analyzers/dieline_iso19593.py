"""DielineIso19593Analyzer — flags single-spot dielines that should
decompose into ISO 19593-1 ProcessingSteps.

ISO 19593-1:2018 specifies that finishing/converting operations on a
PDF should be tagged as separate ProcessingStep spots — each cut,
fold, crease, perforation, embossing, varnish layer, etc. lives on its
own named separation so the converter's RIP can route each operation
to the right finishing tool.

The 2026-04-27 Opus audit flagged ~7 misses where the engine accepted
a single ``/Dieline`` (or ``/CutContour``) spot mixing perimeter cut
+ fold + perforation indicators, without flagging the missing
decomposition. Without it, downstream finishing has to eyeball the
artwork to decide what's a cut vs a fold vs a perf.

Check ID:
    LPDF_DIE_PROCESSING_STEPS — Single-spot dieline; ISO 19593-1
        ProcessingStep decomposition (separate Cutting / Crease /
        Perforating / Kiss-Cut etc. spots) is missing or partial.
        Severity: ADVISORY.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from siftpdf.analyzers.base import BaseAnalyzer
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument


# Generic dieline-style spot names. Case-insensitive, matched as
# full-token equality after lowercasing.
_DIELINE_GENERIC: frozenset[str] = frozenset(
    {
        "dieline",
        "die_line",
        "die-line",
        "die line",
        "cutcontour",
        "cut_contour",
        "cut-contour",
        "cut contour",
        "cut",
        "trim",
        "diecut",
        "die_cut",
    }
)

# Canonical ISO 19593-1 ProcessingStep names (Annex A.4 + common
# variants). Presence of any of these is evidence that the artwork
# already uses the standard.
_ISO_19593_PROCESSING_STEPS: frozenset[str] = frozenset(
    {
        "cutting",
        "perforating",
        "creasing",
        "crease",
        "kiss_cut",
        "kiss-cut",
        "kisscut",
        "score",
        "scoring",
        "foldline",
        "fold_line",
        "fold-line",
        "perfline",
        "perf_line",
        "perf-line",
        "bleedline",
        "bleed_line",
        "embossing",
        "deboss",
        "debossing",
        "varnish",
        "varnishing",
        "spot_varnish",
        "stamping",
        "hot_stamping",
        "foil",
        "foiling",
    }
)


def _norm(raw: str | None) -> str | None:
    if not raw:
        return None
    return raw.strip().strip("/").lower().replace("-", "_").replace(" ", "_")


class DielineIso19593Analyzer(BaseAnalyzer):
    """Detect single-spot dielines that lack ISO 19593-1
    ProcessingStep decomposition."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        # Collect every spot/devicen colorant name across the document.
        spot_names: set[str] = set()
        original_names: dict[str, str] = {}  # normalised → original
        for page in document.pages:
            for cs in (page.color_spaces or {}).values():
                if getattr(cs, "cs_type", None) not in ("Separation", "DeviceN", "NChannel"):
                    continue
                for colorant in getattr(cs, "colorant_names", None) or ():
                    norm = _norm(colorant)
                    if not norm:
                        continue
                    spot_names.add(norm)
                    original_names.setdefault(norm, colorant)

        # Generic dieline spots present.
        generic = spot_names & _DIELINE_GENERIC
        # ISO 19593-1 decomposition spots present.
        iso_steps = spot_names & _ISO_19593_PROCESSING_STEPS

        # Fire the advisory ONLY when:
        # * at least one generic dieline is declared, AND
        # * NO ISO-19593 ProcessingStep spots appear alongside it.
        # If the document already mixes both (e.g. ``/Dieline`` +
        # ``/Cutting``) the converter has the decomposition info;
        # don't double-flag.
        if not generic or iso_steps:
            return []

        # Pick the first generic name to surface in the message —
        # original casing for readability.
        generic_norm = sorted(generic)[0]
        generic_orig = original_names.get(generic_norm, generic_norm)

        return [
            Finding(
                inspection_id="LPDF_DIE_PROCESSING_STEPS",
                severity=Severity.ADVISORY,
                message=(
                    f"Single dieline spot '{generic_orig}' carries the cut, "
                    "fold, perf, and any other finishing operations as one "
                    "layer. ISO 19593-1 specifies a separate spot per "
                    "ProcessingStep (Cutting / Crease / Perforating / "
                    "KissCut / FoldLine / etc.). Without decomposition the "
                    "converter has to eyeball the artwork to route each "
                    "operation to the right finishing tool."
                ),
                details={
                    "generic_dieline_spot": generic_orig,
                    "iso_19593_steps_found": [],
                    "spec": "ISO 19593-1:2018 Annex A.4",
                },
                category="dieline",
                object_type="document",
                iso_clause="ISO 19593-1:2018 Annex A.4",
            )
        ]
