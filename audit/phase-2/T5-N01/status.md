# T5-N01 — PDF/VT structural validation — DONE

`LPDF_PDFVT_STRUCTURE` (warning) fires when the document declares
PDF/VT in its XMP metadata (token `PDF/VT-1` / `-2` / `-3`) but
lacks the structural elements ISO 16612-2 requires — currently
the `/Catalog /DPartRoot` reference. Silent on documents that
don't declare PDF/VT.

PDF/X-4 base conformance is already covered by `LPDF_PDFX_CONF`
through veraPDF, so this check focuses purely on the structural
delta between PDF/X-4 and PDF/VT.

Files:
- `packages/engine/src/lintpdf/conformance/pdfvt.py` — new module.
- `packages/engine/src/lintpdf/profiles/orchestrator.py` — wires
  `check_pdfvt_structure(document)` into Step 5c.
- `packages/engine/tests/analyzers/test_batch10b.py` — 3 cases.
