# T3-D02 — Dieline z-order on top

## What the check detects

Flags PDFs where the dieline is painted BEFORE non-dieline content in
the content stream. PDF rendering is painter's-algorithm — later
operators paint over earlier ones — so a dieline drawn first gets
visually covered by the artwork that follows. The cutter preview shows
the cut line underneath the artwork, which looks wrong to reviewers
and breaks the "dieline on top" convention used by every major
prepress tool (Esko, PackZ, ArtiosCAD).

New inspection_id: `LPDF_DIE_ZORDER`. Severity **warning**.

## Input / preconditions

- `DielineResult.spot_name` is populated (source in `{"name", "vision"}`).
  When `source="missing"`, the check is silent.
- `pdf_bytes` — re-open for content-stream walk.

## Detection

Walk the page-1 content stream operator sequence:

1. Maintain two running operator-index counters:
   - `last_dieline_paint_idx` — last `S`/`s`/`B`/`b`/`f`/`F` operator
     that ran under the dieline's stroke / fill spot.
   - `last_nondieline_paint_idx` — last paint operator under any
     other colour.
2. After the walk: if `last_dieline_paint_idx < last_nondieline_paint_idx`,
   the dieline was drawn first and something painted on top of it.
   Emit the finding.

Only page 1 is scanned (the dieline lives on one page by convention).

## Output

```
Finding(
    inspection_id="LPDF_DIE_ZORDER",
    severity=Severity.WARNING,
    message="Dieline 'CutContour' is drawn below artwork (operator N before M) — move the dieline layer to the top of the stack",
    page_num=1,
    details={
        "spot_name": "CutContour",
        "last_dieline_paint_idx": N,
        "last_nondieline_paint_idx": M,
    },
    iso_clause="ISO 19593-1 §5.3 (Processing Step ordering)",
)
```

## Remediation guidance

> Move the dieline layer (`{spot_name}`) to the top of the layer stack
> in Illustrator / InDesign before exporting. The cutter marker must
> sit above artwork so the prepress operator can verify cut placement.

## Read-only

Confirmed. Content-stream walk reads operator + operand tuples via
pikepdf's `parse_content_stream` (already used by the detector).
Never writes back.

## Profiles

Added to every bundled profile via the default `enabled: ["LPDF_*"]`
pattern. No profile should tolerate out-of-order dielines; packaging /
flexo / gravure workflows all share this convention.

## Edge cases

1. **No dieline detected** → silent (precondition).
2. **Dieline is the only content** → `last_nondieline_paint_idx == -1`;
   silent (nothing for it to be under).
3. **Dieline never painted** → `last_dieline_paint_idx == -1`; silent.
4. **Form XObject contains the dieline** → follow-up work. The
   content stream walker today doesn't recurse into `Do` invocations
   of Form XObjects; this check will false-negative on nested forms.
   Documented as a known limitation.

## Q&A gate

No open questions. Greenlight for implementation.
