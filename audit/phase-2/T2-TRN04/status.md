# T2-TRN04 — Blending CS vs OutputIntent mismatch — DONE

`LPDF_TRANS_BLEND_CS_MISMATCH` (warning) fires when a page's
transparency-group `/CS` differs from the document's OutputIntent
destination colour space. Flatteners may render the page with a
colour shift relative to the printed proof.

Files:
- `packages/engine/src/lintpdf/analyzers/transparency.py` —
  `_check_blend_cs_mismatch()` + `_output_intent_cs()`.
- `packages/engine/tests/analyzers/test_batch10a.py` — 2 cases.
