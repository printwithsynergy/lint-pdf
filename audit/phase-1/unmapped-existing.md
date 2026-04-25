# Phase 1.3 — Unmapped existing checks

**Generated:** 2026-04-24
**Source:** all `inspection_id`s in `audit/phase-0/existing-checks.json` that did NOT match any Tier 1-5 gap-list entry in `audit/phase-1/gap-mapping.json`.

**Total:** 311 of 373 (83%).

Per the playbook (§1.3), each row needs an operator decision: **keep**, **rename to gap taxonomy**, or **deprecate**. Default recommendation noted inline; operator overrides via the Q&A gate.

## Categories

| Category | Count | Notable IDs |
|---|---:|---|
| `ai_color_compliance` | 38 | `AI_BRAND_003, LPDF_AI_DIEL_002, LPDF_ECG_001, LPDF_ECG_002, LPDF_ECG_003` |
| `barcodes` | 28 | `LPDF_BARCODE_001, LPDF_BARCODE_004, LPDF_BARCODE_005, LPDF_BARCODE_006, LPDF_BARCODE_007` |
| `ai_barcode` | 25 | `LPDF_BCQM_001, LPDF_BCQM_002, LPDF_BCQM_003, LPDF_BCQM_004, LPDF_BCV_001` |
| `color` | 17 | `LPDF_COLOR_002, LPDF_COLOR_003, LPDF_COLOR_007, LPDF_COLOR_008, LPDF_COLOR_009` |
| `advanced` | 14 | `LPDF_ADV_001, LPDF_ADV_002, LPDF_ADV_003, LPDF_ADV_004, LPDF_ADV_006` |
| `strokes` | 11 | `LPDF_PATH_001, LPDF_STROKE_002, LPDF_STROKE_003, LPDF_STROKE_004, LPDF_STROKE_005` |
| `ai_regulatory_compliance` | 10 | `AI_GHS_002, AI_GHS_003, AI_GHS_004, AI_GHS_005, AI_GHS_006` |
| `packaging` | 10 | `LPDF_PKG_001, LPDF_PKG_002, LPDF_PKG_003, LPDF_PKG_004, LPDF_PKG_005` |
| `structure` | 10 | `LPDF_STRUCT_005, LPDF_STRUCT_006, LPDF_STRUCT_007, LPDF_STRUCT_008, LPDF_STRUCT_009` |
| `fonts` | 9 | `LPDF_FONT_003, LPDF_FONT_006, LPDF_FONT_007, LPDF_FONT_009, LPDF_FONT_010` |
| `color_management` | 9 | `LPDF_ICC_001, LPDF_ICC_002, LPDF_ICC_003, LPDF_ICC_004, LPDF_ICC_005` |
| `image` | 9 | `LPDF_IMG_002, LPDF_IMG_004, LPDF_IMG_005, LPDF_IMG_006, LPDF_IMG_007` |
| `spot_colors` | 8 | `LPDF_SPOT_004, LPDF_SPOT_005, LPDF_SPOT_006, LPDF_SPOT_007, LPDF_SPOT_008` |
| `ai_other` | 7 | `AI_LANG_002, AI_SPELL_002, AI_SZ_002, LPDF_AI_BAND_001, LPDF_AI_CAST_001` |
| `document` | 7 | `LPDF_DOC_002, LPDF_DOC_003, LPDF_DOC_004, LPDF_DOC_005, LPDF_DOC_006` |
| `accessibility` | 6 | `LPDF_ACCESS_007, LPDF_ACCESS_008, LPDF_ACCESS_009, LPDF_ACCESS_010, LPDF_ACCESS_011` |
| `overprint` | 6 | `LPDF_OVER_003, LPDF_OVER_004, LPDF_OVER_005, LPDF_OVER_006, LPDF_OVER_007` |
| `ai_image_analysis` | 5 | `AI_IQ_002, AI_IQ_003, AI_NSFW_002, AI_NSFW_003, AI_SIM_002` |
| `ai_symbol_detection` | 5 | `AI_PSTEP_002, AI_PSTEP_003, AI_RSYM_002, AI_RSYM_003, AI_RSYM_004` |
| `annotations` | 5 | `LPDF_ANNOT_002, LPDF_ANNOT_003, LPDF_ANNOT_004, LPDF_ANNOT_005, LPDF_ANNOT_006` |
| `page_geometry` | 5 | `LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_007, LPDF_BOX_008, LPDF_BOX_009` |
| `prepress` | 5 | `LPDF_PRESS_001, LPDF_PRESS_002, LPDF_PRESS_003, LPDF_PRESS_004, LPDF_PRESS_005` |
| `ai_document_classification` | 4 | `AI_AFP_002, AI_AFP_003, AI_FCLASS_002, AI_FCLASS_003` |
| `ai_trend_analysis` | 4 | `AI_SPC_001, AI_SPC_002, AI_SPC_003, AI_SPC_004` |
| `metadata` | 4 | `LPDF_META_001, LPDF_META_002, LPDF_META_003, LPDF_META_004` |
| `other` | 3 | `AI_EU1169_001, AI_EU1169_002, AI_EU1169_003` |
| `ai:fda` | 3 | `AI_FDA_001, AI_FDA_002, AI_FDA_005` |
| `standards` | 3 | `LPDF_STD_001, LPDF_STD_002, LPDF_STD_003` |
| `transparency` | 3 | `LPDF_TRANS_004, LPDF_TRANS_006, LPDF_TRANS_007` |
| `ai:brand` | 2 | `AI_BRAND_001, AI_BRAND_002` |
| `ai:cannabis` | 2 | `AI_CANN_001, AI_CANN_002` |
| `ai_dieline_detection` | 2 | `AI_DIE_001, AI_DIE_002` |
| `ai_nlp_interfaces` | 2 | `AI_LANG_003, AI_LANG_004` |
| `ai_logo_verification` | 2 | `AI_LOGO_002, AI_LOGO_003` |
| `ai:orgmetric` | 2 | `AI_ORG_001, AI_ORG_002` |
| `ai_text_analysis` | 2 | `AI_TAO_002, AI_TAO_003` |
| `ai_file_comparison` | 2 | `AI_VDIFF_002, AI_VDIFF_003` |
| `hairlines` | 2 | `LPDF_HAIR_001, LPDF_HAIR_002` |
| `processing` | 2 | `LPDF_PROC_001, LPDF_PROC_002` |
| `ai:afp` | 1 | `AI_AFP_001` |
| `ai:dieline` | 1 | `AI_DIE_003` |
| `ai:duplication` | 1 | `AI_DUP_001` |
| `ai:fibre` | 1 | `AI_FCLASS_001` |
| `ai:ghs` | 1 | `AI_GHS_001` |
| `ai:image_quality` | 1 | `AI_IQ_001` |
| `ai:language` | 1 | `AI_LANG_001` |
| `ai:logo` | 1 | `AI_LOGO_001` |
| `ai:nsfw` | 1 | `AI_NSFW_001` |
| `ai:pharma` | 1 | `AI_PHARMA_001` |
| `ai:recycling_symbols` | 1 | `AI_RSYM_001` |
| `ai:scan_quality` | 1 | `AI_SCAN_001` |
| `ai:similarity` | 1 | `AI_SIM_001` |
| `ai:spelling` | 1 | `AI_SPELL_001` |
| `ai:safe_zones` | 1 | `AI_SZ_001` |
| `ai:tao` | 1 | `AI_TAO_001` |
| `ai:visual_diff` | 1 | `AI_VDIFF_001` |
| `paths` | 1 | `LPDF_PATH_002` |

