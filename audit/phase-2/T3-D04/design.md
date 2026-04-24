# T3-D04 — Bleed extending beyond dieline by X mm

## What the check detects

Flags artwork that extends MORE than the maximum expected bleed past
the dieline polygon. Complements:

- `LPDF_BOX_003` — insufficient bleed past trim box.
- `LPDF_DIE_CONTENT_OUTSIDE` (T3-D05) — any overhang past the dieline
  envelope (usually small).

T3-D04 fills the "excessive bleed" slot: content overhang that exceeds
the `max_bleed_mm` threshold signals paper waste + possible binding /
imposition issues when the PDF is placed in a multi-up sheet.

New inspection_id: `LPDF_DIE_EXCESSIVE_BLEED`. Severity **advisory**.

## Preconditions

- `DielineResult.regions` populated (needs the dieline envelope).
- `profile.thresholds.max_bleed_mm` set (new threshold field).

## Detection

Reuses `dieline_quality._walk_page_one()` signals. For each
non-dieline paint bbox:

1. Compute `overhang_pts` past the dieline envelope (positive if
   content sticks out).
2. Compare overhang to `max_bleed_mm` (converted to points).
3. Flag the paint bbox as excessive-bleed when `overhang > max_bleed`.

Report the maximum overhang across the page + the count of paint
bboxes that exceed the threshold.

## Output

```
Finding(
    inspection_id="LPDF_DIE_EXCESSIVE_BLEED",
    severity=Severity.ADVISORY,
    message="3 content region(s) extend past the dieline by more than 10.0mm (max overhang 15.3mm)",
    details={
        "excessive_count": 3,
        "max_overhang_mm": 15.3,
        "max_bleed_mm": 10.0,
        "dieline_envelope_pts": [x0, y0, x1, y1],
        "worst_paint_bbox_pts": [x0, y0, x1, y1],
    },
)
```

## Read-only / profile membership

Confirmed read-only. Universal advisory across packaging profiles;
disabled by default when `max_bleed_mm` is absent from the profile.

## Edge cases

1. `max_bleed_mm` not set → check silent (opt-in).
2. No dieline detected → silent (no envelope).
3. Overhang ≤ tolerance → silent (T3-D05 territory).

## Q&A gate

No open questions.
