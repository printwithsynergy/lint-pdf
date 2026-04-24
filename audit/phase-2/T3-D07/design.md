# T3-D07 — Text near fold line

## What the check detects

Flags text bboxes that sit closer than the configured threshold to a
fold / crease line. Text that crosses or hugs a fold gets bent and
becomes hard to read in the finished product (greeting card spine,
brochure crease, packaging fold).

New inspection_id: `LPDF_TEXT_NEAR_FOLD`. Severity **warning**.

## Preconditions

- A fold / crease spot is detected (Crease, FoldLine, ScoreLine,
  Score — see canonical taxonomy from T3-D11).
- The dieline_quality walker has captured fold-line stroke bboxes.

## Detection

Extends the dieline_quality walker:

1. Track `crease_line_bboxes` (separate from dieline bboxes —
   crease ≠ cut).
2. Walk text events (TextRenderedEvent) on page 1, collect text
   bboxes.
3. For each text bbox, compute min distance to any crease line
   bbox.
4. If distance < `text_to_fold_distance_mm` (default 3.0mm), count
   it as too-close.
5. Emit one per-page finding with the count + worst-distance.

## Output

```
Finding(
    inspection_id="LPDF_TEXT_NEAR_FOLD",
    severity=Severity.WARNING,
    message="5 text region(s) within 3.0mm of a fold / crease line — text will be bent at the fold",
    details={
        "text_count": 5,
        "threshold_mm": 3.0,
        "min_distance_mm": 0.8,
        "worst_text_bbox_pts": [...],
    },
)
```

## Configuration

New profile threshold field:
- `text_to_fold_distance_mm: float = 3.0` — minimum clearance from
  fold lines. 0 disables the check.

## Read-only / profile

Confirmed read-only. Universal warning. Disabled when no fold/crease
spot is detected.

## Q&A gate

No open questions.
