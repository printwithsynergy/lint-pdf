# Phase 0.3 — Blast-radius map

**Generated:** 2026-04-24  
**Scope:** every `.py` under `packages/engine/src/lintpdf/analyzers/` (deterministic LPDF_* checks).  
**Out of scope here:** AI analyzers under `packages/engine/src/lintpdf/ai/analyzers/` — separate map in Phase 1 if AI checks land in the backlog.

Source: `audit/phase-0/blast-radius.json` (machine-readable rows).

## Summary

| Metric | Value |
|---|---:|
| Modules audited | **31** |
| Total LOC (non-blank, non-comment) | 12,139 |
| Total emitted check IDs | 261 |
| Modules with a `test_<name>.py` test file | 18/31 (58%) |
| Risk: high | 14 |
| Risk: medium | 11 |
| Risk: low | 6 |

**Risk heuristic:** `high` if importer_count ≥ 5 OR LOC > 600; `medium` if importer_count ≥ 2 OR LOC > 250 OR check_count ≥ 8; otherwise `low`. Untested modules with any non-trivial use are bumped one notch.

## High risk (touch with care; tests required before any change)

| Module | LOC | Checks | Importers | Test | Notes |
|---|---:|---:|---:|:--:|---|
| `ecg_analyzer.py` | 1,047 | 18 | 1 | ❌ | **No test file.** Emits 18 checks — change blast-radius is wide. Module > 800 LOC — split candidate. |
| `advanced_color_analyzer.py` | 942 | 15 | 1 | ❌ | **No test file.** Emits 15 checks — change blast-radius is wide. Module > 800 LOC — split candidate. |
| `barcode.py` | 920 | 28 | 1 | ✅ | Emits 28 checks — change blast-radius is wide. Module > 800 LOC — split candidate. |
| `spot_color_analyzer.py` | 858 | 11 | 1 | ❌ | **No test file.** Module > 800 LOC — split candidate. |
| `color.py` | 827 | 21 | 1 | ✅ | Emits 21 checks — change blast-radius is wide. Module > 800 LOC — split candidate. |
| `dieline.py` | 734 | 0 | 2 | ❌ | **No test file.** |
| `epm_analyzer.py` | 669 | 18 | 1 | ❌ | **No test file.** Emits 18 checks — change blast-radius is wide. |
| `icc_profile_analyzer.py` | 514 | 9 | 1 | ❌ | **No test file.** |
| `gamut_analyzer.py` | 386 | 3 | 3 | ❌ | **No test file.** |
| `standards_compliance.py` | 352 | 3 | 1 | ❌ | **No test file.** |
| `packaging.py` | 345 | 10 | 2 | ❌ | **No test file.** |
| `ink_coverage_analyzer.py` | 297 | 3 | 1 | ❌ | **No test file.** |
| `finding.py` | 42 | 0 | 105 | ✅ | — |
| `base.py` | 30 | 0 | 25 | ❌ | **No test file.** |

## Medium risk

| Module | LOC | Checks | Importers | Test |
|---|---:|---:|---:|:--:|
| `image.py` | 593 | 17 | 1 | ✅ |
| `hairline.py` | 505 | 15 | 1 | ✅ |
| `structure.py` | 461 | 14 | 1 | ✅ |
| `page_geometry.py` | 400 | 9 | 1 | ✅ |
| `font.py` | 342 | 14 | 1 | ✅ |
| `overprint.py` | 294 | 8 | 1 | ✅ |
| `accessibility.py` | 231 | 13 | 1 | ✅ |
| `document.py` | 193 | 8 | 1 | ✅ |
| `legend.py` | 138 | 0 | 1 | ❌ |
| `text_metrics.py` | 97 | 0 | 2 | ✅ |
| `art_size.py` | 58 | 0 | 1 | ❌ |

## Low risk

| Module | LOC | Checks | Importers | Test |
|---|---:|---:|---:|:--:|
| `transparency.py` | 215 | 7 | 1 | ✅ |
| `cxf_parser.py` | 205 | 0 | 1 | ✅ |
| `prepress.py` | 143 | 5 | 1 | ✅ |
| `annotation.py` | 130 | 6 | 1 | ✅ |
| `processing.py` | 88 | 2 | 1 | ✅ |
| `metadata.py` | 83 | 4 | 1 | ✅ |

## Untested risky modules (priority for Phase 2 test backfill)