## Per-category breakdown + default recommendation

### `ai_color_compliance` (38 IDs)

**Recommendation:** KEEP — lintPDF differentiator, ECG/EPM analyzers are unique to this engine

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_BRAND_003` | — | implemented_uncatalogued | `brand_palette.py` |
| `LPDF_AI_DIEL_002` | — | implemented_uncatalogued | `dieline_by_color_name.py` |
| `LPDF_ECG_001` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_002` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_003` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_004` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_005` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_006` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_007` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_008` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_009` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_010` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_011` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_012` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_013` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_014` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_015` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_016` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_017` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_ECG_018` | — | implemented_uncatalogued | `ecg_analyzer.py` |
| `LPDF_EPM_001` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_002` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_003` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_004` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_005` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_006` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_007` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_008` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_009` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_010` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_011` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_012` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_013` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_014` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_015` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_016` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_017` | — | implemented_uncatalogued | `epm_analyzer.py` |
| `LPDF_EPM_018` | — | implemented_uncatalogued | `epm_analyzer.py` |

</details>

### `barcodes` (28 IDs)

**Recommendation:** MIXED — most LPDF_BARCODE_* are barcode finder/decoder rules; uncatalogued ones may be advanced flags. Triage per ID.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_BARCODE_001` | Barcode Detected | implemented | `barcode.py` |
| `LPDF_BARCODE_004` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_005` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_006` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_007` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_008` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_009` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_010` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_011` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_012` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_013` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_014` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_015` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_016` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_017` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_018` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_019` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_020` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_021` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_022` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_023` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_024` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_025` | Low Barcode Resolution | implemented | `barcode.py` |
| `LPDF_BARCODE_026` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_027` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_028` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_029` | — | implemented_uncatalogued | `barcode.py` |
| `LPDF_BARCODE_030` | — | implemented_uncatalogued | `barcode.py` |

</details>

### `ai_barcode` (25 IDs)

**Recommendation:** KEEP — barcode-content-validation suite (LPDF_BCV/BCQM/BD/QR/QHR/PS) is unique

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_BCQM_001` | — | implemented_uncatalogued | `barcode_content_qr_match.py` |
| `LPDF_BCQM_002` | — | implemented_uncatalogued | `barcode_content_qr_match.py` |
| `LPDF_BCQM_003` | — | implemented_uncatalogued | `barcode_content_qr_match.py` |
| `LPDF_BCQM_004` | — | implemented_uncatalogued | `barcode_content_qr_match.py` |
| `LPDF_BCV_001` | — | implemented_uncatalogued | `barcode_content.py` |
| `LPDF_BCV_002` | — | implemented_uncatalogued | `barcode_content.py` |
| `LPDF_BCV_003` | — | implemented_uncatalogued | `barcode_content.py` |
| `LPDF_BC_001` | — | implemented_uncatalogued | `barcode_decode.py` |
| `LPDF_BD_001` | — | implemented_uncatalogued | `barcode_dimensions.py` |
| `LPDF_BD_002` | — | implemented_uncatalogued | `barcode_dimensions.py` |
| `LPDF_BD_003` | — | implemented_uncatalogued | `barcode_dimensions.py` |
| `LPDF_BD_004` | — | implemented_uncatalogued | `barcode_dimensions.py` |
| `LPDF_PS_001` | — | implemented_uncatalogued | `pharma_serialization.py` |
| `LPDF_PS_002` | — | implemented_uncatalogued | `pharma_serialization.py` |
| `LPDF_PS_003` | — | implemented_uncatalogued | `pharma_serialization.py` |
| `LPDF_PS_004` | — | implemented_uncatalogued | `pharma_serialization.py` |
| `LPDF_PS_005` | — | implemented_uncatalogued | `pharma_serialization.py` |
| `LPDF_PS_006` | — | implemented_uncatalogued | `pharma_serialization.py` |
| `LPDF_QHR_001` | — | implemented_uncatalogued | `qr_human_readable.py` |
| `LPDF_QHR_002` | — | implemented_uncatalogued | `qr_human_readable.py` |
| `LPDF_QHR_003` | — | implemented_uncatalogued | `qr_human_readable.py` |
| `LPDF_QR_001` | — | implemented_uncatalogued | `qr_validation.py` |
| `LPDF_QR_002` | — | implemented_uncatalogued | `qr_validation.py` |
| `LPDF_QR_003` | — | implemented_uncatalogued | `qr_validation.py` |
| `LPDF_QR_004` | — | implemented_uncatalogued | `qr_validation.py` |

