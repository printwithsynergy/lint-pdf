# T2-XMP01 — GWG XMP audit-trail namespace — DONE

`LPDF_XMP_GWG_TRAIL` (advisory) fires when the document's XMP
metadata stream contains no GWG audit-trail namespace
(`http://www.gwg.org/...`, `ghentpdfworkgroup`, etc.). Tells the
operator the PDF has not been through a Ghent Workgroup-aware
preflight tool — useful as a soft signal during incoming-file QA.

Detection scans both the parsed property keys and the raw XMP
bytes (since the parser strips the prefix when the namespace URI
is not in the well-known list).

Files:
- `packages/engine/src/lintpdf/analyzers/metadata.py` —
  `_check_gwg_namespace()`.
- `packages/engine/tests/analyzers/test_batch10a.py` — 2 cases.
