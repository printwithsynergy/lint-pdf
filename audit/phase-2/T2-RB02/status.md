# T2-RB02 — Reverse text minimum stroke — DONE

`LPDF_TEXT_REVERSE_THIN` (advisory) emitted per page that has
small (effective < 12pt) white text rendered with `rendering_mode=0`
(fill only, no stroke). Recommends adding a ≥0.5pt stroke or
using ≥12pt for legibility on press.

Aggregated alongside the existing `LPDF_TEXT_004` per-page bucket
to keep finding noise low on label artwork with many small
reverse-text instances.

Files:
- `packages/engine/src/lintpdf/analyzers/hairline.py` — extended
  `text004_agg` bucket with `reverse_thin_count` + emit logic.
- `packages/engine/tests/analyzers/test_batch10a.py` — 2 cases.