</details>

### `color` (17 IDs)

**Recommendation:** MIXED — ~24 emit-only colour IDs; many overlap with rich-black / spot work. Likely keep, may need rename.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_COLOR_002` | Spot Color Without Fallback | implemented | `color.py` |
| `LPDF_COLOR_003` | Lab Color Used | implemented | `color.py` |
| `LPDF_COLOR_007` | Mixed Color Spaces | implemented | `color.py` |
| `LPDF_COLOR_008` | CalRGB Color | implemented | `color.py` |
| `LPDF_COLOR_009` | CalGray Color | implemented | `color.py` |
| `LPDF_COLOR_010` | Indexed Color | implemented | `color.py` |
| `LPDF_COLOR_011` | Pattern Color Space | implemented | `color.py` |
| `LPDF_COLOR_012` | Separation Color | implemented | `color.py` |
| `LPDF_COLOR_013` | DeviceN Color | implemented | `color.py` |
| `LPDF_COLOR_014` | Color Space Inventory | implemented | `color.py` |
| `LPDF_COLOR_015` | ICC Profile Mismatch | implemented | `color.py` |
| `LPDF_COLOR_016` | RGB in CMYK Workflow | implemented | `color.py` |
| `LPDF_COLOR_019` | Wide Gamut Color | implemented | `color.py` |
| `LPDF_COLOR_020` | Overink Warning | implemented | `color.py` |
| `LPDF_GAMUT_001` | — | implemented_uncatalogued | `gamut_analyzer.py` |
| `LPDF_GAMUT_002` | — | implemented_uncatalogued | `gamut_analyzer.py` |
| `LPDF_GAMUT_003` | — | implemented_uncatalogued | `gamut_analyzer.py` |

</details>

### `advanced` (14 IDs)

**Recommendation:** MIXED — some advanced colour checks (LPDF_ADV_*) are catalogued; sub-IDs without catalog entries are usually data-capability emissions, not findings. Triage per ID.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_ADV_001` | — | implemented_uncatalogued | `advanced_color_analyzer.py` |
| `LPDF_ADV_002` | Ink Savings Estimate | implemented | `advanced_color_analyzer.py` |
| `LPDF_ADV_003` | — | implemented_uncatalogued | `advanced_color_analyzer.py` |
| `LPDF_ADV_004` | No Spectral Data | implemented | `advanced_color_analyzer.py` |
| `LPDF_ADV_006` | — | implemented_uncatalogued | `advanced_color_analyzer.py` |
| `LPDF_ADV_007` | — | implemented_uncatalogued | `advanced_color_analyzer.py` |
| `LPDF_ADV_008` | — | implemented_uncatalogued | `advanced_color_analyzer.py` |
| `LPDF_ADV_009` | — | implemented_uncatalogued | `advanced_color_analyzer.py` |
| `LPDF_ADV_010` | — | implemented_uncatalogued | `advanced_color_analyzer.py` |
| `LPDF_ADV_011` | — | implemented_uncatalogued | `advanced_color_analyzer.py` |
| `LPDF_ADV_012` | — | implemented_uncatalogued | `advanced_color_analyzer.py` |
| `LPDF_ADV_013` | — | implemented_uncatalogued | `advanced_color_analyzer.py` |
| `LPDF_ADV_014` | — | implemented_uncatalogued | `advanced_color_analyzer.py` |
| `LPDF_ADV_015` | — | implemented_uncatalogued | `advanced_color_analyzer.py` |

