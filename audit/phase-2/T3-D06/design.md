# T3-D06 — Barcode quiet zone vs dieline / fold / crease

## What the check detects

Flags PDFs where an image XObject (likely a barcode) sits closer than
the configured quiet zone to a dieline / fold / crease line. The
finished product can have the cut blade or fold crease pass through
the barcode's quiet zone, breaking scanability.

New inspection_id: `LPDF_BARCODE_QUIET_ZONE`. Severity **advisory**.

## Scope simplification

The playbook lists T3-D06 as **hard** with the full implementation
requiring per-barcode 1D/2D classification + module-size measurement
+ exact quiet-zone math (4 modules for 2D, 10x X-dim for 1D). This
batch ships a simpler **proximity-based** version: any image XObject
within `barcode_quiet_zone_mm` of a dieline / crease stroke triggers
the advisory.

False-positive risk: images that aren't barcodes (logos, photos)
near a cut line will fire. Severity = advisory keeps the noise
acceptable; tenants can drop the false-positives via the rules
editor or set the threshold to 0.

A future commit can refine this with the existing
`LPDF_BARCODE_014` finder pattern (already detects 2D barcode
candidates with module counts) once that analyzer's bboxes are
exposed in a shareable form.

## Preconditions

- A dieline or crease line is detected in the content stream
  (either dieline-named spot OR crease-named spot stroked).
- At least one image XObject is placed on page 1.

## Detection

Reuses `dieline_quality._walk_page_one()`:

1. Track `dieline_line_bboxes` and `crease_line_bboxes` separately —
   stroke bboxes painted with dieline / crease spot colours.
2. Track `image_bboxes` from `Do` operator paint events on page 1.
3. After the walk: for each image bbox, compute the minimum distance
   to any dieline / crease line bbox. If distance <
   `barcode_quiet_zone_mm` (default 2.5mm — matches
   `barcode_quiet_zone_mm` in existing thresholds), flag.

## Output

```
Finding(
    inspection_id="LPDF_BARCODE_QUIET_ZONE",
    severity=Severity.ADVISORY,
    message="2 image(s) within 2.5mm of a fold / cut line — verify barcode quiet zones",
    details={
        "image_count": 2,
        "quiet_zone_mm": 2.5,
        "min_distance_mm": 1.2,
        "worst_image_bbox_pts": [...],
    },
)
```

## Read-only / profile

Confirmed read-only. Universal advisory.

## Q&A gate

No open questions.
