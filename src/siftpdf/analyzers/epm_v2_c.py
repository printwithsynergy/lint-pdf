"""EPM v2 Tier-C analyzer — advisory checks.

Six detection-only analyzers backing the advisory v2 IDs from
:mod:`siftpdf.epm.codes`. Tier-C findings inform the operator without
changing the EPM scorer's verdict — they appear under
``advisories`` on :class:`siftpdf.epm.scoring.EpmVerdict`.

Codes:

* **EPM-C1** ``LPDF_EPM_SPOT_COUNT_REJECT`` — spot color count above
  advisory cap.
* **EPM-C2** ``LPDF_EPM_FEATURE_SIZE_REJECT`` — smallest stroked
  feature below digital-press minimum line weight.
* **EPM-C3** ``LPDF_EPM_MIXED_SPACES_REJECT`` — mixed process color
  spaces in the same job (some pages CMYK, some DeviceN).
* **EPM-C5** ``LPDF_EPM_TRAPPING_REJECT`` — Trapped key absent /
  Unknown / explicitly False.
* **EPM-C6** ``LPDF_EPM_TRIM_BLEED_REJECT`` — trim and bleed boxes
  mis-aligned beyond tolerance.
* **EPM-C7** ``LPDF_EPM_PAGE_GEOM_REJECT`` — per-page geometry varies
  (some pages bleed, others don't).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from siftpdf.analyzers.base import BaseAnalyzer
from siftpdf.analyzers.finding import Finding, Severity
from siftpdf.epm import codes

if TYPE_CHECKING:
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument


_DEFAULT_SPOT_COUNT_ADVISORY = 6
_DEFAULT_MIN_LINE_WEIGHT_PT = 0.35
_DEFAULT_TRIM_BLEED_TOLERANCE_PT = 1.0


class EpmTierCAnalyzer(BaseAnalyzer):
    """Tier-C EPM analyzer — fans out to the six C-tier detectors."""

    def __init__(
        self,
        *,
        spot_count_advisory: int = _DEFAULT_SPOT_COUNT_ADVISORY,
        min_line_weight_pt: float = _DEFAULT_MIN_LINE_WEIGHT_PT,
        trim_bleed_tolerance_pt: float = _DEFAULT_TRIM_BLEED_TOLERANCE_PT,
    ) -> None:
        self._spot_count_advisory = spot_count_advisory
        self._min_line_weight_pt = min_line_weight_pt
        self._trim_bleed_tolerance_pt = trim_bleed_tolerance_pt

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(
            detect_c1_spot_count_high(
                document, advisory_cap=self._spot_count_advisory
            )
        )
        findings.extend(
            detect_c2_feature_below_digital_res(
                events, min_line_weight_pt=self._min_line_weight_pt
            )
        )
        findings.extend(detect_c3_mixed_process_spaces(document))
        findings.extend(detect_c5_trapping_disabled(document))
        findings.extend(
            detect_c6_trim_bleed_misaligned(
                document, tolerance_pt=self._trim_bleed_tolerance_pt
            )
        )
        findings.extend(detect_c7_page_geometry_varies(document))
        return findings


# ---- C1: spot count high (advisory) -----------------------------------


def detect_c1_spot_count_high(
    document: SemanticDocument, *, advisory_cap: int
) -> list[Finding]:
    """Fire EPM-C1 when distinct spot colorant names exceed the advisory
    cap (default 6). Different from B1 which fires on overall process
    color count; C1 is purely about how many separations operators will
    see at proof time.
    """
    spot_names: set[str] = set()
    for page in document.pages:
        for cs in page.color_spaces.values():
            cs_type = (getattr(cs, "cs_type", "") or "").lower()
            if "separation" not in cs_type and "devicen" not in cs_type:
                continue
            for c in getattr(cs, "colorant_names", None) or ():
                if c and c.lower() not in {
                    "cyan",
                    "magenta",
                    "yellow",
                    "black",
                    "all",
                    "none",
                }:
                    spot_names.add(c)

    if len(spot_names) <= advisory_cap:
        return []
    return [
        Finding(
            inspection_id=codes.EPM_SPOT_COUNT_HIGH,
            severity=Severity.ADVISORY,
            message=(
                f"Document uses {len(spot_names)} spot colors "
                f"(advisory cap {advisory_cap}). Confirm EPM workflow "
                "intent."
            ),
            page_num=0,
            category="color",
            details={
                "spot_count": len(spot_names),
                "advisory_cap": advisory_cap,
                "spot_names": sorted(spot_names),
            },
        )
    ]


# ---- C2: feature below digital-press resolution ----------------------


def detect_c2_feature_below_digital_res(
    events: list[ContentStreamEvent], *, min_line_weight_pt: float
) -> list[Finding]:
    """Fire EPM-C2 when a stroked path uses a line width below the
    digital-press minimum (default 0.35pt)."""
    from siftpdf.semantic.events import PathPaintingEvent

    findings: list[Finding] = []
    seen: set[tuple[int, float]] = set()

    for ev in events:
        if not isinstance(ev, PathPaintingEvent) or not ev.stroke:
            continue
        line_width = getattr(ev, "line_width", 0.0) or 0.0
        if line_width <= 0 or line_width >= min_line_weight_pt:
            continue
        key = (ev.page_num, round(line_width, 3))
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                inspection_id=codes.EPM_FEATURE_BELOW_DIGITAL_RES,
                severity=Severity.ADVISORY,
                message=(
                    f"Stroked feature {line_width:.2f}pt is below the "
                    f"digital-press minimum {min_line_weight_pt:.2f}pt."
                ),
                page_num=ev.page_num,
                category="geometry",
                details={
                    "line_width_pt": round(line_width, 3),
                    "min_pt": min_line_weight_pt,
                },
            )
        )
    return findings


# ---- C3: mixed process color spaces -----------------------------------


def detect_c3_mixed_process_spaces(
    document: SemanticDocument,
) -> list[Finding]:
    """Fire EPM-C3 when the document mixes CMYK with DeviceN/Separation
    on different pages (or any heterogeneous mix of process spaces)."""
    page_kinds: dict[int, set[str]] = {}
    for page in document.pages:
        kinds: set[str] = set()
        for cs in page.color_spaces.values():
            cs_type = (getattr(cs, "cs_type", "") or "").lower()
            if "cmyk" in cs_type:
                kinds.add("cmyk")
            elif "rgb" in cs_type:
                kinds.add("rgb")
            elif "gray" in cs_type:
                kinds.add("gray")
            elif "separation" in cs_type:
                kinds.add("separation")
            elif "devicen" in cs_type:
                kinds.add("devicen")
            elif "iccbased" in cs_type:
                kinds.add("icc")
        page_kinds[page.page_num] = kinds

    union: set[str] = set().union(*page_kinds.values()) if page_kinds else set()
    process_kinds = union & {"cmyk", "rgb", "gray", "separation", "devicen"}
    if len(process_kinds) < 2:
        return []
    return [
        Finding(
            inspection_id=codes.EPM_MIXED_PROCESS_SPACES,
            severity=Severity.ADVISORY,
            message=(
                f"Document mixes process color spaces ({sorted(process_kinds)}). "
                "Confirm separation setup."
            ),
            page_num=0,
            category="color",
            details={"kinds": sorted(process_kinds)},
        )
    ]


# ---- C5: trapping disabled / unknown ---------------------------------


def detect_c5_trapping_disabled(document: SemanticDocument) -> list[Finding]:
    """Fire EPM-C5 when the document's /Trapped key is missing,
    Unknown, or explicitly False. Digital presses still benefit from
    explicit traps on tight register, so this is an advisory cue."""
    info = getattr(document, "info_dict", None) or {}
    trapped = info.get("/Trapped") or info.get("Trapped")
    trapped_str = str(trapped or "").strip().lower()
    if trapped_str in {"true", "yes", "/true"}:
        return []
    return [
        Finding(
            inspection_id=codes.EPM_TRAPPING_DISABLED,
            severity=Severity.ADVISORY,
            message=(
                "Trapping is " + (trapped_str or "missing")
                + " — explicit traps recommended for tight register."
            ),
            page_num=0,
            category="color",
            details={"trapped": trapped_str or "missing"},
        )
    ]


# ---- C6: trim/bleed mis-aligned --------------------------------------


def detect_c6_trim_bleed_misaligned(
    document: SemanticDocument, *, tolerance_pt: float
) -> list[Finding]:
    """Fire EPM-C6 when the trim box on any page is mis-centred inside
    the bleed box beyond ``tolerance_pt`` (i.e. unequal margins on
    opposing sides)."""
    findings: list[Finding] = []

    for page in document.pages:
        bleed = page.bleed_box or page.media_box
        trim = page.trim_box or page.crop_box or page.media_box
        left = trim.x0 - bleed.x0
        right = bleed.x1 - trim.x1
        bottom = trim.y0 - bleed.y0
        top = bleed.y1 - trim.y1
        h_skew = abs(left - right)
        v_skew = abs(top - bottom)
        if h_skew <= tolerance_pt and v_skew <= tolerance_pt:
            continue
        findings.append(
            Finding(
                inspection_id=codes.EPM_TRIM_BLEED_MISALIGNED,
                severity=Severity.ADVISORY,
                message=(
                    f"Trim is off-centre inside bleed by H {h_skew:.1f}pt / "
                    f"V {v_skew:.1f}pt (tolerance {tolerance_pt:.1f}pt)."
                ),
                page_num=page.page_num,
                category="geometry",
                details={
                    "left_pt": round(left, 2),
                    "right_pt": round(right, 2),
                    "top_pt": round(top, 2),
                    "bottom_pt": round(bottom, 2),
                    "tolerance_pt": tolerance_pt,
                },
            )
        )
    return findings


# ---- C7: page geometry varies ----------------------------------------


def detect_c7_page_geometry_varies(
    document: SemanticDocument,
) -> list[Finding]:
    """Fire EPM-C7 when MediaBox dimensions vary across pages.

    Distinct from B6 (trim/bleed varies). C7 catches mixed-page-size
    documents that EPM would feed through the wrong substrate path.
    """
    if document.page_count < 2:
        return []

    sizes: set[tuple[float, float]] = set()
    for page in document.pages:
        mb = page.media_box
        sizes.add((round(mb.width, 1), round(mb.height, 1)))
    if len(sizes) < 2:
        return []
    return [
        Finding(
            inspection_id=codes.EPM_PAGE_GEOMETRY_VARIES,
            severity=Severity.ADVISORY,
            message=(
                f"Document has {len(sizes)} distinct page sizes — "
                "confirm substrate-feed setup."
            ),
            page_num=0,
            category="geometry",
            details={"distinct_sizes": sorted(sizes)},
        )
    ]


__all__ = [
    "EpmTierCAnalyzer",
    "detect_c1_spot_count_high",
    "detect_c2_feature_below_digital_res",
    "detect_c3_mixed_process_spaces",
    "detect_c5_trapping_disabled",
    "detect_c6_trim_bleed_misaligned",
    "detect_c7_page_geometry_varies",
]
