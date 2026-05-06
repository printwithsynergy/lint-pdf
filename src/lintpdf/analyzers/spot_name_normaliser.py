"""Spot-name canonical-taxonomy normaliser (T3-D11).

Maps common spot-name variants to a small public taxonomy so tenants
get a clear "use 'CutContour' instead of 'Cut Line'" advisory when
their naming drifts from the cross-vendor standards (Esko, PackZ,
ArtiosCAD all recognise the canonical names).

Emits ``LPDF_SPOT_NONCANONICAL`` (advisory) per non-canonical spot
name discovered in any Separation / DeviceN color space on any
page.

The full taxonomy lives at audit/phase-2/T3-D11/spot-taxonomy.md
for citation; this module is the runtime implementation.
"""

from __future__ import annotations

__all__ = [
    "CANONICAL_NAMES",
    "ISO_19593_GROUP_BY_CANONICAL",
    "POSITION_TOKENS",
    "WHITE_SUBTYPE_TOKENS",
    "find_canonical_name",
    "normalise_spot_name",
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
#: trim marks, color bars. Drives T2-ISO02 ``LPDF_PSTEP_POSITIONS``.
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
        "colorcontrol",
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
