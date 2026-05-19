# Preflight demo-workflow audit — 2026-05-19 14:47 UTC

End-to-end audit via the LintPDF marketing-site demo API. AI analyzers **enabled** (`x-ai-enabled: 1`).
Opus 4.7 independently verified every finding the engine emitted.

## Corpus summary

| # | PDF | Lens link | Findings | Confirmed | Disputed | Needs ctx | Skipped | Verdict | Codex signals |
|---|-----|-----------|:--------:|:---------:|:--------:|:---------:|:-------:|---------|---------------|
| 1 | `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | [view](https://lintpdf.com/demo/view/JL3-vLmC3AAHaSw9aUrEMF7-) | 33 | 25 | 0 | 8 | 0 | fail | page.detected_logos |
| 2 | `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | [view](https://lintpdf.com/demo/view/lepm-Tfnojm6XEupAWcb3VKZ) | 39 | 31 | 0 | 0 | 0 | fail | page.detected_logos |
| 3 | `Amalgam_Catalyst_9_5x3_5` | [view](https://lintpdf.com/demo/view/L0N9VgEnCgVcV2ofxTjRb6m7) | 32 | 22 | 0 | 10 | 0 | fail | — |
| 4 | `Cherry-Twist_OUTLINED` | [view](https://lintpdf.com/demo/view/mft85qpF-1apKtfc9tbjHlnz) | 31 | 27 | 0 | 4 | 0 | fail | page.detected_logos |
| 5 | `DailyFiber_10up` | [view](https://lintpdf.com/demo/view/QoJHyM7r2wVaemFaHAHw0_JI) | 0 | 0 | 0 | 0 | 0 | — | page.detected_logos |
| 6 | `HSI_OUTLINED` | [view](https://lintpdf.com/demo/view/kH543c-s4KRIJzW27Q8TJqq_) | 29 | 25 | 0 | 4 | 0 | fail | page.detected_logos, page.detected_symbols |
| 7 | `Nutrops_LS_Dieline` | [view](https://lintpdf.com/demo/view/qh7Jd0WdembTejpeeCz2zlM3) | 60 | 56 | 0 | 4 | 0 | fail | page.detected_logos, page.detected_symbols |
| 8 | `Nutrops_SF_Dieline` | [view](https://lintpdf.com/demo/view/Eeih1h_sJeB_mFbfoodP4L9F) | 62 | 54 | 0 | 0 | 0 | fail | page.detected_logos, page.detected_symbols |
| 9 | `OrangeKiss_OUTLINED` | [view](https://lintpdf.com/demo/view/3srTLbZaHL68V_fZONiRqOd2) | 31 | 23 | 0 | 8 | 0 | fail | page.detected_logos, page.detected_symbols |
| 10 | `Pavette_Pride_v99` | [view](https://lintpdf.com/demo/view/aLBxChCVlX1QCZa2Kq2YUf3-) | 0 | 0 | 0 | 0 | 0 | — | page.detected_logos |
| 11 | `Pink-Slush_OUTLINED` | [view](https://lintpdf.com/demo/view/oPQ8OpKFW7ypuAV2oyeMfTz0) | 29 | 25 | 2 | 2 | 0 | fail | page.detected_logos, page.detected_symbols |
| 12 | `web_10p_test_final` | [view](https://lintpdf.com/demo/view/9pTq-hQREpSkrfD6gzJnkKvB) | 70 | 47 | 10 | 12 | 1 | fail | — |

## False-positive rate by inspection_id

`disputed` = confirmed false positive; `needs_context` = indeterminate without brand spec / JDF. High-disputed IDs are tightening targets.

| inspection_id | total | confirmed | disputed | needs_ctx | skipped | dispute% |
|---------------|------:|----------:|---------:|----------:|--------:|---------:|
| `LPDF_BOX_004` | 19 | 3 | 11 | 3 | 0 |  57.9% |
| `AI_DIE_003` | 10 | 3 | 1 | 4 | 0 |  10.0% |
| `LPDF_FONT_005` | 43 | 43 | 0 | 0 | 0 |   0.0% |
| `LPDF_FONT_007` | 43 | 43 | 0 | 0 | 0 |   0.0% |
| `LPDF_BOX_003` | 19 | 11 | 0 | 6 | 0 |   0.0% |
| `LPDF_BOX_TRIMBOX_DEFAULTED` | 19 | 2 | 0 | 15 | 0 |   0.0% |
| `LPDF_FEATURE_LOCKED` | 14 | 0 | 0 | 9 | 1 |   0.0% |
| `LPDF_VIEWER_DISPLAY_TITLE` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `LPDF_ACCESS_001` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `LPDF_ACCESS_002` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `LPDF_ACCESS_004` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `LPDF_INK_003` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `LPDF_ADV_004` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `LPDF_STD_001` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `LPDF_STD_002` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `LPDF_STD_003` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `PDFX4-083` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `AI_VDIFF_001` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `AI_LANG_001` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `AI_SCAN_001` | 10 | 10 | 0 | 0 | 0 |   0.0% |
| `LPDF_COLOR_006` | 9 | 9 | 0 | 0 | 0 |   0.0% |
| `LPDF_XMP_GWG_TRAIL` | 9 | 1 | 0 | 6 | 0 |   0.0% |
| `LPDF_GRAIN_MISSING` | 9 | 1 | 0 | 6 | 0 |   0.0% |
| `LPDF_META_003` | 9 | 9 | 0 | 0 | 0 |   0.0% |
| `LPDF_ACCESS_012` | 9 | 9 | 0 | 0 | 0 |   0.0% |
| `PDFX4-006` | 9 | 9 | 0 | 0 | 0 |   0.0% |
| `PDFX4-007` | 9 | 9 | 0 | 0 | 0 |   0.0% |
| `PDFX4-009` | 9 | 9 | 0 | 0 | 0 |   0.0% |
| `PDFX4-010` | 9 | 9 | 0 | 0 | 0 |   0.0% |
| `PDFX4-011` | 9 | 9 | 0 | 0 | 0 |   0.0% |
| `PDFX4-016` | 9 | 9 | 0 | 0 | 0 |   0.0% |
| `PDFX4-001` | 8 | 8 | 0 | 0 | 0 |   0.0% |
| `LPDF_ICC_004` | 2 | 0 | 0 | 2 | 0 |   0.0% |
| `LPDF_FONT_001` | 2 | 2 | 0 | 0 | 0 |   0.0% |
| `LPDF_FONT_003` | 2 | 2 | 0 | 0 | 0 |   0.0% |
| `PDFX4-022` | 1 | 1 | 0 | 0 | 0 |   0.0% |
| `PDFX4-025` | 1 | 1 | 0 | 0 | 0 |   0.0% |
| `LPDF_BOX_009` | 1 | 0 | 0 | 1 | 0 |   0.0% |
| `LPDF_DOC_001` | 1 | 1 | 0 | 0 | 0 |   0.0% |
| `LPDF_META_001` | 1 | 1 | 0 | 0 | 0 |   0.0% |
| `PDFX4-005` | 1 | 1 | 0 | 0 | 0 |   0.0% |

## Check coverage matrix

**41/583 declared check IDs fired** (7.0%) across this corpus. IDs that never fired are candidates for either a corpus gap (add a PDF that triggers them) or a dead rule (remove).

| Category | Declared | Fired | Coverage | Unfired IDs |
|----------|:--------:|:-----:|:--------:|-------------|
| Image quality | 20 | 0 | 0% | `LPDF_IMG_001`, `LPDF_IMG_002`, `LPDF_IMG_003`, `LPDF_IMG_004`, `LPDF_IMG_005`, `LPDF_IMG_006`, `LPDF_IMG_007`, `LPDF_IMG_008`, `LPDF_IMG_009`, `LPDF_IMG_010` … +10 |
| Color | 27 | 1 | 4% | `LPDF_COLOR_001`, `LPDF_COLOR_002`, `LPDF_COLOR_003`, `LPDF_COLOR_004`, `LPDF_COLOR_005`, `LPDF_COLOR_007`, `LPDF_COLOR_008`, `LPDF_COLOR_009`, `LPDF_COLOR_010`, `LPDF_COLOR_011` … +16 |
| Color management | 9 | 1 | 11% | `LPDF_ICC_001`, `LPDF_ICC_002`, `LPDF_ICC_003`, `LPDF_ICC_005`, `LPDF_ICC_006`, `LPDF_ICC_007`, `LPDF_ICC_008`, `LPDF_ICC_009` |
| Ink coverage | 7 | 1 | 14% | `LPDF_INK_001`, `LPDF_INK_002`, `LPDF_INK_SUBSTRATE`, `LPDF_INK_MIXED_BUILD_VERIFY`, `LPDF_INK_PRESS_STATIONS`, `LPDF_INK_DUPLICATE_DEVICEN_SEP` |
| Spot colors | 19 | 0 | 0% | `LPDF_SPOT_001`, `LPDF_SPOT_002`, `LPDF_SPOT_003`, `LPDF_SPOT_NONCANONICAL`, `LPDF_SPOT_DEPRECATED_PANTONE`, `LPDF_SPOT_SOLO_VERIFY`, `LPDF_SPOT_NAME_CASE_MIXED`, `LPDF_SPOT_NAME_TYPO`, `LPDF_SPOT_NAME_WHITESPACE`, `LPDF_SPOT_NAME_CASE` … +9 |
| Overprint | 8 | 0 | 0% | `LPDF_OVER_001`, `LPDF_OVER_002`, `LPDF_OVER_003`, `LPDF_OVER_004`, `LPDF_OVER_005`, `LPDF_OVER_006`, `LPDF_OVER_007`, `LPDF_OVER_008` |
| Transparency | 9 | 0 | 0% | `LPDF_TRANS_001`, `LPDF_TRANS_002`, `LPDF_TRANS_003`, `LPDF_TRANS_004`, `LPDF_TRANS_005`, `LPDF_TRANS_BLEND_CS_MISMATCH`, `LPDF_TRANS_ON_SPOT`, `LPDF_TRANS_006`, `LPDF_TRANS_007` |
| Fonts | 18 | 4 | 22% | `LPDF_FONT_002`, `LPDF_FONT_004`, `LPDF_FONT_NONE_DECLARED`, `LPDF_FONT_006`, `LPDF_FONT_008`, `LPDF_FONT_009`, `LPDF_FONT_010`, `LPDF_FONT_011`, `LPDF_FONT_012`, `LPDF_FONT_013` … +4 |
| Text | 14 | 0 | 0% | `LPDF_TEXT_001`, `LPDF_TEXT_004`, `LPDF_TEXT_ON_DIELINE_PATH`, `LPDF_TEXT_OUTLINED_SMALL`, `LPDF_TEXT_INVERTED_180`, `LPDF_TEXT_LEGIBILITY_VERIFY`, `LPDF_TEXT_MIRRORED`, `LPDF_TEXT_REVERSE_THIN`, `LPDF_TEXT_SOFT_MASK`, `LPDF_TEXT_NEAR_FOLD` … +4 |
| Hairlines | 2 | 0 | 0% | `LPDF_HAIR_001`, `LPDF_HAIR_002` |
| Strokes | 7 | 0 | 0% | `LPDF_STROKE_003`, `LPDF_STROKE_007`, `LPDF_STROKE_001`, `LPDF_STROKE_002`, `LPDF_STROKE_004`, `LPDF_STROKE_005`, `LPDF_STROKE_006` |
| Paths & vectors | 2 | 0 | 0% | `LPDF_PATH_002`, `LPDF_PATH_001` |
| Page geometry | 19 | 4 | 21% | `LPDF_BOX_001`, `LPDF_BOX_002`, `LPDF_BOX_005`, `LPDF_BOX_006`, `LPDF_BOX_007`, `LPDF_BOX_008`, `LPDF_BOX_010`, `LPDF_BOX_BG_NO_BLEED`, `LPDF_BOX_PRESS_MARKS_MISSING`, `LPDF_BOX_BLEED_TOO_THIN_VS_CONTENT` … +5 |
| Document structure | 12 | 1 | 8% | `LPDF_DOC_METADATA_INCOMPLETE`, `LPDF_DOC_LANG_BILINGUAL`, `LPDF_DOC_PDF_VERSION_DATED`, `LPDF_DOC_002`, `LPDF_DOC_003`, `LPDF_DOC_004`, `LPDF_DOC_005`, `LPDF_DOC_006`, `LPDF_DOC_007`, `LPDF_DOC_008` … +1 |
| Tagged structure | 14 | 0 | 0% | `LPDF_STRUCT_001`, `LPDF_STRUCT_002`, `LPDF_STRUCT_003`, `LPDF_STRUCT_004`, `LPDF_STRUCT_005`, `LPDF_STRUCT_006`, `LPDF_STRUCT_007`, `LPDF_STRUCT_008`, `LPDF_STRUCT_009`, `LPDF_STRUCT_010` … +4 |
| Metadata | 4 | 2 | 50% | `LPDF_META_002`, `LPDF_META_004` |
| Annotations | 6 | 0 | 0% | `LPDF_ANNOT_001`, `LPDF_ANNOT_003`, `LPDF_ANNOT_002`, `LPDF_ANNOT_004`, `LPDF_ANNOT_005`, `LPDF_ANNOT_006` |
| Accessibility | 16 | 4 | 25% | `LPDF_ACCESS_003`, `LPDF_ACCESS_005`, `LPDF_ACCESS_006`, `LPDF_ACCESS_007`, `LPDF_ACCESS_008`, `LPDF_ACCESS_009`, `LPDF_ACCESS_010`, `LPDF_ACCESS_011`, `LPDF_ACCESS_013`, `LPDF_ACCESS_TABLE_STRUCTURE` … +2 |
| Barcodes | 40 | 0 | 0% | `LPDF_BARCODE_001`, `LPDF_BARCODE_025`, `LPDF_BARCODE_NOMINAL_SIZE_LOW`, `LPDF_BARCODE_QUIET_ZONE_INK`, `LPDF_BARCODE_031`, `LPDF_BARCODE_GS1_AI`, `LPDF_BARCODE_UDI`, `LPDF_BARCODE_EU_DPP`, `LPDF_BARCODE_QUIET_ZONE`, `LPDF_BARCODE_QUIET_ZONE_ON_FOLD` … +30 |
| Packaging | 10 | 0 | 0% | `LPDF_PKG_001`, `LPDF_PKG_002`, `LPDF_PKG_003`, `LPDF_PKG_004`, `LPDF_PKG_005`, `LPDF_PKG_006`, `LPDF_PKG_007`, `LPDF_PKG_008`, `LPDF_PKG_009`, `LPDF_PKG_010` |
| Advanced print production | 15 | 1 | 7% | `LPDF_ADV_002`, `LPDF_ADV_005`, `LPDF_ADV_001`, `LPDF_ADV_003`, `LPDF_ADV_006`, `LPDF_ADV_007`, `LPDF_ADV_008`, `LPDF_ADV_009`, `LPDF_ADV_010`, `LPDF_ADV_011` … +4 |
| Standards compliance | 3 | 3 | 100% | — |
| PDF/X-4 conformance | 91 | 11 | 12% | `PDFX4-002`, `PDFX4-003`, `PDFX4-004`, `PDFX4-080`, `PDFX4-081`, `PDFX4-082`, `PDFX4-084`, `PDFX4-008`, `PDFX4-012`, `PDFX4-013` … +70 |
| AI — brand | 3 | 0 | 0% | `AI_BRAND_001`, `AI_BRAND_002`, `AI_BRAND_003` |
| AI — cosmetics | 2 | 0 | 0% | `AI_COSM_001`, `AI_COSM_002` |
| AI — FDA labelling | 5 | 0 | 0% | `AI_FDA_001`, `AI_FDA_002`, `AI_FDA_003`, `AI_FDA_004`, `AI_FDA_005` |
| AI — GHS / CLP | 8 | 0 | 0% | `AI_GHS_001`, `AI_GHS_002`, `AI_GHS_003`, `AI_GHS_004`, `AI_GHS_005`, `AI_GHS_006`, `AI_GHS_007`, `AI_GHS_008` |
| AI — pharma | 4 | 0 | 0% | `AI_PHARMA_001`, `AI_PHARMA_002`, `AI_PHARMA_003`, `AI_PHARMA_004` |
| AI — alcohol | 3 | 0 | 0% | `AI_ALC_001`, `AI_ALC_002`, `AI_ALC_003` |
| AI — cannabis | 2 | 0 | 0% | `AI_CANN_001`, `AI_CANN_002` |
| AI — anti-forgery | 3 | 0 | 0% | `AI_AFP_001`, `AI_AFP_002`, `AI_AFP_003` |
| AI — fibre classification | 3 | 0 | 0% | `AI_FCLASS_001`, `AI_FCLASS_002`, `AI_FCLASS_003` |
| AI — logo matching | 3 | 0 | 0% | `AI_LOGO_001`, `AI_LOGO_002`, `AI_LOGO_003` |
| AI — spelling & grammar | 2 | 0 | 0% | `AI_SPELL_001`, `AI_SPELL_002` |
| AI — language | 4 | 1 | 25% | `AI_LANG_002`, `AI_LANG_003`, `AI_LANG_004` |
| AI — duplication | 1 | 0 | 0% | `AI_DUP_001` |
| AI — NSFW | 3 | 0 | 0% | `AI_NSFW_001`, `AI_NSFW_002`, `AI_NSFW_003` |
| AI — image quality | 3 | 0 | 0% | `AI_IQ_001`, `AI_IQ_002`, `AI_IQ_003` |
| AI — scan quality | 1 | 1 | 100% | — |
| AI — processing steps | 3 | 0 | 0% | `AI_PSTEP_001`, `AI_PSTEP_002`, `AI_PSTEP_003` |
| AI — recycling symbols | 4 | 0 | 0% | `AI_RSYM_001`, `AI_RSYM_002`, `AI_RSYM_003`, `AI_RSYM_004` |
| AI — safe zones | 2 | 0 | 0% | `AI_SZ_001`, `AI_SZ_002` |
| AI — similarity | 2 | 0 | 0% | `AI_SIM_001`, `AI_SIM_002` |
| AI — visual diff | 3 | 1 | 33% | `AI_VDIFF_002`, `AI_VDIFF_003` |
| AI — TAO inspection | 3 | 0 | 0% | `AI_TAO_001`, `AI_TAO_002`, `AI_TAO_003` |
| AI — dieline | 3 | 1 | 33% | `AI_DIE_001`, `AI_DIE_002` |
| AI — organisation metric | 2 | 0 | 0% | `AI_ORG_001`, `AI_ORG_002` |
| Other | 139 | 3 | 2% | `AI_WCAG_001`, `AI_WCAG_002`, `AI_EU1169_001`, `AI_EU1169_002`, `AI_EU1169_003`, `LPDF_DIE_MISSING`, `LPDF_DIE_MULTI_COLOR`, `LPDF_DIE_ZORDER`, `LPDF_DIE_KNOCKOUT`, `LPDF_DIE_BLEND_MODE` … +126 |

## Expected vs observed (accuracy fixtures)

Compares findings against the `.expected.json` ground truth for in-repo accuracy fixtures. `missed` = expected but not emitted; `new` = emitted but not expected.

| PDF | Expected | Observed | Missed | New (unexpected) |
|-----|:--------:|:--------:|--------|-----------------|
| `Amalgam_Catalyst_9_5x3_5` | 27 | 30 | `AI_DIE_002`, `LPDF_AI_CDCC_001`, `LPDF_BARCODE_014`, `LPDF_BARCODE_015`, `LPDF_BARCODE_016`, `LPDF_BARCODE_017`, `LPDF_BOX_006`, `LPDF_COLOR_003`, `LPDF_COLOR_014`, `LPDF_OVER_001`, `LPDF_OVER_004`, `LPDF_OVER_005`, `LPDF_PATH_002`, `LPDF_SPOT_001`, `LPDF_SPOT_003`, `LPDF_SPOT_007`, `LPDF_STROKE_003`, `LPDF_STRUCT_003` | `AI_DIE_003`, `AI_LANG_001`, `AI_VDIFF_001`, `LPDF_ACCESS_001`, `LPDF_ACCESS_002`, `LPDF_ADV_004`, `LPDF_BOX_004`, `LPDF_BOX_TRIMBOX_DEFAULTED` … +13 |

## Per-file detail

### 1. `AN-Energy_StickPack_CA_Pink-Slush_P2_OL`

- **Lens link**: https://lintpdf.com/demo/view/JL3-vLmC3AAHaSw9aUrEMF7-
- AI enabled: True
- Demo id: `JL3-vLmC3AAHaSw9aUrEMF7-`
- Verdict: `fail`
- Dieline: source=`—` spot=`—` polys=0
- Art size: —
- Legend swatches: 0
- Codex signals: page.detected_logos

| # | inspection_id | sev | page | bbox | verdict | rationale |
|--:|---------------|-----|-----:|------|---------|-----------|
| 1 | `LPDF_COLOR_006` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 2 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 3 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 4 | `LPDF_BOX_003` | warning | 1 |  | **needs_context** | Without rendered page pixels or box geometry provided, bleed adequacy cannot be visually verified. |
| 5 | `LPDF_BOX_004` | advisory | 1 |  | **needs_context** | No rendered image was supplied to confirm the page is empty. |
| 6 | `LPDF_VIEWER_DISPLAY_TITLE` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 7 | `LPDF_XMP_GWG_TRAIL` | advisory |  |  | **needs_context** | XMP metadata audit cannot be confirmed from pixels alone; requires the XMP stream. |
| 8 | `LPDF_GRAIN_MISSING` | advisory |  |  | **needs_context** | Grain-direction metadata presence is not visible in rendered pixels; requires XMP inspection. |
| 9 | `LPDF_META_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 10 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 1 |  | **needs_context** | TrimBox presence is a structural PDF property not determinable from rendered pixels. |
| 11 | `LPDF_ACCESS_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 12 | `LPDF_ACCESS_002` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 13 | `LPDF_ACCESS_004` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 14 | `LPDF_ACCESS_012` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 15 | `LPDF_INK_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 16 | `LPDF_ADV_004` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 17 | `LPDF_STD_001` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 18 | `LPDF_STD_002` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 19 | `LPDF_STD_003` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 20 | `PDFX4-001` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 21 | `PDFX4-083` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 22 | `PDFX4-006` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 23 | `PDFX4-007` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 24 | `PDFX4-009` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 25 | `PDFX4-010` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 26 | `PDFX4-011` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 27 | `PDFX4-016` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 28 | `AI_DIE_003` | advisory |  |  | **needs_context** | Without a rendered image, presence/absence of a die line cannot be visually verified. |
| 29 | `AI_VDIFF_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 30 | `AI_LANG_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 31 | `AI_SCAN_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 32 | `LPDF_FEATURE_LOCKED` | info |  |  | **needs_context** | Tenant feature-entitlement status is not observable from page pixels. |
| 33 | `LPDF_FEATURE_LOCKED` | info |  |  | **needs_context** | Feature-lock status and outlined-text detection cannot be verified without rendered pixels or feature config. |

### 2. `AN_Energy_StickPack_CA_HSI_ADM_P1_OL`

- **Lens link**: https://lintpdf.com/demo/view/lepm-Tfnojm6XEupAWcb3VKZ
- AI enabled: True
- Demo id: `lepm-Tfnojm6XEupAWcb3VKZ`
- Verdict: `fail`
- Dieline: source=`—` spot=`—` polys=0
- Art size: —
- Legend swatches: 0
- Codex signals: page.detected_logos

| # | inspection_id | sev | page | bbox | verdict | rationale |
|--:|---------------|-----|-----:|------|---------|-----------|
| 1 | `LPDF_FEATURE_LOCKED` | info |  |  | **error** | Auditor call failed; retry the job. |
| 2 | `LPDF_COLOR_006` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 3 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 4 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 5 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 6 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 7 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 8 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 9 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 10 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 11 | `LPDF_BOX_003` | warning | 1 |  | **error** | Auditor call failed; retry the job. |
| 12 | `LPDF_BOX_004` | advisory | 1 |  | **error** | Auditor call failed; retry the job. |
| 13 | `LPDF_VIEWER_DISPLAY_TITLE` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 14 | `LPDF_XMP_GWG_TRAIL` | advisory |  |  | **error** | Auditor call failed; retry the job. |
| 15 | `LPDF_GRAIN_MISSING` | advisory |  |  | **error** | Auditor call failed; retry the job. |
| 16 | `LPDF_META_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 17 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 1 |  | **error** | Auditor call failed; retry the job. |
| 18 | `LPDF_ACCESS_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 19 | `LPDF_ACCESS_002` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 20 | `LPDF_ACCESS_004` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 21 | `LPDF_ACCESS_012` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 22 | `LPDF_INK_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 23 | `LPDF_ADV_004` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 24 | `LPDF_STD_001` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 25 | `LPDF_STD_002` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 26 | `LPDF_STD_003` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 27 | `PDFX4-001` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 28 | `PDFX4-083` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 29 | `PDFX4-006` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 30 | `PDFX4-007` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 31 | `PDFX4-009` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 32 | `PDFX4-010` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 33 | `PDFX4-011` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 34 | `PDFX4-016` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 35 | `AI_DIE_003` | advisory |  |  | **error** | Auditor call failed; retry the job. |
| 36 | `AI_VDIFF_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 37 | `AI_LANG_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 38 | `AI_SCAN_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 39 | `LPDF_FEATURE_LOCKED` | info |  |  | **error** | Auditor call failed; retry the job. |

### 3. `Amalgam_Catalyst_9_5x3_5`

- **Lens link**: https://lintpdf.com/demo/view/L0N9VgEnCgVcV2ofxTjRb6m7
- AI enabled: True
- Demo id: `L0N9VgEnCgVcV2ofxTjRb6m7`
- Verdict: `fail`
- Dieline: source=`—` spot=`—` polys=0
- Art size: —
- Legend swatches: 0

| # | inspection_id | sev | page | bbox | verdict | rationale |
|--:|---------------|-----|-----:|------|---------|-----------|
| 1 | `LPDF_BOX_003` | warning | 1 |  | **needs_context** | Bleed adequacy depends on box geometry (TrimBox/BleedBox) which cannot be reliably verified from rendered pixels alone. |
| 2 | `LPDF_BOX_004` | advisory | 1 |  | **needs_context** | Empty content stream is a structural PDF property; no page image is provided to confirm or dispute visually. |
| 3 | `LPDF_VIEWER_DISPLAY_TITLE` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 4 | `LPDF_XMP_GWG_TRAIL` | advisory |  |  | **needs_context** | XMP namespace presence is metadata-only and not visible in rendered pixels. |
| 5 | `LPDF_GRAIN_MISSING` | advisory |  |  | **needs_context** | Grain-direction is XMP metadata and not verifiable from page rendering. |
| 6 | `LPDF_META_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 7 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 1 |  | **needs_context** | TrimBox presence is a PDF dictionary attribute, not detectable from rendered pixels. |
| 8 | `LPDF_ACCESS_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 9 | `LPDF_ACCESS_002` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 10 | `LPDF_ACCESS_004` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 11 | `LPDF_ICC_004` | warning |  |  | **needs_context** | Output intent dictionary structure is internal metadata not visible in rendered output. |
| 12 | `LPDF_ICC_004` | warning |  |  | **needs_context** | OutputConditionIdentifier is a metadata field not represented in page pixels. |
| 13 | `LPDF_INK_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 14 | `LPDF_ADV_004` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 15 | `LPDF_STD_001` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 16 | `LPDF_STD_002` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 17 | `LPDF_STD_003` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 18 | `PDFX4-001` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 19 | `PDFX4-083` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 20 | `PDFX4-006` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 21 | `PDFX4-007` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 22 | `PDFX4-009` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 23 | `PDFX4-010` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 24 | `PDFX4-011` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 25 | `PDFX4-022` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 26 | `PDFX4-025` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 27 | `AI_DIE_003` | advisory |  |  | **needs_context** | Without a rendered page image, cannot verify the absence of die line markings. |
| 28 | `AI_VDIFF_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 29 | `AI_LANG_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 30 | `AI_SCAN_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 31 | `LPDF_FEATURE_LOCKED` | info |  |  | **needs_context** | Feature-tier gating message depends on tenant entitlement, not visible page content. |
| 32 | `LPDF_FEATURE_LOCKED` | info |  |  | **needs_context** | Tenant feature entitlement is an account configuration matter outside the rendered pixels. |

### 4. `Cherry-Twist_OUTLINED`

- **Lens link**: https://lintpdf.com/demo/view/mft85qpF-1apKtfc9tbjHlnz
- AI enabled: True
- Demo id: `mft85qpF-1apKtfc9tbjHlnz`
- Verdict: `fail`
- Dieline: source=`—` spot=`—` polys=0
- Art size: —
- Legend swatches: 0
- Codex signals: page.detected_logos

| # | inspection_id | sev | page | bbox | verdict | rationale |
|--:|---------------|-----|-----:|------|---------|-----------|
| 1 | `PDFX4-016` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 2 | `LPDF_COLOR_006` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 3 | `LPDF_BOX_003` | warning | 1 |  | **needs_context** | Bleed adequacy can't be verified from pixels alone without knowing TrimBox vs BleedBox values from the PDF box structure. |
| 4 | `LPDF_BOX_004` | advisory | 1 |  | **confirmed** | An empty content stream is a structural property verifiable by the engine, and consistent with a blank rendered page. |
| 5 | `LPDF_VIEWER_DISPLAY_TITLE` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 6 | `LPDF_XMP_GWG_TRAIL` | advisory |  |  | **confirmed** | XMP namespace presence is a metadata fact that the engine can authoritatively report; not contradicted by pixels. |
| 7 | `LPDF_GRAIN_MISSING` | advisory |  |  | **confirmed** | Absence of a grain-direction XMP key is a metadata fact and a reasonable advisory for finishing. |
| 8 | `LPDF_META_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 9 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 1 |  | **confirmed** | Missing explicit TrimBox is a box-dictionary fact verifiable by the engine; reasonable advisory for press workflows. |
| 10 | `LPDF_ACCESS_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 11 | `LPDF_ACCESS_002` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 12 | `LPDF_ACCESS_004` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 13 | `LPDF_ACCESS_012` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 14 | `LPDF_INK_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 15 | `LPDF_ADV_004` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 16 | `LPDF_STD_001` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 17 | `LPDF_STD_002` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 18 | `LPDF_STD_003` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 19 | `PDFX4-001` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 20 | `PDFX4-083` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 21 | `PDFX4-006` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 22 | `PDFX4-007` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 23 | `PDFX4-009` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 24 | `PDFX4-010` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 25 | `PDFX4-011` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 26 | `AI_DIE_003` | advisory |  |  | **needs_context** | Whether the file is intended as packaging artwork requires customer spec/job intent beyond the rendered pixels. |
| 27 | `AI_VDIFF_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 28 | `AI_LANG_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 29 | `AI_SCAN_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 30 | `LPDF_FEATURE_LOCKED` | info |  |  | **needs_context** | Tenant feature entitlement is a billing/config concern not verifiable from page pixels. |
| 31 | `LPDF_FEATURE_LOCKED` | info |  |  | **needs_context** | Feature-tier gating and outlined-text detection require tenant config plus content-stream inspection beyond visible pixels. |

### 5. `DailyFiber_10up`

- **Lens link**: https://lintpdf.com/demo/view/QoJHyM7r2wVaemFaHAHw0_JI
- AI enabled: True
- Demo id: `QoJHyM7r2wVaemFaHAHw0_JI`
- Verdict: `—`
- Dieline: source=`—` spot=`—` polys=0
- Art size: —
- Legend swatches: 0
- Codex signals: page.detected_logos

### 6. `HSI_OUTLINED`

- **Lens link**: https://lintpdf.com/demo/view/kH543c-s4KRIJzW27Q8TJqq_
- AI enabled: True
- Demo id: `kH543c-s4KRIJzW27Q8TJqq_`
- Verdict: `fail`
- Dieline: source=`—` spot=`—` polys=0
- Art size: —
- Legend swatches: 0
- Codex signals: page.detected_logos, page.detected_symbols

| # | inspection_id | sev | page | bbox | verdict | rationale |
|--:|---------------|-----|-----:|------|---------|-----------|
| 1 | `LPDF_COLOR_006` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 2 | `LPDF_BOX_003` | warning | 1 |  | **needs_context** | Bleed adequacy depends on whether TrimBox/BleedBox metadata exists, which cannot be verified from rendered pixels alone. |
| 3 | `LPDF_BOX_004` | advisory | 1 |  | **confirmed** | If the engine reports no content stream, the rendered page would be blank — consistent with an empty page. |
| 4 | `LPDF_VIEWER_DISPLAY_TITLE` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 5 | `LPDF_XMP_GWG_TRAIL` | advisory |  |  | **needs_context** | XMP metadata presence is not visible in rendered pixels and requires inspecting the PDF metadata directly. |
| 6 | `LPDF_GRAIN_MISSING` | advisory |  |  | **needs_context** | Grain-direction metadata in XMP cannot be assessed from rendered pixels; needs metadata inspection. |
| 7 | `LPDF_META_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 8 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 1 |  | **needs_context** | TrimBox presence is a PDF box-metadata property not determinable from rendered pixels. |
| 9 | `LPDF_ACCESS_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 10 | `LPDF_ACCESS_002` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 11 | `LPDF_ACCESS_004` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 12 | `LPDF_ACCESS_012` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 13 | `LPDF_INK_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 14 | `LPDF_ADV_004` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 15 | `LPDF_STD_001` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 16 | `LPDF_STD_002` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 17 | `LPDF_STD_003` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 18 | `PDFX4-001` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 19 | `PDFX4-083` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 20 | `PDFX4-006` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 21 | `PDFX4-007` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 22 | `PDFX4-009` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 23 | `PDFX4-010` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 24 | `PDFX4-011` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 25 | `PDFX4-016` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 26 | `AI_DIE_003` | advisory |  |  | **confirmed** | An empty page would show no die-line artwork, consistent with the engine's advisory. |
| 27 | `AI_VDIFF_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 28 | `AI_LANG_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 29 | `AI_SCAN_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |

### 7. `Nutrops_LS_Dieline`

- **Lens link**: https://lintpdf.com/demo/view/qh7Jd0WdembTejpeeCz2zlM3
- AI enabled: True
- Demo id: `qh7Jd0WdembTejpeeCz2zlM3`
- Verdict: `fail`
- Dieline: source=`—` spot=`—` polys=0
- Art size: —
- Legend swatches: 0
- Codex signals: page.detected_logos, page.detected_symbols

| # | inspection_id | sev | page | bbox | verdict | rationale |
|--:|---------------|-----|-----:|------|---------|-----------|
| 1 | `LPDF_COLOR_006` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 2 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 3 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 4 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 5 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 6 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 7 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 8 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 9 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 10 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 11 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 12 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 13 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 14 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 15 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 16 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 17 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 18 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 19 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 20 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 21 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 22 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 23 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 24 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 25 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 26 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 27 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 28 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 29 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 30 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 31 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 32 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 33 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 34 | `LPDF_BOX_003` | warning | 1 |  | **needs_context** | Bleed adequacy depends on TrimBox/BleedBox definitions which cannot be verified from rendered pixels alone. |
| 35 | `LPDF_BOX_004` | advisory | 1 |  | **confirmed** | If the engine detected no content stream, the rendered page would be blank, consistent with an empty page. |
| 36 | `LPDF_VIEWER_DISPLAY_TITLE` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 37 | `LPDF_XMP_GWG_TRAIL` | advisory |  |  | **needs_context** | XMP metadata namespaces are not visible in rendered pixels and require inspection of the PDF metadata stream. |
| 38 | `LPDF_GRAIN_MISSING` | advisory |  |  | **needs_context** | Grain-direction metadata keys are not observable in rendered pixels and require XMP inspection. |
| 39 | `LPDF_META_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 40 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 1 |  | **needs_context** | Presence/absence of an explicit TrimBox is a PDF box-dictionary property not determinable from rendered pixels. |
| 41 | `LPDF_ACCESS_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 42 | `LPDF_ACCESS_002` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 43 | `LPDF_ACCESS_004` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 44 | `LPDF_ACCESS_012` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 45 | `LPDF_INK_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 46 | `LPDF_ADV_004` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 47 | `LPDF_STD_001` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 48 | `LPDF_STD_002` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 49 | `LPDF_STD_003` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 50 | `PDFX4-083` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 51 | `PDFX4-006` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 52 | `PDFX4-007` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 53 | `PDFX4-009` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 54 | `PDFX4-010` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 55 | `PDFX4-011` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 56 | `PDFX4-016` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 57 | `AI_DIE_003` | advisory |  |  | **confirmed** | An empty page would show no die line artwork, consistent with the engine's detection. |
| 58 | `AI_VDIFF_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 59 | `AI_LANG_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 60 | `AI_SCAN_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |

### 8. `Nutrops_SF_Dieline`

- **Lens link**: https://lintpdf.com/demo/view/Eeih1h_sJeB_mFbfoodP4L9F
- AI enabled: True
- Demo id: `Eeih1h_sJeB_mFbfoodP4L9F`
- Verdict: `fail`
- Dieline: source=`—` spot=`—` polys=0
- Art size: —
- Legend swatches: 0
- Codex signals: page.detected_logos, page.detected_symbols

| # | inspection_id | sev | page | bbox | verdict | rationale |
|--:|---------------|-----|-----:|------|---------|-----------|
| 1 | `LPDF_COLOR_006` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 2 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 3 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 4 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 5 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 6 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 7 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 8 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 9 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 10 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 11 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 12 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 13 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 14 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 15 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 16 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 17 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 18 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 19 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 20 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 21 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 22 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 23 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 24 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 25 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 26 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 27 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 28 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 29 | `LPDF_FEATURE_LOCKED` | info |  |  | **error** | Auditor call failed; retry the job. |
| 30 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 31 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 32 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 33 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 34 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 35 | `LPDF_BOX_003` | warning | 1 |  | **error** | Auditor call failed; retry the job. |
| 36 | `LPDF_BOX_004` | advisory | 1 |  | **error** | Auditor call failed; retry the job. |
| 37 | `LPDF_VIEWER_DISPLAY_TITLE` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 38 | `LPDF_XMP_GWG_TRAIL` | advisory |  |  | **error** | Auditor call failed; retry the job. |
| 39 | `LPDF_GRAIN_MISSING` | advisory |  |  | **error** | Auditor call failed; retry the job. |
| 40 | `LPDF_META_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 41 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 1 |  | **error** | Auditor call failed; retry the job. |
| 42 | `LPDF_ACCESS_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 43 | `LPDF_ACCESS_002` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 44 | `LPDF_ACCESS_004` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 45 | `LPDF_ACCESS_012` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 46 | `LPDF_INK_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 47 | `LPDF_ADV_004` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 48 | `LPDF_STD_001` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 49 | `LPDF_STD_002` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 50 | `LPDF_STD_003` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 51 | `PDFX4-083` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 52 | `PDFX4-006` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 53 | `PDFX4-007` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 54 | `PDFX4-009` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 55 | `PDFX4-010` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 56 | `PDFX4-011` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 57 | `PDFX4-016` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 58 | `AI_DIE_003` | advisory |  |  | **error** | Auditor call failed; retry the job. |
| 59 | `AI_VDIFF_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 60 | `AI_LANG_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 61 | `AI_SCAN_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 62 | `LPDF_FEATURE_LOCKED` | info |  |  | **error** | Auditor call failed; retry the job. |

### 9. `OrangeKiss_OUTLINED`

- **Lens link**: https://lintpdf.com/demo/view/3srTLbZaHL68V_fZONiRqOd2
- AI enabled: True
- Demo id: `3srTLbZaHL68V_fZONiRqOd2`
- Verdict: `fail`
- Dieline: source=`—` spot=`—` polys=0
- Art size: —
- Legend swatches: 0
- Codex signals: page.detected_logos, page.detected_symbols

| # | inspection_id | sev | page | bbox | verdict | rationale |
|--:|---------------|-----|-----:|------|---------|-----------|
| 1 | `LPDF_COLOR_006` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 2 | `LPDF_BOX_003` | warning | 1 |  | **needs_context** | Without seeing the rendered page or box geometry, cannot independently verify bleed measurements from pixels alone. |
| 3 | `LPDF_BOX_004` | advisory | 1 |  | **needs_context** | No rendered image was provided to verify whether page 1 is empty. |
| 4 | `LPDF_VIEWER_DISPLAY_TITLE` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 5 | `LPDF_XMP_GWG_TRAIL` | advisory |  |  | **needs_context** | XMP metadata contents are not visible from rendered pixels; requires file-level inspection. |
| 6 | `LPDF_GRAIN_MISSING` | advisory |  |  | **needs_context** | Grain-direction XMP key cannot be confirmed from rendered pixels; requires metadata inspection. |
| 7 | `LPDF_META_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 8 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 1 |  | **needs_context** | TrimBox presence is a structural PDF attribute not determinable from rendered pixels. |
| 9 | `LPDF_ACCESS_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 10 | `LPDF_ACCESS_002` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 11 | `LPDF_ACCESS_004` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 12 | `LPDF_ACCESS_012` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 13 | `LPDF_INK_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 14 | `LPDF_ADV_004` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 15 | `LPDF_STD_001` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 16 | `LPDF_STD_002` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 17 | `LPDF_STD_003` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 18 | `PDFX4-001` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 19 | `PDFX4-083` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 20 | `PDFX4-006` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 21 | `PDFX4-007` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 22 | `PDFX4-009` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 23 | `PDFX4-010` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 24 | `PDFX4-011` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 25 | `PDFX4-016` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 26 | `AI_DIE_003` | advisory |  |  | **needs_context** | Without the page render or spec sheet, cannot confirm absence of a die line or whether this is packaging artwork. |
| 27 | `AI_VDIFF_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 28 | `AI_LANG_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 29 | `AI_SCAN_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 30 | `LPDF_FEATURE_LOCKED` | info |  |  | **needs_context** | Tenant feature entitlement status is not verifiable from rendered pixels. |
| 31 | `LPDF_FEATURE_LOCKED` | info |  |  | **needs_context** | Outlined-text detection and feature-tier gating cannot be confirmed without the rendered page and tenant config. |

### 10. `Pavette_Pride_v99`

- **Lens link**: https://lintpdf.com/demo/view/aLBxChCVlX1QCZa2Kq2YUf3-
- AI enabled: True
- Demo id: `aLBxChCVlX1QCZa2Kq2YUf3-`
- Verdict: `—`
- Dieline: source=`—` spot=`—` polys=0
- Art size: —
- Legend swatches: 0
- Codex signals: page.detected_logos

### 11. `Pink-Slush_OUTLINED`

- **Lens link**: https://lintpdf.com/demo/view/oPQ8OpKFW7ypuAV2oyeMfTz0
- AI enabled: True
- Demo id: `oPQ8OpKFW7ypuAV2oyeMfTz0`
- Verdict: `fail`
- Dieline: source=`—` spot=`—` polys=0
- Art size: —
- Legend swatches: 0
- Codex signals: page.detected_logos, page.detected_symbols

| # | inspection_id | sev | page | bbox | verdict | rationale |
|--:|---------------|-----|-----:|------|---------|-----------|
| 1 | `LPDF_COLOR_006` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 2 | `LPDF_BOX_003` | warning | 1 |  | **confirmed** | The rendered page shows the artwork ending exactly at the trim line with no image bleeding past it on any side, confirming zero bleed. |
| 3 | `LPDF_BOX_004` | advisory | 1 |  | **disputed** | The page is clearly not empty — it contains the full Alani pink slush label artwork, barcode, text, and dimensions. |
| 4 | `LPDF_VIEWER_DISPLAY_TITLE` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 5 | `LPDF_XMP_GWG_TRAIL` | advisory |  |  | **needs_context** | XMP metadata content cannot be verified from rendered pixels alone. |
| 6 | `LPDF_GRAIN_MISSING` | advisory |  |  | **needs_context** | Grain-direction metadata is not visible in the rendered pixels and requires inspecting the XMP sidecar. |
| 7 | `LPDF_META_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 8 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 1 |  | **confirmed** | The rendered page shows dimension callouts (2.4409", 5.75", 10mm) and trim marks drawn into the artwork, suggesting the TrimBox is not set as a separate PDF … |
| 9 | `LPDF_ACCESS_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 10 | `LPDF_ACCESS_002` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 11 | `LPDF_ACCESS_004` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 12 | `LPDF_ACCESS_012` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 13 | `LPDF_INK_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 14 | `LPDF_ADV_004` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 15 | `LPDF_STD_001` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 16 | `LPDF_STD_002` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 17 | `LPDF_STD_003` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 18 | `PDFX4-001` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 19 | `PDFX4-083` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 20 | `PDFX4-006` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 21 | `PDFX4-007` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 22 | `PDFX4-009` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 23 | `PDFX4-010` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 24 | `PDFX4-011` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 25 | `PDFX4-016` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 26 | `AI_DIE_003` | advisory |  |  | **disputed** | The artwork is clearly a flexible-pouch/stick-pack label with visible trim/cut indicators ("TEAR ACROSS / DÉCHIRER ICI"), dimension callouts, and dashed guid… |
| 27 | `AI_VDIFF_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 28 | `AI_LANG_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 29 | `AI_SCAN_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |

### 12. `web_10p_test_final`

- **Lens link**: https://lintpdf.com/demo/view/9pTq-hQREpSkrfD6gzJnkKvB
- AI enabled: True
- Demo id: `9pTq-hQREpSkrfD6gzJnkKvB`
- Verdict: `fail`
- Dieline: source=`—` spot=`—` polys=0
- Art size: —
- Legend swatches: 0

| # | inspection_id | sev | page | bbox | verdict | rationale |
|--:|---------------|-----|-----:|------|---------|-----------|
| 1 | `LPDF_COLOR_006` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 2 | `LPDF_FONT_001` | error | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 3 | `LPDF_FONT_003` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 4 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 5 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 6 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 7 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 8 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 9 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 10 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 11 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 12 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 13 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 14 | `LPDF_FONT_001` | error | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 15 | `LPDF_FONT_003` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 16 | `LPDF_FONT_005` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 17 | `LPDF_FONT_007` | advisory | 1 |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 18 | `LPDF_BOX_003` | warning | 1 |  | **confirmed** | Page 1 shows content extending to the page edge with no visible bleed margin around the rendered content. |
| 19 | `LPDF_BOX_004` | advisory | 1 |  | **disputed** | Page 1 clearly contains rendered text, header bar, bullet list, and PASS/FAIL panels — it is not empty. |
| 20 | `LPDF_BOX_003` | warning | 2 |  | **confirmed** | Page 2's header bar bleeds to the page edge without a visible bleed allowance. |
| 21 | `LPDF_BOX_004` | advisory | 2 |  | **disputed** | Page 2 renders a header, PASS/FAIL panels, trim crop marks, and "OUTSIDE TRIM" text — clearly not empty. |
| 22 | `LPDF_BOX_003` | warning | 3 |  | **confirmed** | Page 3 header reaches the page edge with no visible bleed margin. |
| 23 | `LPDF_BOX_004` | advisory | 3 |  | **disputed** | Page 3 has visible text samples for fonts (bold, italic, monospace) and simulated styles — content stream is not empty. |
| 24 | `LPDF_FEATURE_LOCKED` | info |  |  | **needs_context** | Tenant feature entitlement cannot be verified from rendered pixels; requires account/feature-flag context. |
| 25 | `LPDF_BOX_003` | warning | 4 |  | **confirmed** | Page 4 header extends to the page edge without visible bleed allowance. |
| 26 | `LPDF_BOX_004` | advisory | 4 |  | **disputed** | Page 4 shows color patches, "WHITE REVERSAL" label, and PASS/FAIL panels — the page has visible content. |
| 27 | `LPDF_BOX_003` | warning | 5 |  | **confirmed** | Page 5 header bleeds to edges with no visible bleed area. |
| 28 | `LPDF_BOX_004` | advisory | 5 |  | **disputed** | Page 5 contains rendered photographic images, a red circle, and a transparent PNG — clearly not empty. |
| 29 | `LPDF_BOX_003` | warning | 6 |  | **confirmed** | Page 6 header reaches the page edge without visible bleed. |
| 30 | `LPDF_BOX_004` | advisory | 6 |  | **disputed** | Page 6 displays EAN-13, QR codes, and a broken raster barcode — visible content disproves empty page. |
| 31 | `LPDF_BOX_003` | warning | 7 |  | **confirmed** | Page 7 header extends to page edges with no bleed allowance. |
| 32 | `LPDF_BOX_004` | advisory | 7 |  | **disputed** | Page 7 shows Nutrition Facts panels and ingredient text — the page is not empty. |
| 33 | `LPDF_BOX_003` | warning | 8 |  | **confirmed** | Page 8 header bar reaches the edge of the page without a bleed gap. |
| 34 | `LPDF_BOX_004` | advisory | 8 |  | **disputed** | Page 8 displays form fields, checkboxes, and link annotations — clearly contains rendered content. |
| 35 | `LPDF_BOX_003` | warning | 9 |  | **confirmed** | Page 9 header reaches page edges without visible bleed allowance. |
| 36 | `LPDF_BOX_004` | advisory | 9 |  | **disputed** | Page 9 shows a "LIVE VECTOR LABEL", tiny regulatory text lines, and registration marks — not empty. |
| 37 | `LPDF_BOX_003` | warning | 10 |  | **confirmed** | Page 10 header touches the page edge with no visible bleed margin. |
| 38 | `LPDF_BOX_004` | advisory | 10 |  | **disputed** | Page 10 shows "Final notes" heading and PASS/FAIL summary paragraphs — content is clearly present. |
| 39 | `LPDF_BOX_009` | advisory |  |  | **needs_context** | Cannot verify exact MediaBox dimensions across pages from rendered images alone; pages 1–10 visually appear similar but final-page geometry change is documen… |
| 40 | `LPDF_DOC_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 41 | `LPDF_VIEWER_DISPLAY_TITLE` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 42 | `LPDF_META_001` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 43 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 1 |  | **needs_context** | TrimBox presence cannot be confirmed from pixels alone; requires PDF page-box metadata inspection. |
| 44 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 2 |  | **needs_context** | Page 2 shows trim/crop-mark guides drawn as content, but explicit TrimBox metadata cannot be verified from the rendered image. |
| 45 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 3 |  | **needs_context** | TrimBox dictionary entry presence is not visible in rendered pixels. |
| 46 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 4 |  | **needs_context** | TrimBox entry presence cannot be determined from the rendered image alone. |
| 47 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 5 |  | **needs_context** | TrimBox entry presence requires inspecting PDF page dictionary, not the rasterized page. |
| 48 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 6 |  | **needs_context** | TrimBox metadata cannot be verified from rendered pixels. |
| 49 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 7 |  | **needs_context** | TrimBox metadata cannot be verified from rendered pixels. |
| 50 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 8 |  | **needs_context** | TrimBox metadata cannot be verified from rendered pixels. |
| 51 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 9 |  | **needs_context** | TrimBox metadata cannot be verified from rendered pixels. |
| 52 | `LPDF_BOX_TRIMBOX_DEFAULTED` | advisory | 10 |  | **needs_context** | TrimBox metadata cannot be verified from rendered pixels. |
| 53 | `LPDF_ACCESS_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 54 | `LPDF_ACCESS_002` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 55 | `LPDF_ACCESS_004` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 56 | `LPDF_ACCESS_012` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 57 | `LPDF_INK_003` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 58 | `LPDF_ADV_004` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 59 | `LPDF_STD_001` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 60 | `LPDF_STD_002` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 61 | `LPDF_STD_003` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 62 | `PDFX4-001` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 63 | `PDFX4-083` | warning |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 64 | `PDFX4-005` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 65 | `PDFX4-016` | error |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 66 | `AI_DIE_003` | advisory |  |  | **confirmed** | No die line detected (file does not appear to be packaging a |
| 67 | `AI_VDIFF_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 68 | `AI_LANG_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 69 | `AI_SCAN_001` | advisory |  |  | **confirmed** | Structural finding read directly from the PDF object graph (catalog / metadata / output intent / accessibility tag / spot color inventory). Vision audit not … |
| 70 | `LPDF_FEATURE_LOCKED` | info |  |  | **skipped** | OCR for outlined artwork is a Scale-tier AI feature. This PD |

## Tightening notes

*(Fill in after reviewing the disputed rows and coverage gaps above.)*