</details>

### `strokes` (11 IDs)

**Recommendation:** KEEP — LPDF_STROKE_001..007 family covers Tier-1 hairline + Tier-2/3 derivatives.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_PATH_001` | — | implemented_uncatalogued | `hairline.py` |
| `LPDF_STROKE_002` | — | implemented_uncatalogued | `hairline.py` |
| `LPDF_STROKE_003` | Butt Cap on Thin Line | implemented | `hairline.py` |
| `LPDF_STROKE_004` | — | implemented_uncatalogued | `hairline.py` |
| `LPDF_STROKE_005` | — | implemented_uncatalogued | `hairline.py` |
| `LPDF_STROKE_006` | — | implemented_uncatalogued | `hairline.py` |
| `LPDF_STROKE_007` | Rich Black Stroke | implemented | `hairline.py` |
| `LPDF_TEXT_002` | — | implemented_uncatalogued | `hairline.py` |
| `LPDF_TEXT_003` | — | implemented_uncatalogued | `hairline.py` |
| `LPDF_TEXT_005` | — | implemented_uncatalogued | `hairline.py` |
| `LPDF_TEXT_006` | — | implemented_uncatalogued | `hairline.py` |

</details>

### `ai_regulatory_compliance` (10 IDs)

**Recommendation:** KEEP — regulatory rule pack (FDA, EU 1169, GHS, etc.) supplements the Tier-5 niche line

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_GHS_002` | — | implemented_uncatalogued | `ghs_clp.py` |
| `AI_GHS_003` | — | implemented_uncatalogued | `ghs_clp.py` |
| `AI_GHS_004` | — | implemented_uncatalogued | `ghs_clp.py` |
| `AI_GHS_005` | — | implemented_uncatalogued | `ghs_clp.py` |
| `AI_GHS_006` | — | implemented_uncatalogued | `ghs_clp.py` |
| `AI_GHS_007` | — | implemented_uncatalogued | `ghs_clp.py` |
| `AI_GHS_008` | — | implemented_uncatalogued | `ghs_clp.py` |
| `AI_PHARMA_002` | — | implemented_uncatalogued | `pharma_font.py` |
| `AI_PHARMA_003` | — | implemented_uncatalogued | `pharma_font.py` |
| `AI_PHARMA_004` | — | implemented_uncatalogued | `pharma_font.py` |

</details>

### `packaging` (10 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_PKG_001` | Dieline Detected | implemented | `packaging.py` |
| `LPDF_PKG_002` | Missing Dieline | implemented | `packaging.py` |
| `LPDF_PKG_003` | — | implemented_uncatalogued | `packaging.py` |
| `LPDF_PKG_004` | — | implemented_uncatalogued | `packaging.py` |
| `LPDF_PKG_005` | — | implemented_uncatalogued | `packaging.py` |
| `LPDF_PKG_006` | — | implemented_uncatalogued | `packaging.py` |
| `LPDF_PKG_007` | — | implemented_uncatalogued | `packaging.py` |
| `LPDF_PKG_008` | — | implemented_uncatalogued | `packaging.py` |
| `LPDF_PKG_009` | — | implemented_uncatalogued | `packaging.py` |
| `LPDF_PKG_010` | — | implemented_uncatalogued | `packaging.py` |

</details>

### `structure` (10 IDs)

