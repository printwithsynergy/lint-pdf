"""DuplicateProcessSpotAnalyzer — flags process colors declared as named
Separations (the "Make Spot from CMYK" Illustrator export bug).

When a designer toggles "Make Spot from CMYK" in Illustrator's Swatch
Library or duplicates a process color into a Separation, the resulting
PDF carries an extra plate-per-channel that the press has to image
twice. The 2026-04-27 Opus audit flagged this on multiple Nutrops
fixtures: ``/Cyan`` declared as both a DeviceCMYK process AND a named
Separation — 8 plates instead of 4.

Check ID:
    LPDF_SPOT_DUPE_PROCESS — Process color declared as a named
        Separation/DeviceN colorant. Severity: WARNING.

Goal: catch this before plate-making, prompt the designer to either
re-target the artwork onto the existing process channel or rename
the spot if it really is intended as a special.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from siftpdf.analyzers.base import BaseAnalyzer
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument


# Process channel names. Case-insensitive match after `_normalise()`.
# A spot colorant whose name matches one of these is a duplicate of an
# existing process channel.
_PROCESS_CHANNEL_NAMES: frozenset[str] = frozenset(
    {
        # CMYK + paper white
        "cyan",
        "magenta",
        "yellow",
        "black",
        "white",
        # RGB
        "red",
        "green",
        "blue",
        # Gray
        "gray",
        "grey",
        # Process-prefixed variants Illustrator sometimes writes
        "process_cyan",
        "process_magenta",
        "process_yellow",
        "process_black",
        # Spelt-out CMYK (rare but possible)
        "process_color",
    }
)


def _normalise(raw: str | None) -> str | None:
    """Lowercase + strip + collapse separators so ``"Process Cyan"``,
    ``"process-cyan"``, and ``"Cyan"`` all map sensibly.

    NB: collapses spaces into underscores so ``"Process Cyan"`` →
    ``"process_cyan"`` matches the entry in ``_PROCESS_CHANNEL_NAMES``.
    """
    if not raw:
        return None
    out = raw.strip().strip("/").lower()
    out = out.replace("-", "_").replace(" ", "_")
    return out or None


class DuplicateProcessSpotAnalyzer(BaseAnalyzer):
    """Detect process channels declared as named Separations / DeviceN
    colorants (causes duplicate plates at output)."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[str] = set()  # global dedupe by colorant name

        for page in document.pages:
            for cs in (page.color_spaces or {}).values():
                cs_type = getattr(cs, "cs_type", None)
                if cs_type not in ("Separation", "DeviceN", "NChannel"):
                    continue
                colorants = getattr(cs, "colorant_names", None) or ()
                for colorant in colorants:
                    norm = _normalise(colorant)
                    if not norm or norm not in _PROCESS_CHANNEL_NAMES:
                        continue
                    if norm in seen:
                        continue
                    seen.add(norm)
                    findings.append(
                        Finding(
                            inspection_id="LPDF_SPOT_DUPE_PROCESS",
                            severity=Severity.WARNING,
                            message=(
                                f"Process color '{colorant}' is declared as a "
                                "named Separation / DeviceN colorant. This "
                                "produces a duplicate plate at output (the "
                                "channel is already imaged via process CMYK). "
                                "Convert artwork to DeviceCMYK on the existing "
                                "channel, or rename the spot if it's an "
                                "intentional special."
                            ),
                            details={
                                "colorant": colorant,
                                "color_space_type": cs_type,
                            },
                            category="color",
                            object_type="document",
                        )
                    )
        return findings
