# T2-TRN06 — Soft mask on text — DONE (Batch 11)

`LPDF_TEXT_SOFT_MASK` (advisory) emits one finding per page where
the page's `/Resources /ExtGState` declares an entry with a non-
trivial `/SMask` AND at least one text event was rendered on that
page. Some RIPs lose legibility on text under a soft mask;
flagging the combination lets the operator review at production
DPI.

Files:
- `packages/engine/src/lintpdf/analyzers/transparency.py` —
  `_check_text_soft_mask()` + `_has_soft_mask_extgstate()`.
- `packages/engine/tests/analyzers/test_batch11.py` — 3 cases.