**Recommendation:** MIXED — additional structure checks. Likely keep.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_STRUCT_005` | — | implemented_uncatalogued | `structure.py` |
| `LPDF_STRUCT_006` | — | implemented_uncatalogued | `structure.py` |
| `LPDF_STRUCT_007` | — | implemented_uncatalogued | `structure.py` |
| `LPDF_STRUCT_008` | — | implemented_uncatalogued | `structure.py` |
| `LPDF_STRUCT_009` | — | implemented_uncatalogued | `structure.py` |
| `LPDF_STRUCT_010` | — | implemented_uncatalogued | `structure.py` |
| `LPDF_STRUCT_011` | — | implemented_uncatalogued | `structure.py` |
| `LPDF_STRUCT_012` | — | implemented_uncatalogued | `structure.py` |
| `LPDF_STRUCT_013` | — | implemented_uncatalogued | `structure.py` |
| `LPDF_STRUCT_014` | — | implemented_uncatalogued | `structure.py` |

</details>

### `fonts` (9 IDs)

**Recommendation:** MIXED — additional font checks (CIDSystemInfo, encoding, etc.) — likely keep as Tier-1 supplements.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_FONT_003` | System Font Used | implemented | `font.py` |
| `LPDF_FONT_006` | Missing CIDSystemInfo | implemented | `font.py` |
| `LPDF_FONT_007` | No Font Encoding | implemented | `font.py` |
| `LPDF_FONT_009` | OpenType Not Embedded | implemented | `font.py` |
| `LPDF_FONT_010` | Incomplete Font | implemented | `font.py` |
| `LPDF_FONT_011` | Multiple Master Font | implemented | `font.py` |
| `LPDF_FONT_012` | Faux Bold | implemented | `font.py` |
| `LPDF_FONT_013` | Faux Italic | implemented | `font.py` |
| `LPDF_FONT_014` | Damaged Font | implemented | `font.py` |

</details>

### `color_management` (9 IDs)

**Recommendation:** KEEP — ICC profile inspection beyond Tier-1 output-intent presence.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_ICC_001` | No ICC Profile | implemented | `icc_profile_analyzer.py` |
| `LPDF_ICC_002` | Invalid ICC Profile | implemented | `icc_profile_analyzer.py` |
| `LPDF_ICC_003` | ICC Version Mismatch | implemented | `icc_profile_analyzer.py` |
| `LPDF_ICC_004` | Wrong ICC Device Class | implemented | `icc_profile_analyzer.py` |
| `LPDF_ICC_005` | — | implemented_uncatalogued | `icc_profile_analyzer.py` |
| `LPDF_ICC_006` | — | implemented_uncatalogued | `icc_profile_analyzer.py` |
| `LPDF_ICC_007` | — | implemented_uncatalogued | `icc_profile_analyzer.py` |
| `LPDF_ICC_008` | — | implemented_uncatalogued | `icc_profile_analyzer.py` |
| `LPDF_ICC_009` | — | implemented_uncatalogued | `icc_profile_analyzer.py` |

</details>

### `image` (9 IDs)

**Recommendation:** MIXED — additional image checks beyond the Tier-1 resolution / format set. Keep.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_IMG_002` | Excessive Resolution | implemented | `image.py` |
| `LPDF_IMG_004` | No Image Compression | implemented | `image.py` |
| `LPDF_IMG_005` | Inline Image | implemented | `image.py` |
| `LPDF_IMG_006` | Upscaled Image | implemented | `image.py` |
| `LPDF_IMG_007` | LZW Compression | implemented | `image.py` |
| `LPDF_IMG_009` | 16-Bit Image | implemented | `image.py` |
| `LPDF_IMG_010` | OPI Reference | implemented | `image.py` |
| `LPDF_IMG_012` | OPI in Resources | implemented | `image.py` |
| `LPDF_IMG_016` | Flipped Image | implemented | `image.py` |

</details>

### `spot_colors` (8 IDs)

