# T3-D05 — Content outside dieline polygon

## What the check detects

Flags painted content whose bbox extends beyond the union of the
dieline polygons. Distinct from `LPDF_PKG_004` (which uses the trim
box) — this check uses the actual dieline polygon(s) from the
detector's `DielineResult.polylines`, which is tighter than the
trim box on non-rectangular products (curved labels, irregular
die-cut packaging).

New inspection_id: `LPDF_DIE_CONTENT_OUTSIDE`. Severity **warning**.

## Preconditions

- `DielineResult.source` in `{"name", "vision"}` (there's a
  detected dieline).
- `DielineResult.polylines` non-empty.
- `DielineResult.regions` populated (the per-island bbox list).

When `regions` is empty the check silently no-ops — without bbox
data we can't do polygon-containment.

## Detection

The existing `dieline_quality._walk_page_one()` already tracks
subpath bboxes per paint operator. Extend the signal gathering:

1. For each non-dieline paint operator, compute its total bbox
   (union of current subpath bboxes).
2. Compute the dieline bounding envelope — union of every
   `DielineResult.regions` entry. This is an axis-aligned
   approximation of the dieline polygon's bounding shape.
3. If the paint bbox extends beyond the envelope by more than the
   configured tolerance (default 1mm ≈ 2.83pt), flag.
4. Cap at 10 violations per page; summary carries
   `foreign_content_count` for tenants who want the full list.

## Output

```
Finding(
    inspection_id="LPDF_DIE_CONTENT_OUTSIDE",
    severity=Severity.WARNING,
    message="N content region(s) extend beyond the dieline polygon by >1mm on page 1",
    details={
        "foreign_content_count": N,
        "max_overhang_pts": X,
        "dieline_bbox_pts": [x0, y0, x1, y1],
        "worst_paint_bbox_pts": [x0, y0, x1, y1],
    },
)
```

## Scope simplification

True polygon containment (test whether a paint bbox is inside a
potentially-non-convex dieline polygon) would require a
point-in-polygon check per corner. This implementation ships the
**envelope-based** approximation: "is the paint bbox outside the
axis-aligned union of dieline region bboxes?" That catches the
canonical "artwork extends past the label edge" case without the
geometry cost.

Follow-up: full polygon containment for curved / concave dielines
tracked in followups.md.

## Output shape details

`max_overhang_pts` = max distance in points from any paint-bbox edge
to the nearest dieline-envelope edge when outside. Helps tenants
gauge severity at a glance.

## Read-only

Confirmed. Bbox math only; no writes.

## Profile membership

Universal warning across packaging profiles.

## Edge cases

1. Dieline detector missed → silent.
2. Paint bbox fully outside the page mediabox → silent (already
   covered by LPDF_BOX_006 bleed check).
3. Trim marks / cut-mark registration content just outside the
   dieline (< tolerance) → silent within the 1mm default tolerance.
4. Multi-region dieline (circle + rectangle on same page) →
   envelope = union of both bboxes; content between the two
   regions is "outside" and will fire. Tenant option: set
   tolerance = the expected gap when using multi-island layouts.

## Q&A gate

No open questions.
