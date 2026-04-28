"""Spot-name canonical-taxonomy normaliser (T3-D11).

Maps common spot-name variants to a small public taxonomy so tenants
get a clear "use 'CutContour' instead of 'Cut Line'" advisory when
their naming drifts from the cross-vendor standards (Esko, PackZ,
ArtiosCAD all recognise the canonical names).

Emits ``LPDF_SPOT_NONCANONICAL`` (advisory) per non-canonical spot
name discovered in any Separation / DeviceN colour space on any
page.

The full taxonomy lives at audit/phase-2/T3-D11/spot-taxonomy.md
for citation; this module is the runtime implementation.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from lintpdf.analyzers.finding import Finding, Severity

logger = logging.getLogger(__name__)

__all__ = [
    "CANONICAL_NAMES",
    "ISO_19593_GROUP_BY_CANONICAL",
    "POSITION_TOKENS",
    "WHITE_SUBTYPE_TOKENS",
    "check_deprecated_pantone_names",
    "check_spot_naming",
    "check_white_subtype_specificity",
    "find_canonical_name",
    "normalise_spot_name",
    "suggest_position_tagging",
    "suggest_processing_steps",
]


#: Map canonical spot category → ISO 19593-1 ProcessingSteps group.
#: Drives the T2-ISO05 ``LPDF_PSTEP_SUGGEST`` advisory.
ISO_19593_GROUP_BY_CANONICAL: dict[str, str] = {
    "CutContour": "Cutting",
    "ThroughCut": "Cutting",
    "KissCut": "KissCutting",
    "Crease": "Folding",
    "Perforation": "Perforating",
    "White": "White",
    "Varnish": "Varnish",
    "VarnishFree": "VarnishFree",
}


#: Tokens that map to ISO 19593-1 "Positions" group — registration,
#: trim marks, colour bars. Drives T2-ISO02 ``LPDF_PSTEP_POSITIONS``.
POSITION_TOKENS: frozenset[str] = frozenset(
    {
        "registration",
        "registration mark",
        "regmark",
        "reg",
        "reg mark",
        "trimmark",
        "trim mark",
        "trim marks",
        "cropmark",
        "crop mark",
        "crop marks",
        "colorbar",
        "color bar",
        "colourbar",
        "colour bar",
        "colorcontrol",
        "colour control",
        "color control",
        "control strip",
        "controlstrip",
        "fogra mediawedge",
        "media wedge",
        "mediawedge",
    }
)


#: Tokens implying the more specific /White subtype the spot belongs
#: to. Maps a hint token → the subtype label suggested by T2-ISO03
#: (``LPDF_PSTEP_WHITE_SUBTYPE``).
WHITE_SUBTYPE_TOKENS: dict[str, str] = {
    "underprint": "WhiteUnderprint",
    "under": "WhiteUnderprint",
    "back": "WhiteUnderprint",
    "overprint": "WhiteOverprint",
    "over": "WhiteOverprint",
    "top": "WhiteOverprint",
    "print": "WhitePrint",
    "spot": "WhitePrint",
    "fill": "WhitePrint",
    "knockout": "WhiteKnockout",
    "ko": "WhiteKnockout",
}


#: Deprecated Pantone naming suffix tokens (T2-SPT03). Pantone retired
#: the CV / CVC / CVU / CVUX suffixes after the move to the current
#: book; remaining usage in modern artwork is a strong signal that the
#: spot was migrated from a legacy library and the tint behaviour may
#: not match the current Pantone target.
_DEPRECATED_PANTONE_SUFFIXES: tuple[str, ...] = (
    " cvc",
    " cv",
    " cvu",
    " cvp",
    " cvux",
)


# Canonical → set of variant tokens (already normalised: lowercase,
# spaces / hyphens / underscores collapsed to single space).
_TAXONOMY: dict[str, frozenset[str]] = {
    "CutContour": frozenset(
        {
            "cutcontour",
            "cut contour",
            "dieline",
            "die line",
            "cutter",
            "cut",
            "cut line",
            "cutline",
            "die cut",
            "die_cut",
            "trim",
            "trim contour",
            "trimcontour",
            "trimmarks",
            "trim marks",
        }
    ),
    "Perforation": frozenset(
        {
            "perforation",
            "perf",
            "perfline",
            "perf line",
            "perforate",
            "perforated",
        }
    ),
    "Crease": frozenset(
        {
            "crease",
            "creaseline",
            "crease line",
            "foldline",
            "fold line",
            "fold",
            "score",
            "scoreline",
            "score line",
        }
    ),
    "KissCut": frozenset(
        {
            "kisscut",
            "kiss cut",
            "kisscutting",
            "kiss cutting",
        }
    ),
    "ThroughCut": frozenset(
        {
            "throughcut",
            "through cut",
            "through-cut",
            "fullcut",
            "full cut",
            "fullthrough",
            "full through",
        }
    ),
    "White": frozenset(
        {
            "white",
            "opaque white",
            "opaquewhite",
            "whiteunder",
            "white under",
            "whiteunderprint",
            "white underprint",
        }
    ),
    "Varnish": frozenset(
        {
            "varnish",
            "uv varnish",
            "uvvarnish",
            "aquacoat",
            "aqua coat",
            "gloss",
            "matte",
            "spotuv",
            "spot uv",
            "softtouch",
            "soft touch",
            "coating",
        }
    ),
    "VarnishFree": frozenset(
        {
            "varnishfree",
            "varnish free",
            "varnish-free",
            "novarnish",
            "no varnish",
            "no-varnish",
            "coatingfree",
            "coating free",
            "nocoating",
            "no coating",
        }
    ),
}

#: Canonical names exposed for callers.
CANONICAL_NAMES: frozenset[str] = frozenset(_TAXONOMY.keys())


def normalise_spot_name(raw: str) -> str:
    """Lowercase + collapse separators for taxonomy lookup."""
    out = raw.strip().lstrip("/").lower()
    out = out.replace("_", " ").replace("-", " ")
    while "  " in out:
        out = out.replace("  ", " ")
    return out.strip()


def find_canonical_name(raw: str) -> str | None:
    """Return the canonical name for ``raw`` or ``None`` when the spot
    isn't in the taxonomy."""
    norm = normalise_spot_name(raw)
    if not norm:
        return None
    # Already canonical (case-insensitive)?
    for canonical in CANONICAL_NAMES:
        if norm == canonical.lower():
            return canonical
    for canonical, tokens in _TAXONOMY.items():
        if norm in tokens:
            return canonical
    return None


