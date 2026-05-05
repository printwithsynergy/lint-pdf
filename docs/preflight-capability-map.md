# LintPDF preflight capability map (engine)

This document maps what the `lint-pdf/` engine can **detect** today to the major preflight “surfaces” (print production, packaging, accessibility/PDF-UA, and AI regulatory checks), and to the builtin profiles that enable them.

## Profiles (builtin)

- `lintpdf-default.json`
  - **Enabled**: `LPDF_*`, `PDFX4-*`, `PDFX1A-*`, `PDFA-*`, `AI_*`
  - **Conformance target**: `pdfx4`
  - **Notes**: AI enabled (`categories=["all"]`)
- `lintpdf-strict.json`
  - **Enabled**: `LPDF_*`, `PDFX4-*`
  - **Conformance target**: `pdfx4`
  - **Notes**: stricter DPI + small-text thresholds; **AI disabled** (no `AI_*`)
- `lintpdf-advisory-only.json`
  - **Enabled**: `LPDF_*` (with `max_severity="advisory"`)
  - **Conformance target**: none
  - **Notes**: good for “non-blocking” runs; explicitly disables `PDFX4-*`

## Engine pipeline (what runs)

The main pipeline is `PreflightOrchestrator.run()` in `src/lintpdf/profiles/orchestrator.py`:

1. Parse PDF (`pikepdf`)
2. Build semantic model (pages, resources, fonts, images, boxes)
3. Interpret content streams into events (text/image/path paint events)
4. Run engine analyzers (deterministic `LPDF_*`)
5. Run built-in conformance validators (PDF/X, PDF/A variants) where configured
6. Run veraPDF conformance (PDF/X, PDF/A, PDF/UA) when configured and opted-in
7. Run OCR text-region pass (best-effort; enables outlined-text heuristics)
8. Run AI analyzers (if profile enables `AI_*` and `profile.ai.enabled`)
9. Filter/override findings per profile rules; enrich bboxes from events

## Detection domains (non-AI, `LPDF_*`)

### Print production & structural

- **Page boxes / bleed / safety / dimensions**: `PageGeometryAnalyzer`
  - IDs: `LPDF_BOX_*` (incl. `LPDF_BOX_005`, `LPDF_BOX_006`, `LPDF_BOX_010`)
- **Fonts**: `FontAnalyzer`
  - IDs: `LPDF_FONT_*`
- **Images / effective DPI / compression**: `ImageAnalyzer`
  - IDs: `LPDF_IMG_*`
- **Transparency / blend-space**: `TransparencyAnalyzer`
  - IDs: `LPDF_TRANS_*`
- **Overprint**: `OverprintAnalyzer`
  - IDs: `LPDF_OVER_*`
- **ICC profiles / output intent**: `IccProfileAnalyzer`
  - IDs: `LPDF_ICC_*`
- **Metadata / XMP / language**: `MetadataAnalyzer`
  - IDs: `LPDF_META_*`, `LPDF_LANG_*`, `LPDF_XMP_*`
- **Structure / encryption / interactive features**: `StructureAnalyzer`, `DocumentAnalyzer`, `AnnotationAnalyzer`
  - IDs: `LPDF_STRUCT_*`, `LPDF_DOC_*`, `LPDF_ANNOT_*` (varies by module)

### Color, ink coverage, and prepress heuristics

- **Ink coverage**: `InkCoverageAnalyzer`
  - IDs: `LPDF_INK_*`
- **Spot colors**: `SpotColorAnalyzer` + spot-name analyzers
  - IDs: `LPDF_SPOT_*`, `LPDF_SPOT_NAME_*`
- **Process/pure-K/rich-black classification**:
  - `ColorAnalyzer` (IDs: `LPDF_COLOR_009`, `LPDF_COLOR_010`, …)
  - `AdvancedColorAnalyzer` (IDs: `LPDF_ADV_*` incl. `LPDF_ADV_005`)

### Packaging-specific

- **PackagingAnalyzer** (only conditionally added when profile id contains `"packaging"`)
  - IDs: `LPDF_PKG_*`
- **Dieline family**: `DielineIso19593Analyzer`, `DielinePerfIndicatorAnalyzer`, plus orchestrator dieline detection attachment
  - IDs: `AI_DIE_*` (AI) and `LPDF_*` packaging geometry checks depending on analyzer
- **Seal zone / keepout**: `SealZoneKeepoutAnalyzer`
  - ID: `LPDF_BOX_SEAL_ZONE_VIOLATION`

### Barcodes

- **BarcodeAnalyzer**
  - 1D candidate detection + grading: `LPDF_BARCODE_001`–`013`, `019`–`031`
  - 2D fill-grid heuristics: `LPDF_BARCODE_014`–`018`

## Conformance (PDF/X, PDF/A, PDF/UA)

- **Built-in validators** (engine-side) run based on `profile.conformance`:
  - `pdfx4`, `pdfx1a`, `pdfx3`, `pdfa1b/2b/3b`
- **veraPDF runner** (`src/lintpdf/conformance/verapdf_runner.py`) runs when configured and emits:
  - `LPDF_PDFX_CONF` (PDF/X)
  - `LPDF_PDFA_CONF` (PDF/A)
  - `LPDF_UA_CONF` (PDF/UA-1; only when profile opts into `LPDF_UA_*`)

## AI analyzers (`AI_*`)

AI analyzers are registered in `src/lintpdf/ai/**` and run only when the profile enables AI.

Common families:
- **Regulatory compliance**: `AI_EU1169_*`, `AI_PHARMA_*`, `AI_FDA_*`, `AI_GHS_*`, `AI_COSM_*`, `LPDF_TOBACCO_*` (implemented as AI analyzer)
- **Accessibility (contrast)**: `AI_WCAG_*`

## Notable gaps / footguns to watch

- **“Enabled pattern” != “actually runs”**: some analyzers are conditionally added (e.g. packaging analyzer depends on profile id, not checks pattern).
- **veraPDF “silent skip”**: when veraPDF is unreachable, findings are suppressed (good for resilience, but you need metadata to know it didn’t run).
- **Outlined-text / hidden-layer text**: any rule that relies on `page.content_stream` string presence can miss/gate incorrectly unless OCR/text-region fallback is used.

