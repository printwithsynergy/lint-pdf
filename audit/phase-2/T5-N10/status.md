# T5-N10 — Grain direction preservation — DONE

`LPDF_GRAIN_MISSING` (advisory) fires when the document's XMP
metadata stream has no grain-direction key. Detection scans both
the parsed XMP property keys and the raw bytes for `grain` or
`machine-direction` substrings — covers the GWG packaging
supplements, ISO 16763 (folding-carton XMP), and any custom
namespace used by packaging suppliers.

Grain direction is critical for folding-carton / corrugated
finishing (panels need to fold along the grain to avoid cracking).
A read-only metadata check is the strongest signal lintPDF can
produce; lintPDF can't fix the metadata, only flag the absence.

Files:
- `packages/engine/src/lintpdf/analyzers/metadata.py` —
  `_check_grain_direction()`.
- `packages/engine/tests/analyzers/test_batch10b.py` — 2 cases.
