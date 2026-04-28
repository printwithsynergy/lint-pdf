"""InkExtrasAnalyzer — extras around ink-channel topology that the
existing ``InkCoverageAnalyzer`` (LPDF_INK_001..003) doesn't cover.

The 2026-04-28 audit (run 5) flagged two recurring color-category
misses:

* **Press station overflow** — fixtures 03, 07, 09 all have 6+ active
  ink channels. Six is already the typical wide-web flexo press
  station limit; the engine's existing ``LPDF_INK_003`` only fires
  the WARNING at >7 channels. Operators want the heads-up at the
  flexo limit, not after they've already passed it. We add an
  ADVISORY at >6 to give them that nudge without double-firing the
  existing >7 WARNING.

* **Same colorant duplicated across DeviceN and Separation** —
  fixture 12 (Pink-Slush_OUTLINED) has ``PANTONE 236 C`` and
  ``PANTONE 237 C`` declared **both** as standalone Separation color
  spaces **and** inside a DeviceN colorant tuple. The RIP treats
  them as separate channels at output. End result: 14 ink channels
  reported on a job that should run on ~6 plates, plus surprise
  "duplicate plate" rejections at the prepress stage.

Check IDs:
    LPDF_INK_PRESS_STATIONS — Total ink channels above typical flexo
        press station count (6). Severity: ADVISORY. Doesn't replace
        the existing >7 WARNING in ``LPDF_INK_003`` — both can fire
        on extreme cases (e.g., the 14-channel Pink-Slush file).
    LPDF_INK_DUPLICATE_DEVICEN_SEP — Same colorant appears in both a
        DeviceN/NChannel color space AND a separate Separation color
        space. Severity: WARNING.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# Wide-web flexo presses commonly cap at 6 stations (4 process + 2
# spot, or 6 spots). Web-fed offset / sheet-fed jobs handle more, but
# at six channels every operator wants to verify the press deck.
_FLEXO_STATION_LIMIT = 6

# Names that should not count toward press-station capacity — they're
# technical / non-printing channels that the converter routes off-line
# (cut, perf, fold, varnish, white base, etc.). Lowercase + stripped.
_TECHNICAL_NAMES: frozenset[str] = frozenset(
    {
        "dieline",
        "die_line",
        "die line",
        "cutcontour",
        "cut_contour",
        "cut contour",
        "cutting",
        "perforating",
        "perforation",
        "perf",
        "perfline",
        "perf_line",
        "creasing",
        "crease",
        "kiss_cut",
        "kisscut",
        "kiss cut",
        "foldline",
        "fold_line",
        "fold line",
        "varnish",
        "varnishing",
        "spot_varnish",
        "white_base",
        "whitebase",
        "white base",
        "embossing",
        "deboss",
    }
)


def _norm(name: str | None) -> str:
    if not name:
        return ""
    return name.strip().strip("/").lower().replace("-", "_")


class InkExtrasAnalyzer(BaseAnalyzer):
    """Audit-run-5 ink-topology checks (press capacity + DeviceN/Sep
    duplication)."""

    def __init__(self, station_limit: int = _FLEXO_STATION_LIMIT) -> None:
        self._station_limit = station_limit

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        findings: list[Finding] = []

        process_used: set[str] = set()
        spot_seen: set[str] = set()
        spot_originals: dict[str, str] = {}

        # cs_type set per normalized colorant name, for the duplicate
        # check.
        cs_types_for: dict[str, set[str]] = defaultdict(set)
        # Preserve original casing for the message.
        original_for_dupe: dict[str, str] = {}

        for page in document.pages:
            for cs in (page.color_spaces or {}).values():
                cs_type = getattr(cs, "cs_type", None)
                if cs_type == "DeviceCMYK":
                    process_used |= {"C", "M", "Y", "K"}
                elif cs_type == "DeviceGray":
                    process_used.add("K")
                elif cs_type == "DeviceRGB":
                    process_used |= {"R", "G", "B"}
                elif cs_type in ("Separation", "DeviceN", "NChannel"):
                    for colorant in getattr(cs, "colorant_names", None) or ():
                        norm = _norm(colorant)
                        if not norm or norm in ("all", "none"):
                            continue
                        spot_seen.add(norm)
                        spot_originals.setdefault(norm, colorant)
                        cs_types_for[norm].add(cs_type)
                        original_for_dupe.setdefault(norm, colorant)

        # ── LPDF_INK_PRESS_STATIONS ───────────────────────────────────
        # Total *printable* channels = process channels + non-technical
        # spot colors. We deliberately drop dieline / cut / perf / etc.
        # because those don't take a press station — they're routed to
        # the finishing line.
        printable_spots = {n for n in spot_seen if n not in _TECHNICAL_NAMES}
        total_printable = len(process_used) + len(printable_spots)

        if total_printable > self._station_limit:
            findings.append(
                Finding(
                    inspection_id="LPDF_INK_PRESS_STATIONS",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Document uses {total_printable} printable ink channels "
                        f"({len(process_used)} process + {len(printable_spots)} "
                        f"spot), above the typical wide-web flexo press station "
                        f"limit of {self._station_limit}. Confirm the destination "
                        "press has enough decks, or consolidate spots into "
                        "process builds where colorimetric tolerance allows."
                    ),
                    details={
                        "process_channels": sorted(process_used),
                        "printable_spots": sorted(
                            spot_originals.get(n, n) for n in printable_spots
                        ),
                        "total_printable": total_printable,
                        "station_limit": self._station_limit,
                    },
                    category="color",
                    object_type="document",
                )
            )

        # ── LPDF_INK_DUPLICATE_DEVICEN_SEP ────────────────────────────
        # A name appearing in both a DeviceN/NChannel cs AND a
        # standalone Separation cs is a structural duplicate — the RIP
        # may treat them as separate channels even though the operator
        # meant one ink.
        for norm, types in sorted(cs_types_for.items()):
            if "Separation" not in types:
                continue
            if not (types & {"DeviceN", "NChannel"}):
                continue
            original = original_for_dupe.get(norm, norm)
            findings.append(
                Finding(
                    inspection_id="LPDF_INK_DUPLICATE_DEVICEN_SEP",
                    severity=Severity.WARNING,
                    message=(
                        f"Colorant {original!r} is declared in both a "
                        f"{', '.join(sorted(types))} color space. The RIP "
                        "may treat these as separate plates even though the "
                        "intent is one ink. Consolidate to a single "
                        "Separation declaration (or a single DeviceN tuple) "
                        "before plating to avoid duplicate-plate rejections."
                    ),
                    details={
                        "colorant": original,
                        "cs_types": sorted(types),
                    },
                    category="color",
                    object_type="document",
                )
            )

        return findings
