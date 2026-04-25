# T4-A10 — ViewerPreferences DisplayDocTitle — DONE

`LPDF_VIEWER_DISPLAY_TITLE` (advisory) fires when the document
catalog's `/ViewerPreferences /DisplayDocTitle` is absent or set
to false. PDF readers fall back to the filename for the window
title bar instead of the metadata title — failing WCAG 2.1 SC
2.4.2 (Page Titled) when the title is the meaningful document
identifier.

Files:
- `packages/engine/src/lintpdf/analyzers/metadata.py` —
  `_check_display_doc_title()`.
- `packages/engine/tests/analyzers/test_batch10a.py` — 3 cases.
