# T2-RB03 — White text below minimum size combo — DONE

Covered by `LPDF_TEXT_REVERSE_THIN` (T2-RB02 implementation,
Batch 10a). The check fires when text is white **and** rendering
mode is fill-only **and** effective size < 12pt — exactly the
"combo" T2-RB03 calls out. Promoted partial → present; no new
code required.

Files:
- `packages/engine/src/lintpdf/analyzers/hairline.py`
  (`LPDF_TEXT_REVERSE_THIN` — Batch 10a).