def check_spot_naming(pdf_bytes: bytes) -> list[Finding]:
    """Walk every Separation / DeviceN spot in ``pdf_bytes`` and emit
    one advisory per non-canonical spot name.

    Silent when the PDF can't be opened or has no spots in the
    taxonomy.
    """
    if not pdf_bytes:
        return []

    try:
        spots = _collect_spot_names(pdf_bytes)
    except Exception:
        logger.exception("spot_name_normaliser: collection raised")
        return []

    if not spots:
        return []

    findings: list[Finding] = []
    seen_actual: set[str] = set()
    for actual_name in spots:
        if actual_name in seen_actual:
            continue
        seen_actual.add(actual_name)
        canonical = find_canonical_name(actual_name)
        if canonical is None:
            # Unknown spot — silent, taxonomy is opt-in guidance.
            continue
        # Already canonical (case-sensitive) → silent.
        if actual_name == canonical:
            continue
        findings.append(
            Finding(
                inspection_id="LPDF_SPOT_NONCANONICAL",
                severity=Severity.ADVISORY,
                message=(f"Spot '{actual_name}' uses non-canonical name; consider '{canonical}'"),
                page_num=0,
                details={
                    "actual_name": actual_name,
                    "canonical_name": canonical,
                },
                iso_clause="ISO 19593-1 §5.3 / GWG spot naming",
                object_id=actual_name,
                object_type="spot_color",
            )
        )
    return findings


