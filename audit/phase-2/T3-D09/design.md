# T3-D09 — White underprint coverage vs dieline

## What the check detects

Flags PDFs where a White underprint spot doesn't cover the dieline
area. On clear-substrate / foil packaging, white ink prints UNDER
the colour artwork to give the colour something opaque to render
against. If white underprint coverage is smaller than the dieline,
colour shows through the substrate gap → wrong product look.

New inspection_id: `LPDF_DIE_WHITE_GAP`. Severity **warning**.

## Preconditions

- A White / WhiteUnder / OpaqueWhite Separation spot is detected
  in the PDF resources.
- A dieline polygon is detected (`DielineResult.regions` populated).

When either is absent, the check silently no-ops — non-flexible-
packaging PDFs (offset on coated paper, no dieline) shouldn't
emit this finding.

## Detection

Reuses the existing `dieline_quality._walk_page_one()` walker:

1. Extend the spot-name matcher with a White-spot recogniser
   (matches "White", "Opaque White", "WhiteUnder",
   "WhiteUnderprint" — same lexical normaliser as varnish).
2. Track white-spot paint bbox(es) on each paint operator.
3. After the walk: compare union of white-spot bboxes to the
   dieline envelope.
4. If white envelope area < `dieline_area * white_coverage_min`
   (default 0.95 = 95%), flag the gap.

## Output

```
Finding(
    inspection_id="LPDF_DIE_WHITE_GAP",
    severity=Severity.WARNING,
    message="White underprint covers 78% of dieline area — gaps will let substrate show through colour artwork",
    details={
        "white_spot": "OpaqueWhite",
        "white_coverage_pct": 78.4,
        "white_coverage_min_pct": 95.0,
        "dieline_area_pts2": 50000,
        "white_area_pts2": 39200,
        "uncovered_bbox_pts": [x0, y0, x1, y1],  # gap region (approx)
    },
)
```

## Configuration

New profile threshold field:
- `white_coverage_min: float = 0.95` — minimum white-spot coverage
  fraction of the dieline area (0-1). Set to 0 to disable. Defaults
  to 95% (lossless registration tolerance built in).

## Read-only / profile membership

Confirmed read-only. Bbox area math.

## Edge cases

1. No white spot → silent.
2. No dieline → silent.
3. White covers > 100% of dieline (white extends past dieline) →
   silent (excess coverage isn't a defect).
4. Multiple non-overlapping white regions inside dieline (e.g.,
   selective underprint) → coverage = sum of white bboxes minus
   overlap. Bbox-union approximation OK for the first cut.

## Q&A gate

No open questions.