**Recommendation:** MIXED — overlaps Tier-2 SPT family.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_SPOT_004` | — | implemented_uncatalogued | `spot_color_analyzer.py` |
| `LPDF_SPOT_005` | — | implemented_uncatalogued | `spot_color_analyzer.py` |
| `LPDF_SPOT_006` | — | implemented_uncatalogued | `spot_color_analyzer.py` |
| `LPDF_SPOT_007` | — | implemented_uncatalogued | `spot_color_analyzer.py` |
| `LPDF_SPOT_008` | — | implemented_uncatalogued | `spot_color_analyzer.py` |
| `LPDF_SPOT_009` | — | implemented_uncatalogued | `spot_color_analyzer.py` |
| `LPDF_SPOT_010` | — | implemented_uncatalogued | `spot_color_analyzer.py` |
| `LPDF_SPOT_011` | — | implemented_uncatalogued | `spot_color_analyzer.py` |

</details>

### `ai_other` (7 IDs)

**Recommendation:** MIXED — uncategorised AI emissions; Phase 1 cleanup item.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_LANG_002` | — | implemented_uncatalogued | `language_detection.py, multi_language.py` |
| `AI_SPELL_002` | — | implemented_uncatalogued | `spell_check.py` |
| `AI_SZ_002` | — | implemented_uncatalogued | `safe_zone_violations.py` |
| `LPDF_AI_BAND_001` | — | implemented_uncatalogued | `banding_detection.py` |
| `LPDF_AI_CAST_001` | — | implemented_uncatalogued | `color_cast_detection.py` |
| `LPDF_AI_CDCC_001` | — | implemented_uncatalogued | `cross_document_consistency.py` |
| `LPDF_AI_SKIN_001` | — | implemented_uncatalogued | `skin_tone_validation.py` |

</details>

### `document` (7 IDs)

**Recommendation:** MIXED — overlaps Tier-1 CMP/STR family.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_DOC_002` | — | implemented_uncatalogued | `document.py` |
| `LPDF_DOC_003` | — | implemented_uncatalogued | `document.py` |
| `LPDF_DOC_004` | — | implemented_uncatalogued | `document.py` |
| `LPDF_DOC_005` | — | implemented_uncatalogued | `document.py` |
| `LPDF_DOC_006` | — | implemented_uncatalogued | `document.py` |
| `LPDF_DOC_007` | — | implemented_uncatalogued | `document.py` |
| `LPDF_DOC_008` | — | implemented_uncatalogued | `document.py` |

</details>

### `accessibility` (6 IDs)

**Recommendation:** KEEP — Tier 4 catches some, but additional LPDF_ACCESS_* checks supplement it.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_ACCESS_007` | — | implemented_uncatalogued | `accessibility.py` |
| `LPDF_ACCESS_008` | — | implemented_uncatalogued | `accessibility.py` |
| `LPDF_ACCESS_009` | — | implemented_uncatalogued | `accessibility.py` |
| `LPDF_ACCESS_010` | — | implemented_uncatalogued | `accessibility.py` |
| `LPDF_ACCESS_011` | — | implemented_uncatalogued | `accessibility.py` |
| `LPDF_ACCESS_013` | — | implemented_uncatalogued | `accessibility.py` |

</details>

### `overprint` (6 IDs)

**Recommendation:** MIXED — overlaps Tier-1 C05/C06.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_OVER_003` | Overprint Mode Mismatch | implemented | `overprint.py` |
| `LPDF_OVER_004` | — | implemented_uncatalogued | `overprint.py` |
| `LPDF_OVER_005` | — | implemented_uncatalogued | `overprint.py` |
| `LPDF_OVER_006` | — | implemented_uncatalogued | `overprint.py` |
| `LPDF_OVER_007` | — | implemented_uncatalogued | `overprint.py` |
| `LPDF_OVER_008` | — | implemented_uncatalogued | `overprint.py` |

</details>

### `ai_image_analysis` (5 IDs)

**Recommendation:** KEEP — pixel-level image quality + NSFW detection

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_IQ_002` | — | implemented_uncatalogued | `image_quality.py` |
| `AI_IQ_003` | — | implemented_uncatalogued | `image_quality.py` |
| `AI_NSFW_002` | — | implemented_uncatalogued | `nsfw_detection.py` |
| `AI_NSFW_003` | — | implemented_uncatalogued | `nsfw_detection.py` |
| `AI_SIM_002` | — | implemented_uncatalogued | `image_similarity.py` |

</details>

### `ai_symbol_detection` (5 IDs)

**Recommendation:** KEEP — regulatory symbol detection

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_PSTEP_002` | — | implemented_uncatalogued | `processing_steps_fallback.py` |
| `AI_PSTEP_003` | — | implemented_uncatalogued | `processing_steps_fallback.py` |
| `AI_RSYM_002` | — | implemented_uncatalogued | `regulatory_symbols.py` |
| `AI_RSYM_003` | — | implemented_uncatalogued | `regulatory_symbols.py` |
| `AI_RSYM_004` | — | implemented_uncatalogued | `regulatory_symbols.py` |

</details>

### `annotations` (5 IDs)

**Recommendation:** MIXED — overlaps Tier-1 CMP05.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_ANNOT_002` | — | implemented_uncatalogued | `annotation.py` |
| `LPDF_ANNOT_003` | Link Annotation | implemented | `annotation.py` |
| `LPDF_ANNOT_004` | — | implemented_uncatalogued | `annotation.py` |
| `LPDF_ANNOT_005` | — | implemented_uncatalogued | `annotation.py` |
| `LPDF_ANNOT_006` | — | implemented_uncatalogued | `annotation.py` |