These modules have no `test_<name>.py` yet score medium/high blast radius. Adding a regression test should land **before** any check change in Phase 2.

| Module | LOC | Checks | Risk |
|---|---:|---:|---|
| `ecg_analyzer.py` | 1,047 | 18 | high |
| `advanced_color_analyzer.py` | 942 | 15 | high |
| `spot_color_analyzer.py` | 858 | 11 | high |
| `dieline.py` | 734 | 0 | high |
| `epm_analyzer.py` | 669 | 18 | high |
| `icc_profile_analyzer.py` | 514 | 9 | high |
| `gamut_analyzer.py` | 386 | 3 | high |
| `standards_compliance.py` | 352 | 3 | high |
| `packaging.py` | 345 | 10 | high |
| `ink_coverage_analyzer.py` | 297 | 3 | high |
| `legend.py` | 138 | 0 | medium |
| `art_size.py` | 58 | 0 | medium |
| `base.py` | 30 | 0 | high |

## Where the analyzers are wired

Most analyzers are imported by `packages/engine/src/lintpdf/profiles/orchestrator.py` (the central fan-out). Modules with importer_count > 1 are listed with their consumers below.

| Module | Importer paths |
|---|---|
| `finding.py` | `packages/engine/src/lintpdf/ai/analyzers/barcode/barcode_content.py`<br>`packages/engine/src/lintpdf/ai/analyzers/barcode/barcode_content_qr_match.py`<br>`packages/engine/src/lintpdf/ai/analyzers/barcode/barcode_decode.py`<br>`packages/engine/src/lintpdf/ai/analyzers/barcode/barcode_dimensions.py`<br>`packages/engine/src/lintpdf/ai/analyzers/barcode/pharma_serialization.py`<br>`packages/engine/src/lintpdf/ai/analyzers/barcode/qr_human_readable.py`<br>`packages/engine/src/lintpdf/ai/analyzers/barcode/qr_validation.py`<br>`packages/engine/src/lintpdf/ai/analyzers/color_analysis/banding_detection.py`<br>`packages/engine/src/lintpdf/ai/analyzers/color_analysis/color_cast_detection.py`<br>`packages/engine/src/lintpdf/ai/analyzers/color_analysis/cross_document_consistency.py`<br>`packages/engine/src/lintpdf/ai/analyzers/color_analysis/skin_tone_validation.py`<br>`packages/engine/src/lintpdf/ai/analyzers/color_compliance/brand_palette.py`<br>`packages/engine/src/lintpdf/ai/analyzers/color_compliance/dieline_by_color_name.py`<br>`packages/engine/src/lintpdf/ai/analyzers/color_compliance/wcag_contrast.py`<br>`packages/engine/src/lintpdf/ai/analyzers/content_quality/duplicate_detection.py`<br>`packages/engine/src/lintpdf/ai/analyzers/content_quality/language_detection.py`<br>`packages/engine/src/lintpdf/ai/analyzers/content_quality/spell_check.py`<br>`packages/engine/src/lintpdf/ai/analyzers/dieline_detection/dieline_by_name.py`<br>`packages/engine/src/lintpdf/ai/analyzers/document_classification/auto_preflight_profile.py`<br>`packages/engine/src/lintpdf/ai/analyzers/document_classification/file_classification.py`<br>`packages/engine/src/lintpdf/ai/analyzers/file_comparison/version_diff.py`<br>`packages/engine/src/lintpdf/ai/analyzers/image_analysis/image_quality.py`<br>`packages/engine/src/lintpdf/ai/analyzers/image_analysis/image_similarity.py`<br>`packages/engine/src/lintpdf/ai/analyzers/image_analysis/nsfw_detection.py`<br>`packages/engine/src/lintpdf/ai/analyzers/logo_verification/logo_detection.py`<br>`packages/engine/src/lintpdf/ai/analyzers/nlp_interfaces/multi_language.py`<br>`packages/engine/src/lintpdf/ai/analyzers/nlp_interfaces/nl_preflight_profile.py`<br>`packages/engine/src/lintpdf/ai/analyzers/nlp_interfaces/nl_report_interpret.py`<br>`packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/alcohol.py`<br>`packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/cannabis.py`<br>`packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/cosmetics.py`<br>`packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/eu_fir_1169.py`<br>`packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/fda_nutrition.py`<br>`packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/fda_otc.py`<br>`packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/ghs_clp.py`<br>`packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/organic.py`<br>`packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/pharma_font.py`<br>`packages/engine/src/lintpdf/ai/analyzers/spatial_analysis/safe_zone_violations.py`<br>`packages/engine/src/lintpdf/ai/analyzers/symbol_detection/processing_steps_fallback.py`<br>`packages/engine/src/lintpdf/ai/analyzers/symbol_detection/regulatory_symbols.py`<br>`packages/engine/src/lintpdf/ai/analyzers/text_analysis/text_as_outlines.py`<br>`packages/engine/src/lintpdf/ai/analyzers/trend_analysis/submission_quality_spc.py`<br>`packages/engine/src/lintpdf/ai/base.py`<br>`packages/engine/src/lintpdf/analyzers/__init__.py`<br>`packages/engine/src/lintpdf/analyzers/accessibility.py`<br>`packages/engine/src/lintpdf/analyzers/advanced_color_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/annotation.py`<br>`packages/engine/src/lintpdf/analyzers/barcode.py`<br>`packages/engine/src/lintpdf/analyzers/base.py`<br>`packages/engine/src/lintpdf/analyzers/color.py`<br>`packages/engine/src/lintpdf/analyzers/document.py`<br>`packages/engine/src/lintpdf/analyzers/ecg_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/epm_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/font.py`<br>`packages/engine/src/lintpdf/analyzers/gamut_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/hairline.py`<br>`packages/engine/src/lintpdf/analyzers/icc_profile_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/image.py`<br>`packages/engine/src/lintpdf/analyzers/ink_coverage_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/metadata.py`<br>`packages/engine/src/lintpdf/analyzers/overprint.py`<br>`packages/engine/src/lintpdf/analyzers/packaging.py`<br>`packages/engine/src/lintpdf/analyzers/page_geometry.py`<br>`packages/engine/src/lintpdf/analyzers/prepress.py`<br>`packages/engine/src/lintpdf/analyzers/processing.py`<br>`packages/engine/src/lintpdf/analyzers/spot_color_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/standards_compliance.py`<br>`packages/engine/src/lintpdf/analyzers/structure.py`<br>`packages/engine/src/lintpdf/analyzers/transparency.py`<br>`packages/engine/src/lintpdf/color_score.py`<br>`packages/engine/src/lintpdf/conformance/base.py`<br>`packages/engine/src/lintpdf/conformance/pdfa/__init__.py`<br>`packages/engine/src/lintpdf/conformance/pdfa/_color.py`<br>`packages/engine/src/lintpdf/conformance/pdfa/_font.py`<br>`packages/engine/src/lintpdf/conformance/pdfa/_metadata.py`<br>`packages/engine/src/lintpdf/conformance/pdfa/_restrictions.py`<br>`packages/engine/src/lintpdf/conformance/pdfx1a/__init__.py`<br>`packages/engine/src/lintpdf/conformance/pdfx1a/_color.py`<br>`packages/engine/src/lintpdf/conformance/pdfx1a/_font.py`<br>`packages/engine/src/lintpdf/conformance/pdfx1a/_metadata.py`<br>`packages/engine/src/lintpdf/conformance/pdfx1a/_output_intent.py`<br>`packages/engine/src/lintpdf/conformance/pdfx1a/_restrictions.py`<br>`packages/engine/src/lintpdf/conformance/pdfx1a/_transparency.py`<br>`packages/engine/src/lintpdf/conformance/pdfx3/__init__.py`<br>`packages/engine/src/lintpdf/conformance/pdfx3/_color.py`<br>`packages/engine/src/lintpdf/conformance/pdfx3/_font.py`<br>`packages/engine/src/lintpdf/conformance/pdfx3/_metadata.py`<br>`packages/engine/src/lintpdf/conformance/pdfx3/_output_intent.py`<br>`packages/engine/src/lintpdf/conformance/pdfx3/_restrictions.py`<br>`packages/engine/src/lintpdf/conformance/pdfx3/_transparency.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/__init__.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_annotations.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_boxes.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_color.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_file_structure.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_font.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_images.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_metadata.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_optional_content.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_output_intent.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_resources.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_restricted_features.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_security.py`<br>`packages/engine/src/lintpdf/conformance/pdfx4/_transparency.py`<br>`packages/engine/src/lintpdf/profiles/orchestrator.py` |
| `base.py` | `packages/engine/src/lintpdf/analyzers/__init__.py`<br>`packages/engine/src/lintpdf/analyzers/accessibility.py`<br>`packages/engine/src/lintpdf/analyzers/advanced_color_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/annotation.py`<br>`packages/engine/src/lintpdf/analyzers/barcode.py`<br>`packages/engine/src/lintpdf/analyzers/color.py`<br>`packages/engine/src/lintpdf/analyzers/document.py`<br>`packages/engine/src/lintpdf/analyzers/ecg_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/epm_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/font.py`<br>`packages/engine/src/lintpdf/analyzers/gamut_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/hairline.py`<br>`packages/engine/src/lintpdf/analyzers/icc_profile_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/image.py`<br>`packages/engine/src/lintpdf/analyzers/ink_coverage_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/metadata.py`<br>`packages/engine/src/lintpdf/analyzers/overprint.py`<br>`packages/engine/src/lintpdf/analyzers/packaging.py`<br>`packages/engine/src/lintpdf/analyzers/page_geometry.py`<br>`packages/engine/src/lintpdf/analyzers/prepress.py`<br>`packages/engine/src/lintpdf/analyzers/processing.py`<br>`packages/engine/src/lintpdf/analyzers/spot_color_analyzer.py`<br>`packages/engine/src/lintpdf/analyzers/standards_compliance.py`<br>`packages/engine/src/lintpdf/analyzers/structure.py`<br>`packages/engine/src/lintpdf/analyzers/transparency.py` |
| `gamut_analyzer.py` | `packages/engine/src/lintpdf/profiles/icc/build_gamut_meshes.py`<br>`packages/engine/src/lintpdf/profiles/icc/pantone_manager.py`<br>`packages/engine/src/lintpdf/profiles/orchestrator.py` |
| `dieline.py` | `packages/engine/src/lintpdf/ai/dieline_claude.py`<br>`packages/engine/src/lintpdf/queue/tasks.py` |
| `packaging.py` | `packages/engine/src/lintpdf/analyzers/__init__.py`<br>`packages/engine/src/lintpdf/profiles/orchestrator.py` |
| `text_metrics.py` | `packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/eu_fir_1169.py`<br>`packages/engine/src/lintpdf/ai/analyzers/regulatory_compliance/pharma_font.py` |

