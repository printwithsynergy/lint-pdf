---
title: "Preflight engine audit"
description: "Engineering record tying the preflight capability map to known failure modes, the edits shipped in this cycle, and how to regress them."
group: "Project"
order: 12
---

# LintPDF preflight engine audit (implementation notes)

This document ties the **preflight capability map** ([preflight-capability-map.md](preflight-capability-map.md)) to **known failure modes**, the **edits shipped in this cycle**, and how to **regress** them.

## Executive summary

| Area | Risk | Mitigation shipped |
|------|------|---------------------|
| 2D barcode (`LPDF_BARCODE_014`–`018`) | Dense vector art / full-panel grids passed the structural gate | Trim-box **coverage cap**; when **zxing-cpp + raw PDF bytes** are available, require a **decoded QR/DataMatrix/Aztec/PDF417** in the raster crop before emitting the cascade. `document._pdf_bytes` is set in the orchestrator for crops. |
| AI text sizing (`AI_WCAG_*`, FDA, tobacco) | Raw `Tf` size ignored `Tm`/`CTM` composition | `effective_font_size_pt()` from [text_metrics.py](../src/lintpdf/analyzers/text_metrics.py) wired into WCAG, FDA nutrition text extraction, and tobacco warning bbox selection. |
| NFP gating (`AI_FDA_003`/`004`) | Outlined headers absent from `content_stream` | [nfp_detector.py](../src/lintpdf/ai/analyzers/regulatory_compliance/nfp_detector.py) merges **OCR `detected_text_regions`** text with stream text for the three-signal gate. |
| PDF/UA + veraPDF | Silent skip looked like “passed” | [verapdf_runner.py](../src/lintpdf/conformance/verapdf_runner.py) accepts optional **`metadata_out`**: configured / empty input / per-flavour **pass \| fail \| error**. [orchestrator.py](../src/lintpdf/profiles/orchestrator.py) exposes this as `metadata["verapdf"]` on `PreflightResult`. |

## Failure modes (residual / watch)

1. **veraPDF “pass” vs “unreachable”** — When the HTTP client returns an empty list, we still record `status: "pass"`. Distinguishing true conformance from parse/API ambiguity remains a product decision (would need response schema changes from the sidecar).
2. **2D barcode without zxing** — If zxing is not installed, the cascade remains **heuristic-only** (structural gate + trim coverage). Install `zxingcpp` in the deploy image for stricter 2D behaviour.
3. **Large true 2D symbols** — A legitimate symbol whose crop fails to decode (low DPI, colour bleed) may be suppressed when zxing is enabled. Mitigation: tune DPI in `_zxing_decodes_2d_matrix_in_region` or add a second DPI pass if field reports misses.

## Test map

| Change | Tests |
|--------|--------|
| Trim + zxing gate for 2D | [tests/analyzers/test_barcode.py](../tests/analyzers/test_barcode.py) `test_2d_barcode_suppressed_when_region_covers_trim_excessively` |
| veraPDF metadata | [tests/conformance/test_verapdf_runner.py](../tests/conformance/test_verapdf_runner.py) `test_metadata_out_when_not_configured` |
| NFP + OCR text | [tests/ai/analyzers/regulatory_compliance/test_nfp_detector.py](../tests/ai/analyzers/regulatory_compliance/test_nfp_detector.py) `test_detector_reads_nutrition_panel_from_ocr_regions_only` |
| WCAG / FDA / tobacco sizing | Covered by existing analyzer suites; run full `pytest tests/ai` after substantive edits to `text_metrics`. |

## Golden / corpus fixtures

Scripts under [scripts/audit_preflight_accuracy.py](../scripts/audit_preflight_accuracy.py) may compare `expected_inspection_ids` (e.g. Amalgam fixture). If a reference PDF **stops** emitting `LPDF_BARCODE_014`–`018` after this tightening, refresh that JSON deliberately after verifying on real output.