</details>

### `page_geometry` (5 IDs)

**Recommendation:** MIXED — overlaps Tier-1 STR family.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_BOX_005` | Content in Safety Margin | implemented | `page_geometry.py` |
| `LPDF_BOX_006` | Content Beyond Bleed | implemented | `page_geometry.py` |
| `LPDF_BOX_007` | UserUnit Scaling | implemented | `page_geometry.py` |
| `LPDF_BOX_008` | Non-Standard Orientation | implemented | `page_geometry.py` |
| `LPDF_BOX_009` | Inconsistent Page Sizes | implemented | `page_geometry.py` |

</details>

### `prepress` (5 IDs)

**Recommendation:** KEEP — prepress-specific checks not in canonical gap list.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_PRESS_001` | — | implemented_uncatalogued | `prepress.py` |
| `LPDF_PRESS_002` | — | implemented_uncatalogued | `prepress.py` |
| `LPDF_PRESS_003` | — | implemented_uncatalogued | `prepress.py` |
| `LPDF_PRESS_004` | — | implemented_uncatalogued | `prepress.py` |
| `LPDF_PRESS_005` | — | implemented_uncatalogued | `prepress.py` |

</details>

### `ai_document_classification` (4 IDs)

**Recommendation:** KEEP — auto-preflight-profile and file-classification AI

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_AFP_002` | — | implemented_uncatalogued | `auto_preflight_profile.py` |
| `AI_AFP_003` | — | implemented_uncatalogued | `auto_preflight_profile.py` |
| `AI_FCLASS_002` | — | implemented_uncatalogued | `file_classification.py` |
| `AI_FCLASS_003` | — | implemented_uncatalogued | `file_classification.py` |

</details>

### `ai_trend_analysis` (4 IDs)

**Recommendation:** KEEP — submission-quality SPC, runs across jobs

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_SPC_001` | — | implemented_uncatalogued | `submission_quality_spc.py` |
| `AI_SPC_002` | — | implemented_uncatalogued | `submission_quality_spc.py` |
| `AI_SPC_003` | — | implemented_uncatalogued | `submission_quality_spc.py` |
| `AI_SPC_004` | — | implemented_uncatalogued | `submission_quality_spc.py` |

</details>

### `metadata` (4 IDs)

**Recommendation:** MIXED — overlaps Tier-2 XMP family.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_META_001` | No XMP Metadata | implemented | `metadata.py` |
| `LPDF_META_002` | — | implemented_uncatalogued | `metadata.py` |
| `LPDF_META_003` | — | implemented_uncatalogued | `metadata.py` |
| `LPDF_META_004` | — | implemented_uncatalogued | `metadata.py` |

</details>

### `other` (3 IDs)

**Recommendation:** MIXED — uncategorised; per-ID triage required.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_EU1169_001` | EU Font Size Violation | implemented | `eu_fir_1169.py` |
| `AI_EU1169_002` | Allergen Not Emphasized | implemented | `eu_fir_1169.py` |
| `AI_EU1169_003` | EU Nutrition Format | implemented | `eu_fir_1169.py` |

</details>

### `ai:fda` (3 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_FDA_001` | Calories Font Too Small | implemented | `fda_nutrition.py` |
| `AI_FDA_002` | NFP Text Too Small | implemented | `fda_nutrition.py` |
| `AI_FDA_005` | FDA Label Warning | implemented | `fda_nutrition.py` |

</details>

### `standards` (3 IDs)

**Recommendation:** KEEP — standards-conformance checks.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_STD_001` | G7 Compliance | implemented | `standards_compliance.py` |
| `LPDF_STD_002` | GRACoL Compliance | implemented | `standards_compliance.py` |
| `LPDF_STD_003` | ISO 12647 Compliance | implemented | `standards_compliance.py` |

</details>

### `transparency` (3 IDs)

**Recommendation:** MIXED — overlaps Tier-1 TRN family.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_TRANS_004` | Low Opacity | implemented | `transparency.py` |
| `LPDF_TRANS_006` | — | implemented_uncatalogued | `transparency.py` |
| `LPDF_TRANS_007` | — | implemented_uncatalogued | `transparency.py` |

</details>

### `ai:brand` (2 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_BRAND_001` | No Brand Palette | implemented | `brand_palette.py` |
| `AI_BRAND_002` | Brand Color Deviation | implemented | `brand_palette.py` |

</details>

### `ai:cannabis` (2 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_CANN_001` | Cannabis Warning Missing | stub_documented | `cannabis.py` |
| `AI_CANN_002` | — | docstring_only_uncatalogued | `cannabis.py` |

</details>

### `ai_dieline_detection` (2 IDs)

