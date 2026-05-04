---
title: "External preflight imports"
description: "Import third-party preflight reports (Enfocus PitStop, callas pdfToolbox, Adobe Acrobat Pro Preflight) so their findings join LintPDF's output — useful for vendor-neutral consolidated reporting."
group: "Reference"
order: 9
---

# External preflight imports

LintPDF can ingest preflight reports produced by other vendors and
fold their findings into the same `Job` shape that native analyzers
emit. Useful when you already run PitStop or pdfToolbox upstream and
want a single consolidated audit trail without re-running the file
through every checker.

## Supported formats

Five format tokens map 1:1 to parsers under
[`src/lintpdf/imports/`](../src/lintpdf/imports/):

| Token          | Vendor / source                                | Parser                                                              |
|----------------|------------------------------------------------|---------------------------------------------------------------------|
| `pitstop_xml`  | Enfocus PitStop / PitStop Server reports       | [`pitstop.py`](../src/lintpdf/imports/pitstop.py)                   |
| `callas_json`  | callas pdfToolbox JSON export                  | [`callas.py`](../src/lintpdf/imports/callas.py)                     |
| `callas_xml`   | callas pdfToolbox XML export                   | [`callas.py`](../src/lintpdf/imports/callas.py)                     |
| `acrobat_xml`  | Adobe Acrobat Pro Preflight XML export         | [`acrobat.py`](../src/lintpdf/imports/acrobat.py)                   |
| `lintpdf_json` | LintPDF native re-import (round-trip / replay) | [`lintpdf_native.py`](../src/lintpdf/imports/lintpdf_native.py)     |

The parser-protocol contract lives in
[`base.py`](../src/lintpdf/imports/base.py): each parser exposes a
`format` class attribute (one of the tokens above) and a `parse(payload:
bytes) -> ImportedReport` method.

## Auto-detection

If you don't set `external_format` explicitly on a submission, the
engine sniffs the payload via
[`detect.py`](../src/lintpdf/imports/detect.py):

- **JSON** payloads: routed to `lintpdf_json` if the document carries
  `schema_version` + `findings`, or to `callas_json` if it has
  `hits` / `results` plus pdfToolbox-shaped metadata.
- **XML** payloads: dispatched by root element — `<Preflight>` /
  `<AcrobatReport>` → `acrobat_xml`, `<EnfocusReport>` /
  `<PitStopReport>` → `pitstop_xml`, `<preflight_report>` /
  `<callasreport>` → `callas_xml`. Heuristic fallbacks check for
  signature child elements (`<Hit>`, `<ResultItem>`, `<Problem>`).

When detection fails the parser raises `ParserError` and the API
responds **422** carrying the field path that broke. Per the engine
contract: parsers must fail cleanly — never swallow a parse error and
emit zero findings, since the caller would assume their report was
clean.

## Adding a new format

Per the engine's `CLAUDE.md` contract, adding a built-in format is
exactly three changes:

1. New parser under `src/lintpdf/imports/<vendor>.py`, registered in
   `src/lintpdf/imports/detect.py`.
2. New round-trippable sample fixture committed alongside the parser's
   tests.
3. New row in the `external_format` enum appendix and the
   supported-formats table in the public docs.

Vendor-specific implementations stay isolated — the engine's analyzer
tier never touches the parser modules; everything funnels through the
unified `ImportedReport` shape.
