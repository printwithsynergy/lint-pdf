# T1-CMP06 — Embedded files / attachments

## What the check detects

Two embedding paths for attachments collapse into one inspection_id
(`LPDF_STRUCT_004`, severity warning):

1. **`/Names /EmbeddedFiles` tree at catalog level** — the canonical
   attachment location per ISO 32000-2 §7.11.4. Always the primary
   path Acrobat uses when `File > Attach File` is clicked.
2. **`/FileAttachment` annotation on a page** — the alternative
   attachment location per ISO 32000-2 §12.5.6.15. Less common but
   widely used by XFA-authored forms and some legacy Acrobat plug-ins.

Previous implementation only covered path #1. Path #2 is the extension
landed in this batch.

## Details on emit

`details.source` distinguishes the two paths:
- `"catalog_names_tree"` — found via `/Names /EmbeddedFiles`
- `"file_attachment_annotation"` — found via page annotation walk,
  with `details.attachment_count` carrying the annotation count

## Dedup behaviour

At most one `LPDF_STRUCT_004` emits per document. When both paths exist,
the catalog-tree path wins (canonical location). This matches the
existing single-finding policy for LPDF_STRUCT_002 (form fields), _003
(OCG layers), etc.

## Read-only

Confirmed. Reads `document.catalog["/Names"]` and iterates
`page.annotations`. No pikepdf writes.

## Profiles

Universal warning across all bundled profiles. PDF/X forbids embedded
files outright per ISO 15930-7 §6.2.8.

## Verification

`tests/analyzers/test_file_attachment_detection.py` — 5 cases:
- single `/FileAttachment` annotation fires
- multiple annotations → one finding with count in details
- no attachments → silent
- empty annotations list → silent
- catalog-tree path AND annotation both present → catalog wins

All pass; test count: +5 in the engine test suite.

## Outcome

Tiny extension (+25 LOC to structure.py). Gap-mapping corrected to
`present`. `status.md` set to `verified`.