**Recommendation:** KEEP — supplements Tier-3 dieline gap (these are the *detectors* that feed dieline rules)

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_DIE_001` | — | implemented_uncatalogued | `dieline_by_name.py` |
| `AI_DIE_002` | — | implemented_uncatalogued | `dieline_by_name.py` |

</details>

### `ai_nlp_interfaces` (2 IDs)

**Recommendation:** KEEP — multi-language scan / translation, no canonical equivalent

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_LANG_003` | — | implemented_uncatalogued | `multi_language.py` |
| `AI_LANG_004` | — | implemented_uncatalogued | `multi_language.py` |

</details>

### `ai_logo_verification` (2 IDs)

**Recommendation:** KEEP — brand-spec aware, complements Tier 2 brand work

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_LOGO_002` | — | implemented_uncatalogued | `logo_detection.py` |
| `AI_LOGO_003` | — | implemented_uncatalogued | `logo_detection.py` |

</details>

### `ai:orgmetric` (2 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_ORG_001` | Organic Seal Issue | stub_documented | `organic.py` |
| `AI_ORG_002` | — | docstring_only_uncatalogued | `organic.py` |

</details>

### `ai_text_analysis` (2 IDs)

**Recommendation:** KEEP — text-as-outlines aggregation, spelling, etc.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_TAO_002` | — | implemented_uncatalogued | `text_as_outlines.py` |
| `AI_TAO_003` | — | implemented_uncatalogued | `text_as_outlines.py` |

</details>

### `ai_file_comparison` (2 IDs)

**Recommendation:** KEEP — version-diff and similarity

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_VDIFF_002` | — | implemented_uncatalogued | `version_diff.py` |
| `AI_VDIFF_003` | — | implemented_uncatalogued | `version_diff.py` |

</details>

### `hairlines` (2 IDs)

**Recommendation:** KEEP — overlaps Tier-1 STR07 / Tier-2 RB02.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_HAIR_001` | Hairline Stroke | catalog_only_no_source | `—` |
| `LPDF_HAIR_002` | Small Text on Thin Stroke | catalog_only_no_source | `—` |

</details>

### `processing` (2 IDs)

**Recommendation:** KEEP — processing-related warnings.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_PROC_001` | — | implemented_uncatalogued | `processing.py` |
| `LPDF_PROC_002` | — | implemented_uncatalogued | `processing.py` |

</details>

### `ai:afp` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_AFP_001` | Auto Profile Suggestion | implemented | `auto_preflight_profile.py` |

</details>

### `ai:dieline` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_DIE_003` | No Dieline Found | implemented | `dieline_by_name.py` |

</details>

### `ai:duplication` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_DUP_001` | Duplicate Content | implemented | `duplicate_detection.py` |

</details>

### `ai:fibre` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_FCLASS_001` | Document Classification | implemented | `file_classification.py` |

</details>

### `ai:ghs` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_GHS_001` | Missing GHS Elements | implemented | `ghs_clp.py` |

</details>

### `ai:image_quality` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_IQ_001` | Image Quality Issue | implemented | `image_quality.py` |

</details>

### `ai:language` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_LANG_001` | Language Detected | implemented | `language_detection.py, multi_language.py` |

</details>

### `ai:logo` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_LOGO_001` | Logo Not Found | implemented | `logo_detection.py` |

</details>

### `ai:nsfw` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_NSFW_001` | Content Safety Flag | implemented | `nsfw_detection.py` |

</details>

### `ai:pharma` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_PHARMA_001` | Pharma Font Too Small | implemented | `pharma_font.py` |

</details>

### `ai:recycling_symbols` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_RSYM_001` | Missing Regulatory Symbol | catalog_only_no_source | `—` |

</details>

### `ai:scan_quality` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_SCAN_001` | AI Scan Complete | catalog_only_no_source | `—` |

</details>

### `ai:similarity` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_SIM_001` | Similar Images | implemented | `image_similarity.py` |

</details>

### `ai:spelling` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_SPELL_001` | Misspelled Word | implemented | `spell_check.py` |

</details>

### `ai:safe_zones` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_SZ_001` | Safe Zone Violation | implemented | `safe_zone_violations.py` |

</details>

### `ai:tao` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_TAO_001` | Text Not Outlined | catalog_only_no_source | `—` |

</details>

### `ai:visual_diff` (1 IDs)

**Recommendation:** TRIAGE — operator decision needed

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `AI_VDIFF_001` | No Reference File | implemented | `version_diff.py` |

</details>

### `paths` (1 IDs)

**Recommendation:** KEEP — path-specific checks.

<details><summary>IDs (click to expand)</summary>

| ID | Name | Status | Source |
|---|---|---|---|
| `LPDF_PATH_002` | White Fill Path | implemented | `hairline.py` |

</details>
