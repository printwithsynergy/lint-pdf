# T3-D11 — Spot-name heuristic normaliser (public table)

## What the check detects

Flags spot colour names that don't match the lintPDF canonical
taxonomy. The taxonomy is a small, opinionated public table that
maps common name variants to canonical spot names per
ISO 19593-1 / GWG conventions. Tenants who follow the canonical
names get cross-vendor compatibility (Esko, PackZ, ArtiosCAD all
recognise the same names); tenants who use idiosyncratic names
("Cut Line", "DIE_CUT", "TrimMarks") get an advisory pointing them
at the canonical equivalent.

New inspection_id: `LPDF_SPOT_NONCANONICAL`. Severity **advisory**.

## Public taxonomy

```
DIELINE      ← Dieline, CutContour, Cutter, Cut, Cut_Line,
               CutLine, DIE_CUT, Trim, TrimContour, TrimMarks
PERFORATION  ← Perforation, Perf, PerfLine, Perforate
CREASE       ← Crease, CreaseLine, FoldLine, Fold, Score, ScoreLine
KISS_CUT     ← KissCut, Kiss_Cut, KissCutting
THROUGH_CUT  ← ThroughCut, Through_Cut, FullCut, FullThrough
WHITE        ← White, Opaque White, OpaqueWhite, WhiteUnder, WhiteUnderprint
VARNISH      ← Varnish, UV Varnish, AquaCoat, Gloss, Matte, SpotUV
VARNISH_FREE ← VarnishFree, NoVarnish, CoatingFree, NoCoating
```

The table ships as `audit/phase-2/T3-D11/spot-taxonomy.md` so it's
discoverable + citeable. lintPDF's recommended canonical names are:
`CutContour`, `Crease`, `Perforation`, `KissCut`, `ThroughCut`,
`White`, `Varnish`, `VarnishFree`.

## Detection

1. Walk every Separation / DeviceN colour space in the PDF.
2. Normalise each spot name (lowercase, strip separators, drop
   prefix `/`).
3. If the normalised name maps to a canonical entry but isn't
   already the canonical name, emit one advisory per spot.
4. If the name is genuinely unknown (not in the table at all),
   silent — the table is opt-in guidance, not a "use only these
   names" mandate.

## Output

```
Finding(
    inspection_id="LPDF_SPOT_NONCANONICAL",
    severity=Severity.ADVISORY,
    message="Spot 'Cut Line' uses non-canonical name; consider 'CutContour'",
    details={
        "actual_name": "Cut Line",
        "canonical_name": "CutContour",
        "category": "DIELINE",
    },
)
```

## Read-only / profile membership

Confirmed read-only. Universal advisory. Follows the existing
dieline-detector spot-walk path (no new content-stream walking).

## Edge cases

1. Already-canonical name → silent.
2. Unknown name not in any category → silent (no recommendation).
3. Multiple spots with the same non-canonical name → one finding
   per unique non-canonical name (deduplicated).

## Q&A gate

No open questions.
