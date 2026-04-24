# Phase 0.3b — Blast-radius map (AI analyzers)

**Generated:** 2026-04-24  
**Scope:** every `.py` (excluding `__init__.py`) under `packages/engine/src/lintpdf/ai/analyzers/`. **Companion to** `blast-radius.md` (deterministic LPDF_* analyzers).

Source: `audit/phase-0/blast-radius-ai.json` (machine-readable rows).

## Summary

| Metric | Value |
|---|---:|
| AI analyzer modules | **44** (60 .py files including __init__.py shims) |
| Total LOC (non-blank, non-comment) | 6,926 |
| Total emitted check IDs (sum across modules) | 101 |
| Docstring-only IDs (declared, not emitted) | 8 |
| With matching `test_<name>.py` | 9/44 (20%) |
| **Stubs** (analyze() returns []) | **8** |
| Risk: high | 7 |
| Risk: medium | 16 |
| Risk: low | 13 |

**Risk heuristic:** same as deterministic blast-radius, plus a `stub` bucket for analyzers whose `analyze()` body returns `[]` unconditionally — they advertise check IDs in docstrings but emit nothing at runtime.

## Subdirectory breakdown

| Subdir | Modules | LOC | Checks | With tests | Stubs |
|---|---:|---:|---:|---:|---:|
| `barcode/` | 7 | 1,825 | 25 | 1 | 0 |
| `regulatory_compliance/` | 11 | 1,566 | 20 | 4 | 6 |
| `color_compliance/` | 3 | 459 | 6 | 1 | 0 |
| `content_quality/` | 3 | 424 | 5 | 2 | 0 |
| `symbol_detection/` | 2 | 400 | 6 | 0 | 0 |
| `color_analysis/` | 4 | 385 | 4 | 0 | 0 |
| `image_analysis/` | 3 | 325 | 8 | 0 | 0 |
| `trend_analysis/` | 1 | 305 | 4 | 0 | 0 |
| `document_classification/` | 2 | 241 | 6 | 0 | 0 |
| `nlp_interfaces/` | 3 | 217 | 4 | 0 | 2 |
| `dieline_detection/` | 1 | 212 | 3 | 1 | 0 |
| `file_comparison/` | 1 | 152 | 3 | 0 | 0 |
| `text_analysis/` | 1 | 151 | 2 | 0 | 0 |
| `spatial_analysis/` | 1 | 139 | 2 | 0 | 0 |
| `logo_verification/` | 1 | 125 | 3 | 0 | 0 |

## Stubs (analyze() returns [] — not actually implemented)

These analyzers register check IDs in their class docstring (the WS-12 catalog picks them up via `check_names.py`) but ship `return []  # Stub` as the analyze() body. Findings will never appear in production output until someone replaces the body.

| Module | Subdir | LOC | Docstring-declared IDs | Note |
|---|---|---:|---|---|
| `nl_preflight_profile.py` | `nlp_interfaces` | 37 | (none in docstring) | — |
| `nl_report_interpret.py` | `nlp_interfaces` | 36 | (none in docstring) | — |
| `alcohol.py` | `regulatory_compliance` | 31 | AI_ALC_001, AI_ALC_002 | Marked `tier=gpu` — needs inference service. |
| `cannabis.py` | `regulatory_compliance` | 30 | AI_CANN_001, AI_CANN_002 | Marked `tier=gpu` — needs inference service. |
| `cosmetics.py` | `regulatory_compliance` | 31 | AI_COSM_001, AI_COSM_002 | Marked `tier=gpu` — needs inference service. |
| `fda_otc.py` | `regulatory_compliance` | 26 | (none in docstring) | Marked `tier=gpu` — needs inference service. |
| `nfp_detector.py` | `regulatory_compliance` | 120 | (none in docstring) | — |
| `organic.py` | `regulatory_compliance` | 32 | AI_ORG_001, AI_ORG_002 | Marked `tier=gpu` — needs inference service. |

## High risk (large analyzers and/or many imports)

| Module | Subdir | LOC | Checks | Importers | Test |
|---|---|---:|---:|---:|:--:|
| `barcode_content.py` | `barcode` | 345 | 3 | 0 | ❌ |
| `barcode_content_qr_match.py` | `barcode` | 331 | 4 | 0 | ❌ |
| `barcode_dimensions.py` | `barcode` | 329 | 4 | 0 | ❌ |
| `submission_quality_spc.py` | `trend_analysis` | 305 | 4 | 1 | ❌ |
| `pharma_serialization.py` | `barcode` | 263 | 6 | 0 | ❌ |
| `fda_nutrition.py` | `regulatory_compliance` | 254 | 5 | 1 | ❌ |
| `_gates.py` | `regulatory_compliance` | 58 | 0 | 2 | ❌ |

## Medium risk