## Notable single-file complexity

- `barcode.py` — 920 LOC, 28 emitted checks. The biggest single-rule-family analyzer; touches LPDF_BARCODE_001..028. Has tests.
- `color.py` — 827 LOC, 21 checks. LPDF_COLOR_* family + LPDF_INK_* hand-offs. Has tests.
- `ecg_analyzer.py` — 1,047 LOC, 18 checks. Extended-Colour-Gamut (multi-channel beyond CMYK) checks — none in catalog. **No test.**
- `epm_analyzer.py` — 669 LOC, 18 checks. Equivalent Process-Match analyzer. **No test.**
- `dieline.py` — 734 LOC, 0 emitted check IDs (analyzer is data-feeding, not finding-emitting). 2 importers. **No test of its own** (read this session — relied on by `DielineOverlay.tsx` viewer surface; the recent CTM fix in commit `912cf16` shipped without a unit test).
- `advanced_color_analyzer.py` — 942 LOC, 15 checks (LPDF_ADV_*). Recently extended in WS-7/WS-8 (per-page aggregation + pixel K gate). **No test.**
- `spot_color_analyzer.py` — 858 LOC, 11 checks. LPDF_SPOT_*. **No test.**
- `icc_profile_analyzer.py` — 514 LOC, 9 checks. LPDF_ICC_*. **No test.**

## Phase-0 follow-ups recorded for the Q&A gate

- The four largest analyzers (`ecg_analyzer`, `epm_analyzer`, `spot_color_analyzer`, `icc_profile_analyzer`, `advanced_color_analyzer`) emit 71 catalogued/uncatalogued checks combined and have **zero unit tests**. Phase 1 priority scoring should weight any change there as high-risk until at least a smoke-level regression test exists.
- `dieline.py` is the only large analyzer that emits no findings — it produces structured data consumed by the viewer and downstream art-info rules. Treat it as a data source, not a check; carve out its own follow-up if Phase 1 wants dieline-derived checks (e.g. dieline-vs-trim-mismatch warnings).
