"""ColorInventoryAuditAnalyzer — five color-inventory checks added by
PR-K (audit miss closure).

Closes 4 of 5 color category misses surfaced by the post-merge Opus
4.7 audit:

* ``LPDF_COLOR_PLATE_COUNT_HIGH`` — total ink channels (process +
  spots, excluding ProcessingStep technical inks) exceeds typical
  press station counts (>6). Advisory — many flexo / stick-pack
  presses cap out at 6 stations and excess spots will be converted
  to process at the printer.
* ``LPDF_COLOR_DUPLICATE_K_SPOT`` — spot color whose name contains
  "black" as a token (e.g. ``/Black Black``, ``/Rich Black``,
  ``/Process Black``) alongside process K. Likely a duplicate of
  the K plate that will image twice or create an unintended extra
  plate. Advisory.
* ``LPDF_COLOR_DIELINE_PRINTABLE`` — generic dieline spot
  (``/Dieline``, ``/CutContour``, ``/Cut``) exists with no ISO
  19593-1 ProcessingStep companion and no clear technical-ink
  hint. The spot is a regular Separation that will print on the
  live plate unless explicitly set to non-printing in the press
  workflow. Advisory.
* ``LPDF_COLOR_DEVICEN_CMYK_NAMED`` — a DeviceN / NChannel tuple
  names process CMYK channels (``/Cyan``, ``/Magenta``, ``/Yellow``,
  ``/Black``) as colorants. Combined with stand-alone process plates
  the file frequently produces extra unintended separations on the
  RIP. Warning.

The 5th miss (HSI_OUTLINED — pictorial elements rendered without
CMYK process inks) needs image-classification beyond the structural
inventory and is deferred to PR-K-followup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


_PROCESS_CHANNEL_TOKENS: frozenset[str] = frozenset(
    {
        "cyan",
        "magenta",
        "yellow",
        "black",
        "process_cyan",
        "process_magenta",
        "process_yellow",
        "process_black",
    }
)

_DIELINE_TOKENS: frozenset[str] = frozenset(
    {"dieline", "die_line", "cutcontour", "cut_contour", "cut", "trim", "diecut", "die_cut"}
)

_ISO_19593_PROCESSING_STEP_TOKENS: frozenset[str] = frozenset(
    {
        "cutting",
        "perforating",
        "creasing",
        "crease",
        "kiss_cut",
        "kisscut",
        "score",
        "scoring",
        "foldline",
        "fold_line",
        "perfline",
        "perf_line",
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

# When a press has more than this many ink channels, advise.
_HIGH_PLATE_COUNT_THRESHOLD = 6


def _normalise(raw: str | None) -> str | None:
    if not raw:
        return None
    out = raw.strip().strip("/").lower().replace("-", "_").replace(" ", "_")
    return out or None


def _name_tokens(raw: str | None) -> list[str]:
    """Split a normalised colorant name into tokens on underscores."""
    norm = _normalise(raw)
    if not norm:
        return []
    return [t for t in norm.split("_") if t]


class ColorInventoryAuditAnalyzer(BaseAnalyzer):
    """Audit the document's color/ink inventory for PR-K patterns."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        spot_colorants = self._collect_spot_colorants(document)
        process_used = self._process_channels_in_use(document)
        devicen_named_cmyk = self._devicen_with_named_cmyk(document)

        findings: list[Finding] = []
        findings.extend(self._check_plate_count(spot_colorants, process_used))
        findings.extend(self._check_duplicate_k_spot(spot_colorants, process_used))
        findings.extend(self._check_dieline_printable(spot_colorants))
        findings.extend(self._check_devicen_named_cmyk(devicen_named_cmyk))
        return findings

    # ── Inventory helpers ──────────────────────────────────────────

    @staticmethod
    def _collect_spot_colorants(document: SemanticDocument) -> list[str]:
        """All Separation / DeviceN / NChannel colorant names, deduped
        (preserving original case for the first occurrence)."""
        seen: dict[str, str] = {}
        for page in document.pages:
            for cs in (page.color_spaces or {}).values():
                if getattr(cs, "cs_type", None) not in ("Separation", "DeviceN", "NChannel"):
                    continue
                for colorant in getattr(cs, "colorant_names", None) or ():
                    norm = _normalise(colorant)
                    if norm and norm not in seen:
                        seen[norm] = colorant
        return list(seen.values())

    @staticmethod
    def _process_channels_in_use(document: SemanticDocument) -> set[str]:
        """Process channels declared via DeviceCMYK / DeviceGray / ICCBased.
        Returns ``{"cmyk"}`` or ``{"gray"}`` etc. — coarse-grained.

        We always assume the four CMYK plates are in play if the doc
        declares any CMYK-class color space; that's how preflight
        houses count plate stations.
        """
        out: set[str] = set()
        for page in document.pages:
            for cs in (page.color_spaces or {}).values():
                cs_type = getattr(cs, "cs_type", None)
                if cs_type in ("DeviceCMYK", "ICCBased"):
                    out.add("cmyk")
                elif cs_type == "DeviceGray":
                    out.add("k")
        # K-only docs still ship a Black plate.
        if not out:
            out.add("k")
        return out

    @staticmethod
    def _devicen_with_named_cmyk(document: SemanticDocument) -> list[str]:
        """Return ``[colorspace_name, ...]`` for every DeviceN/NChannel
        whose colorant tuple names CMYK channels (``/Cyan`` etc.) as
        colorants — they shouldn't be there; CMYK belongs in the
        process plates."""
        hits: list[str] = []
        for page in document.pages:
            for cs_name, cs in (page.color_spaces or {}).items():
                if getattr(cs, "cs_type", None) not in ("DeviceN", "NChannel"):
                    continue
                colorants = getattr(cs, "colorant_names", None) or ()
                norm_set = {_normalise(c) for c in colorants if c}
                # Process-CMYK token in the tuple → flag.
                if any(t in _PROCESS_CHANNEL_TOKENS for t in norm_set if t):
                    hits.append(cs_name or "(unnamed)")
                    break  # one finding per page
        return hits

    # ── Individual checks ──────────────────────────────────────────

    @staticmethod
    def _check_plate_count(spots: list[str], process_used: set[str]) -> list[Finding]:
        # Spots that are NOT ProcessingStep technical inks count
        # toward press stations.
        plate_spots = [
            s
            for s in spots
            if (_normalise(s) or "") not in _ISO_19593_PROCESSING_STEP_TOKENS
            and (_normalise(s) or "") not in _DIELINE_TOKENS
        ]
        process_count = 4 if "cmyk" in process_used else (1 if "k" in process_used else 0)
        # If only K-process and the artwork says so, count K only.
        if "cmyk" not in process_used:
            total = process_count + len(plate_spots)
        else:
            total = process_count + len(plate_spots)
        if total <= _HIGH_PLATE_COUNT_THRESHOLD:
            return []
        return [
            Finding(
                inspection_id="LPDF_COLOR_PLATE_COUNT_HIGH",
                severity=Severity.ADVISORY,
                message=(
                    f"Document declares {total} ink channels "
                    f"({process_count} process + {len(plate_spots)} spot "
                    "non-ProcessingStep separations). Many flexo / "
                    "stick-pack / label presses cap out at 6 ink "
                    "stations; excess spots may be converted to "
                    "process at the printer. Confirm the press supports "
                    "all declared plates or convert lower-priority "
                    "spots to CMYK before release."
                ),
                details={
                    "total_plates": total,
                    "process_plates": process_count,
                    "spot_plates": len(plate_spots),
                    "spot_names": plate_spots,
                    "threshold": _HIGH_PLATE_COUNT_THRESHOLD,
                },
                category="color",
                object_type="document",
            )
        ]

    @staticmethod
    def _check_duplicate_k_spot(spots: list[str], process_used: set[str]) -> list[Finding]:
        # Process K is in play whenever any process color space exists.
        if "cmyk" not in process_used and "k" not in process_used:
            return []
        out: list[Finding] = []
        for spot in spots:
            tokens = _name_tokens(spot)
            if "black" not in tokens:
                continue
            # Skip the literal `/Black` Separation — that's covered
            # by the existing DuplicateProcessSpotAnalyzer.
            if tokens == ["black"]:
                continue
            out.append(
                Finding(
                    inspection_id="LPDF_COLOR_DUPLICATE_K_SPOT",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Spot color '{spot}' contains 'black' in its name "
                        "and is declared alongside process K. This may "
                        "produce a duplicate plate at output (double-"
                        "printed K) or an unintended extra plate. Verify "
                        "intent: rename the spot if it's a special, or "
                        "merge with process K."
                    ),
                    details={
                        "spot_name": spot,
                    },
                    category="color",
                    object_type="document",
                )
            )
        return out

    @staticmethod
    def _check_dieline_printable(spots: list[str]) -> list[Finding]:
        """When a generic dieline spot exists alongside no ISO 19593
        ProcessingStep, advise the user the dieline may print."""
        norm_set = {(_normalise(s) or "") for s in spots}
        dieline_spots = [s for s in spots if (_normalise(s) or "") in _DIELINE_TOKENS]
        if not dieline_spots:
            return []
        # If there's any ProcessingStep companion, the dieline is
        # almost certainly being routed to a finishing tool.
        if norm_set & _ISO_19593_PROCESSING_STEP_TOKENS:
            return []
        return [
            Finding(
                inspection_id="LPDF_COLOR_DIELINE_PRINTABLE",
                severity=Severity.ADVISORY,
                message=(
                    f"Generic dieline spot '{dieline_spots[0]}' is declared "
                    "as a regular Separation with no ISO 19593-1 "
                    "ProcessingStep companion. The spot will print on the "
                    "live plate unless explicitly set to non-printing in "
                    "the press workflow. Tag it as ProcessingStep / "
                    "Cutting (or similar) so the converter routes it to "
                    "a finishing tool instead of imaging it."
                ),
                details={
                    "dieline_spots": dieline_spots,
                },
                category="color",
                object_type="document",
            )
        ]

    @staticmethod
    def _check_devicen_named_cmyk(devicen_hits: list[str]) -> list[Finding]:
        if not devicen_hits:
            return []
        return [
            Finding(
                inspection_id="LPDF_COLOR_DEVICEN_CMYK_NAMED",
                severity=Severity.WARNING,
                message=(
                    f"DeviceN/NChannel color space '{devicen_hits[0]}' "
                    "names process CMYK channels (e.g. /Cyan, /Magenta, "
                    "/Yellow, /Black) as colorants. Process plates "
                    "should not appear inside DeviceN tuples — combined "
                    "with stand-alone Separations this commonly produces "
                    "extra unintended plates on the RIP. Re-target the "
                    "artwork onto DeviceCMYK or remove the process names "
                    "from the DeviceN tuple."
                ),
                details={
                    "devicen_color_spaces": devicen_hits,
                },
                category="color",
                object_type="document",
            )
        ]
