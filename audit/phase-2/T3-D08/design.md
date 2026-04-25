# T3-D08 — Small vector element won't die-cut cleanly

## What the check detects

Flags dieline path features below the cutting machine's resolution
threshold. Two failure modes:

1. **Short segments**: a straight or curved subpath whose total
   length is shorter than `min_segment_length_mm` (default 1.0mm)
   — the cutter blade can't track features that small without
   tearing the substrate.
2. **Tight corners**: a subpath whose bbox is smaller than
   `min_feature_size_mm` (default 1.0mm × 1.0mm) — the smallest
   die-cut detail that flesh paper / cardstock can hold without
   crumbling. Very small filled regions inside a dieline don't
   come out as discrete cuts; they tear into the surrounding
   stock.

New inspection_id: `LPDF_DIE_TOO_SMALL`. Severity **warning**.

## Preconditions

- `DielineResult.polylines` populated.
- One or more polygons in the polyline list.

## Detection

For each polygon in `DielineResult.polylines`:

1. Compute total perimeter (sum of segment distances between
   consecutive points).
2. Compute bbox (already in `regions`).
3. If perimeter < `min_segment_length_mm` (converted to pt) OR
   width < `min_feature_size_mm` OR height < `min_feature_size_mm`,
   flag the polygon as too-small.

Aggregate into one per-document finding with the count of too-small
polygons + the smallest one's metrics.

## Output

```
Finding(
    inspection_id="LPDF_DIE_TOO_SMALL",
    severity=Severity.WARNING,
    message="3 dieline feature(s) below 1.0mm cutting threshold (smallest: 0.5x0.5mm)",
    details={
        "feature_count": 3,
        "min_feature_size_mm": 1.0,
        "smallest_width_mm": 0.5,
        "smallest_height_mm": 0.5,
        "smallest_perimeter_mm": 1.8,
    },
)
```

## Thresholds

New profile fields:
- `min_dieline_feature_mm: float = 1.0` — minimum width or height
- `min_dieline_segment_length_mm: float = 1.0` — minimum perimeter

Both default-on with sensible 1.0mm thresholds (matches industry
trade norms for cardstock cutting).

## Read-only / profile membership

Confirmed read-only. Bbox math + polygon perimeter calc.

## Edge cases

1. No dieline polygons → silent.
2. Single huge dieline polygon → silent (passes thresholds).
3. Dieline with one valid + one too-small polygon → fires with
   feature_count = 1.
4. Polygon with concave shape — bbox is convex hull; perimeter is
   point-to-point. May over-count perimeter for self-intersecting
   shapes but doesn't false-flag clean shapes.

## Q&A gate

No open questions.