| Module | Subdir | LOC | Checks | Importers | Test |
|---|---|---:|---:|---:|:--:|
| `ghs_clp.py` | `regulatory_compliance` | 378 | 8 | 1 | ✅ |
| `eu_fir_1169.py` | `regulatory_compliance` | 328 | 3 | 1 | ✅ |
| `pharma_font.py` | `regulatory_compliance` | 278 | 4 | 1 | ✅ |
| `qr_validation.py` | `barcode` | 217 | 4 | 0 | ❌ |
| `qr_human_readable.py` | `barcode` | 204 | 3 | 0 | ❌ |
| `processing_steps_fallback.py` | `symbol_detection` | 204 | 3 | 0 | ❌ |
| `regulatory_symbols.py` | `symbol_detection` | 196 | 3 | 0 | ❌ |
| `language_detection.py` | `content_quality` | 164 | 2 | 1 | ❌ |
| `wcag_contrast.py` | `color_compliance` | 163 | 2 | 1 | ❌ |
| `version_diff.py` | `file_comparison` | 152 | 3 | 1 | ❌ |
| `text_as_outlines.py` | `text_analysis` | 151 | 2 | 0 | ❌ |
| `color_cast_detection.py` | `color_analysis` | 111 | 1 | 1 | ❌ |
| `cross_document_consistency.py` | `color_analysis` | 102 | 1 | 1 | ❌ |
| `banding_detection.py` | `color_analysis` | 89 | 1 | 1 | ❌ |
| `skin_tone_validation.py` | `color_analysis` | 83 | 1 | 1 | ❌ |
| `dieline_by_color_name.py` | `color_compliance` | 83 | 1 | 1 | ❌ |

## Low risk

| Module | Subdir | LOC | Checks | Importers | Test |
|---|---|---:|---:|---:|:--:|
| `brand_palette.py` | `color_compliance` | 213 | 3 | 1 | ✅ |
| `dieline_by_name.py` | `dieline_detection` | 212 | 3 | 1 | ✅ |
| `spell_check.py` | `content_quality` | 168 | 2 | 1 | ✅ |
| `multi_language.py` | `nlp_interfaces` | 144 | 4 | 0 | ❌ |
| `auto_preflight_profile.py` | `document_classification` | 143 | 3 | 0 | ❌ |
| `safe_zone_violations.py` | `spatial_analysis` | 139 | 2 | 0 | ❌ |
| `barcode_decode.py` | `barcode` | 136 | 1 | 0 | ✅ |
| `nsfw_detection.py` | `image_analysis` | 128 | 3 | 0 | ❌ |
| `logo_detection.py` | `logo_verification` | 125 | 3 | 0 | ❌ |
| `image_quality.py` | `image_analysis` | 108 | 3 | 0 | ❌ |
| `file_classification.py` | `document_classification` | 98 | 3 | 0 | ❌ |
| `duplicate_detection.py` | `content_quality` | 92 | 1 | 1 | ✅ |
| `image_similarity.py` | `image_analysis` | 89 | 2 | 0 | ❌ |

## Untested risky AI modules (priority for Phase 2 test backfill)

20 non-stub modules score medium/high risk without a `test_<name>.py`. AI analyzers are inherently model-backed and harder to unit-test, but at least an input-shape regression test should land before changing them.

| Module | Subdir | LOC | Checks | Risk |
|---|---|---:|---:|---|
| `barcode_content.py` | `barcode` | 345 | 3 | high |
| `barcode_content_qr_match.py` | `barcode` | 331 | 4 | high |
| `barcode_dimensions.py` | `barcode` | 329 | 4 | high |
| `submission_quality_spc.py` | `trend_analysis` | 305 | 4 | high |
| `pharma_serialization.py` | `barcode` | 263 | 6 | high |
| `fda_nutrition.py` | `regulatory_compliance` | 254 | 5 | high |
| `qr_validation.py` | `barcode` | 217 | 4 | medium |
| `qr_human_readable.py` | `barcode` | 204 | 3 | medium |
| `processing_steps_fallback.py` | `symbol_detection` | 204 | 3 | medium |
| `regulatory_symbols.py` | `symbol_detection` | 196 | 3 | medium |
| `language_detection.py` | `content_quality` | 164 | 2 | medium |
| `wcag_contrast.py` | `color_compliance` | 163 | 2 | medium |
| `version_diff.py` | `file_comparison` | 152 | 3 | medium |
| `text_as_outlines.py` | `text_analysis` | 151 | 2 | medium |
| `color_cast_detection.py` | `color_analysis` | 111 | 1 | medium |
| `cross_document_consistency.py` | `color_analysis` | 102 | 1 | medium |
| `banding_detection.py` | `color_analysis` | 89 | 1 | medium |
| `skin_tone_validation.py` | `color_analysis` | 83 | 1 | medium |
| `dieline_by_color_name.py` | `color_compliance` | 83 | 1 | medium |
| `_gates.py` | `regulatory_compliance` | 58 | 0 | high |

## Notable findings

- **8 of 44 AI analyzers are stubs.** Each advertises check IDs (some catalogued in WS-12) but emits nothing. Tenants who toggle these severities in the rules editor see no effect. Phase 1 needs a per-stub triage decision: implement (Tier-3+ priority depending on regulation reach), drop from catalog, or surface as 'planned' in the UI.
- **Test coverage is 9/44 (20%)** vs 18/31 (58%) for deterministic analyzers. AI checks are the most likely place to introduce silent regressions when changing prompts or model versions.
- **`regulatory_compliance/` subdir is the largest** (11 modules, biggest by LOC). Includes `eu_fir_1169.py`, `pharma_font.py`, `fda_nutrition.py`, `ghs_clp.py`, `nfp_detector.py`, `_gates.py` — all touched in WS-2..WS-6 of the prior Phase 1/2 plans.
- **`barcode/` subdir (7 modules) is mostly uncatalogued.** Pulls in `pyzbar`/`pylibdmtx`-style 1D/2D decoders behind AI gating. 25 emitted IDs in this subdir, 0 in WS-12 catalog (confirmed by `existing-checks.json` `category_id == ai_barcode`).