def suggest_position_tagging(pdf_bytes: bytes) -> list[Finding]:
    """T2-ISO02 — emit one ``LPDF_PSTEP_POSITIONS`` advisory per spot
    whose name matches a registration / trim-mark / colour-bar token.

    These spots belong in the ISO 19593-1 ``Positions`` ProcessingSteps
    group, not as printable inks. When they leak through into the
    rendered output (uncaught Positions content), printers see junk
    on press.
    """
    if not pdf_bytes:
        return []

    try:
        spots = _collect_spot_names(pdf_bytes)
    except Exception:
        logger.exception("suggest_position_tagging: collection raised")
        return []

    findings: list[Finding] = []
    seen: set[str] = set()
    for actual_name in spots:
        if actual_name in seen:
            continue
        seen.add(actual_name)
        norm = normalise_spot_name(actual_name)
        if norm in POSITION_TOKENS or any(tok in norm for tok in POSITION_TOKENS):
            findings.append(
                Finding(
                    inspection_id="LPDF_PSTEP_POSITIONS",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Spot '{actual_name}' looks like a positioning aid; tag it "
                        f"under ISO 19593-1 ProcessingSteps 'Positions' so prepress "
                        f"strips it before plating"
                    ),
                    page_num=0,
                    details={
                        "actual_name": actual_name,
                        "iso_group": "Positions",
                    },
                    iso_clause="ISO 19593-1 §5.4 Positions",
                    object_id=actual_name,
                    object_type="spot_color",
                )
            )
    return findings


def check_white_subtype_specificity(pdf_bytes: bytes) -> list[Finding]:
    """T2-ISO03 — when a White spot exists with a hint token in the
    name (Underprint / Overprint / Print / Knockout), emit
    ``LPDF_PSTEP_WHITE_SUBTYPE`` suggesting the specific ISO 19593-1
    White subtype.

    Helps printers identify which physical white pass is needed
    (under, over, knockout) without manual review.
    """
    if not pdf_bytes:
        return []

    try:
        spots = _collect_spot_names(pdf_bytes)
    except Exception:
        logger.exception("check_white_subtype_specificity: collection raised")
        return []

    findings: list[Finding] = []
    seen: set[str] = set()
    for actual_name in spots:
        if actual_name in seen:
            continue
        seen.add(actual_name)
        canonical = find_canonical_name(actual_name)
        if canonical != "White":
            continue
        norm = normalise_spot_name(actual_name)
        for hint, subtype in WHITE_SUBTYPE_TOKENS.items():
            if hint in norm:
                findings.append(
                    Finding(
                        inspection_id="LPDF_PSTEP_WHITE_SUBTYPE",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Spot '{actual_name}' should be tagged with the more "
                            f"specific ISO 19593-1 White subtype '{subtype}'"
                        ),
                        page_num=0,
                        details={
                            "actual_name": actual_name,
                            "suggested_subtype": subtype,
                        },
                        iso_clause="ISO 19593-1 §5.3 White subtypes",
                        object_id=actual_name,
                        object_type="spot_color",
                    )
                )
                break
    return findings


def check_deprecated_pantone_names(pdf_bytes: bytes) -> list[Finding]:
    """T2-SPT03 — emit ``LPDF_SPOT_DEPRECATED_PANTONE`` for any spot
    whose name carries one of the legacy Pantone suffixes (CV, CVC,
    CVU, CVP, CVUX).

    The current Pantone book uses simple letter codes (C, U) and
    leftover CV* names usually mean the artwork was migrated from a
    pre-2008 library and the spot's tint behaviour may no longer
    match the printed Pantone target.
    """
    if not pdf_bytes:
        return []

    try:
        spots = _collect_spot_names(pdf_bytes)
    except Exception:
        logger.exception("check_deprecated_pantone_names: collection raised")
        return []

    findings: list[Finding] = []
    seen: set[str] = set()
    for actual_name in spots:
        if actual_name in seen:
            continue
        seen.add(actual_name)
        norm = normalise_spot_name(actual_name)
        # Strip leading "pms"/"pantone " for simpler suffix matching.
        cleaned = norm
        for prefix in ("pantone ", "pms "):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :]
                break
        for suffix in _DEPRECATED_PANTONE_SUFFIXES:
            if cleaned.endswith(suffix):
                findings.append(
                    Finding(
                        inspection_id="LPDF_SPOT_DEPRECATED_PANTONE",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Spot '{actual_name}' uses deprecated Pantone suffix "
                            f"'{suffix.strip().upper()}'; the current book uses simple "
                            f"'C' / 'U' codes"
                        ),
                        page_num=0,
                        details={
                            "actual_name": actual_name,
                            "deprecated_suffix": suffix.strip().upper(),
                        },
                        iso_clause="Pantone book migration (2008-)",
                        object_id=actual_name,
                        object_type="spot_color",
                    )
                )
                break
    return findings


