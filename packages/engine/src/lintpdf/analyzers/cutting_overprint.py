"""CuttingOverprintAnalyzer — cutting / die-line spots without overprint.

PR-Y (audit miss closure): ISO 19593-1 §6.3 requires that
ProcessingStep inks (cutting, creasing, perforating, scoring) be set
to overprint so they print on top of live artwork without knocking it
out. Artwork where a ``/Cutting`` Separation is used **without** the
``OP`` / ``op`` flag in the active graphics state will produce a
white-outline artifact at press because the spot knocks out the live
plates underneath.

The 2026-04-28 Opus audit caught roughly four dieline misses where
a cutting / crease spot was painted with default (non-overprinting)
graphics state. The existing :class:`OverprintAnalyzer` tracks state
generically (white overprint, RGB overprint, etc.) but doesn't gate
on cutting-spot semantics.

Check ID:
    LPDF_DIE_CUTTING_NOT_OVERPRINT — Cutting / die-line spot used
        without overprint set. Severity: WARNING. Per-spot dedupe so
        a multi-page artwork emits one finding per offending spot,
        not one per glyph / stroke.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.dieline import _name_matches as _is_dieline_name
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


class CuttingOverprintAnalyzer(BaseAnalyzer):
    """Detect ISO 19593 cutting / dieline spots used without overprint."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        from lintpdf.semantic.events import (
            ColorChangedEvent,
            OverprintChangedEvent,
            PathPaintingEvent,
        )

        # 1. Collect the resource-name → colorant-name mapping for any
        #    Separation / DeviceN color space whose colorant matches
        #    a dieline / cutting / crease token. Only those resource
        #    names are interesting; everything else is skipped.
        cutting_resource_names: dict[str, str] = {}  # resource_name -> display colorant
        cutting_colorants: set[str] = set()
        for page in document.pages:
            for cs_name, cs in (getattr(page, "color_spaces", None) or {}).items():
                if getattr(cs, "cs_type", None) not in ("Separation", "DeviceN", "NChannel"):
                    continue
                colorant_names = getattr(cs, "colorant_names", None) or ()
                for colorant in colorant_names:
                    if not colorant or colorant in ("All", "None"):
                        continue
                    if not _is_dieline_name(str(colorant)):
                        continue
                    cutting_resource_names[str(cs_name)] = str(colorant)
                    cutting_colorants.add(str(colorant))
                    break  # first cutting colorant per cs is enough

        if not cutting_resource_names:
            return []

        # 2. Walk the event stream tracking overprint state + the most
        #    recent stroke / non-stroke color space. When a paint
        #    event fires while the current color is a cutting spot,
        #    record whether OP was set at that moment.
        overprint_stroking = False
        overprint_non_stroking = False
        # Resource name of the most recent stroking / non-stroking color.
        cur_stroke_cs: str = ""
        cur_fill_cs: str = ""

        # Map colorant -> dict tracking the worst-case observation:
        # "overprinted_at_least_once" + a representative offending page.
        seen_with_overprint: set[str] = set()
        # First sighting of the colorant being painted without OP.
        first_offending: dict[str, tuple[int, str]] = {}  # colorant -> (page_num, source)

        for event in events:
            if isinstance(event, OverprintChangedEvent):
                if event.overprint_stroking is not None:
                    overprint_stroking = bool(event.overprint_stroking)
                if event.overprint_non_stroking is not None:
                    overprint_non_stroking = bool(event.overprint_non_stroking)
                continue
            if isinstance(event, ColorChangedEvent):
                if event.stroking:
                    cur_stroke_cs = event.color_space
                else:
                    cur_fill_cs = event.color_space
                continue
            if isinstance(event, PathPaintingEvent):
                if event.stroke:
                    cs_name = event.stroke_color_space or cur_stroke_cs
                    colorant = cutting_resource_names.get(cs_name)
                    if colorant:
                        if overprint_stroking:
                            seen_with_overprint.add(colorant)
                        else:
                            first_offending.setdefault(colorant, (event.page_num, "stroke"))
                if event.fill:
                    cs_name = event.fill_color_space or cur_fill_cs
                    colorant = cutting_resource_names.get(cs_name)
                    if colorant:
                        if overprint_non_stroking:
                            seen_with_overprint.add(colorant)
                        else:
                            first_offending.setdefault(colorant, (event.page_num, "fill"))
                continue

        # 3. Emit one finding per cutting spot that was painted
        #    without overprint anywhere in the stream AND was never
        #    observed with overprint set (so the operator gets one
        #    clear signal per offending spot).
        findings: list[Finding] = []
        for colorant, (page_num, source) in sorted(first_offending.items()):
            if colorant in seen_with_overprint:
                continue
            findings.append(
                Finding(
                    inspection_id="LPDF_DIE_CUTTING_NOT_OVERPRINT",
                    severity=Severity.WARNING,
                    message=(
                        f"Cutting / dieline spot '{colorant}' is painted on page "
                        f"{page_num} ({source}) without the overprint flag set. "
                        "ISO 19593-1 §6.3 requires ProcessingStep inks (cutting, "
                        "creasing, perforating) to overprint so the dieline "
                        "doesn't knock out live artwork on the press plates. "
                        "Set OP/op true in the graphics state for any path "
                        "stroked or filled in this spot."
                    ),
                    page_num=page_num,
                    details={
                        "colorant_name": colorant,
                        "first_offending_page": page_num,
                        "operation": source,
                    },
                    category="dieline",
                    object_type="color_space",
                    iso_clause="ISO 19593-1:2018 §6.3",
                )
            )
        return findings
