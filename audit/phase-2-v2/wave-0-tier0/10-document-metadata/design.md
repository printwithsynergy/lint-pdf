# Tier-0 Batch 10 — Document / Metadata predicates

**Wave:** 0 (Tier-0 primitives)
**Category:** doc.* (extends Batch 09 doc namespace)
**Primitive count:** 13
**EM estimate:** 0.20
**Date:** 2026-04-25

Per universe enumeration §4.10.

## Primitives (all under `doc.*` namespace)

### Conformance flags

| Primitive | Inputs | Returns |
|-----------|--------|---------|
| `pdf_version(doc)` | doc | str (e.g. "1.7", "2.0") or None |
| `is_pdf_x(doc)` | doc | bool — XMP `pdfx:GTS_PDFXVersion` present OR Info /GTS_PDFXVersion |
| `pdf_x_part(doc)` | doc | str (e.g. "PDF/X-4") or None |
| `is_pdf_a(doc)` | doc | bool — XMP `pdfaid:part` present |
| `pdf_a_part(doc)` | doc | str (e.g. "PDF/A-2b") or None |
| `is_pdf_va(doc)` | doc | bool — variant for accessibility (PDF/UA) |

### Content / objects

| Primitive | Inputs | Returns |
|-----------|--------|---------|
| `has_xmp(doc)` | doc | bool — Catalog /Metadata stream present |
| `acroform_present(doc)` | doc | bool — Catalog /AcroForm with non-empty /Fields |
| `has_javascript(doc)` | doc | bool — /Names /JavaScript or actions with JS |
| `has_embedded_files(doc)` | doc | bool |
| `has_output_intent(doc)` | doc | bool — Catalog /OutputIntents non-empty |
| `output_intent_subtype(doc)` | doc | str ("GTS_PDFX", "GTS_PDFA1", etc.) or None |
| `is_linearized(doc)` | doc | bool — fast-web-view |
| `signature_count(doc)` | doc | int |

## Module

`packages/engine/src/lintpdf/primitives/document.py` — extends `doc.*` namespace started in Batch 9.

## POC migration

`pdfx_compliance.py` analyzer hand-checks Info dict; flip to `doc_p.is_pdf_x()`.

## Read-only / no-stub

- ✓ Pure functions; no PDF mutation; ruff + mypy clean