def suggest_processing_steps(pdf_bytes: bytes) -> list[Finding]:
    """T2-ISO05 — emit one ``LPDF_PSTEP_SUGGEST`` advisory per spot
    whose canonical category maps to a known ISO 19593-1 group.

    Suggests the appropriate ``/ProcessingSteps /Group`` entry so
    finishing equipment recognises cut/crease/perforation/varnish
    inks as production processes rather than print-able colour.

    Silent when the PDF has no spots in the taxonomy or when none
    of the discovered spots map to an ISO 19593-1 group.
    """
    if not pdf_bytes:
        return []

    try:
        spots = _collect_spot_names(pdf_bytes)
    except Exception:
        logger.exception("suggest_processing_steps: collection raised")
        return []

    if not spots:
        return []

    findings: list[Finding] = []
    seen: set[str] = set()
    for actual_name in spots:
        if actual_name in seen:
            continue
        seen.add(actual_name)
        canonical = find_canonical_name(actual_name)
        if canonical is None:
            continue
        iso_group = ISO_19593_GROUP_BY_CANONICAL.get(canonical)
        if iso_group is None:
            continue
        findings.append(
            Finding(
                inspection_id="LPDF_PSTEP_SUGGEST",
                severity=Severity.ADVISORY,
                message=(
                    f"Spot '{actual_name}' should be tagged ISO 19593-1 "
                    f"ProcessingSteps group '{iso_group}'"
                ),
                page_num=0,
                details={
                    "actual_name": actual_name,
                    "canonical_name": canonical,
                    "iso_group": iso_group,
                },
                iso_clause="ISO 19593-1 §5.3",
                object_id=actual_name,
                object_type="spot_color",
            )
        )
    return findings


def _collect_spot_names(pdf_bytes: bytes) -> list[str]:
    """Walk pikepdf's Separation / DeviceN colour-spaces and return
    every spot colourant name discovered."""
    import io

    import pikepdf

    names: list[str] = []
    seen: set[int] = set()

    def walk(obj: Any, depth: int) -> None:
        if depth > 12:
            return
        try:
            obj_id = id(obj)
        except Exception:
            obj_id = 0
        if obj_id in seen:
            return
        seen.add(obj_id)

        # Separation / DeviceN colour-space arrays:
        #   [/Separation /Name /Alternate <tintXform>]
        #   [/DeviceN [/N1 /N2 ...] /Alternate <tintXform>]
        if isinstance(obj, (list, pikepdf.Array)):
            try:
                if len(obj) >= 2:
                    first = str(obj[0]).lstrip("/")
                    if first == "Separation":
                        try:
                            spot = str(obj[1]).lstrip("/")
                            if spot and spot not in ("All", "None"):
                                names.append(spot)
                        except Exception:
                            pass
                    elif first == "DeviceN":
                        try:
                            comp_array = obj[1]
                            for comp in iter(comp_array):
                                spot = str(comp).lstrip("/")
                                if spot and spot not in ("All", "None"):
                                    names.append(spot)
                        except Exception:
                            pass
            except Exception:
                pass

            for item in iter(obj):
                walk(item, depth + 1)
        elif isinstance(obj, (pikepdf.Dictionary, pikepdf.Stream)) or (
            hasattr(obj, "items") and not isinstance(obj, (list, str, bytes))
        ):
            try:
                for v in obj.values():
                    walk(v, depth + 1)
            except Exception:
                pass

    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        # Walk each page's resource graph.
        for page in pdf.pages:
            try:
                resources = page.obj.get("/Resources")
                if resources is not None:
                    walk(resources, 0)
            except Exception:
                continue
        # Also walk the catalog for global spot defs.
        with contextlib.suppress(Exception):
            walk(pdf.Root, 0)

    # Dedupe preserving first-seen order.
    out: list[str] = []
    seen_str: set[str] = set()
    for n in names:
        if n in seen_str:
            continue
        seen_str.add(n)
        out.append(n)
    return out
