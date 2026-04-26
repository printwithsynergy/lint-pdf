# Phase 1.4 — Unmapped Existing Checks

**Date:** 2026-04-25
**Source:** `audit/phase-0/existing-checks.json` ∩ `audit/phase-1-v2/v2-id-coverage.json`

- **Engine inspection_ids total:** 373
- **Claimed by v2 universe:** 126
- **Unmapped (lintPDF surface beyond v2):** 283

## What 'unmapped' means

An engine `inspection_id` is unmapped if no v2 ID's `matched_inspection_ids`
claims it. These are checks lintPDF emits today that aren't in the v2
canonical universe — they are net-new surface beyond the published
competitive baselines (callas, PitStop, Esko, etc.).

Per Phase 0.2: this is largely **AI-tier surface** (color compliance,
barcode subfamily, regulatory subfamily, dieline-detection, etc.) plus
Tier-1 supplements within established families.

## Default recommendation per category

Per playbook §1.4: for each, decide **Keep / Rename to match v2 / Deprecate / Escalate to v2 universe**.
Default: **KEEP** for AI-tier categories; **RENAME to v2 ID** for items that semantically map to a v2 slot but use a different engine id.

## Counts by engine-prefix

| Prefix | Unmapped | Sample |
|--------|---------:|--------|
| `LPDF_ECG` | 18 | LPDF_ECG_001, LPDF_ECG_002, LPDF_ECG_003… |
| `LPDF_EPM` | 17 | LPDF_EPM_001, LPDF_EPM_002, LPDF_EPM_003… |
| `LPDF_ADV` | 14 | LPDF_ADV_001, LPDF_ADV_002, LPDF_ADV_003… |
| `LPDF_ACCESS` | 12 | LPDF_ACCESS_001, LPDF_ACCESS_002, LPDF_ACCESS_003… |
| `LPDF_COLOR` | 12 | LPDF_COLOR_002, LPDF_COLOR_003, LPDF_COLOR_005… |
| `LPDF_BARCODE` | 11 | LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022… |
| `LPDF_STRUCT` | 10 | LPDF_STRUCT_002, LPDF_STRUCT_003, LPDF_STRUCT_005… |
| `LPDF_ICC` | 9 | LPDF_ICC_001, LPDF_ICC_002, LPDF_ICC_003… |
| `LPDF_SPOT` | 9 | LPDF_SPOT_002, LPDF_SPOT_004, LPDF_SPOT_005… |
| `AI_GHS` | 8 | AI_GHS_001, AI_GHS_002, AI_GHS_003… |
| `LPDF_PKG` | 8 | LPDF_PKG_001, LPDF_PKG_002, LPDF_PKG_003… |
| `LPDF_STROKE` | 7 | LPDF_STROKE_001, LPDF_STROKE_002, LPDF_STROKE_003… |
| `LPDF_BOX` | 6 | LPDF_BOX_004, LPDF_BOX_005, LPDF_BOX_006… |
| `LPDF_DOC` | 6 | LPDF_DOC_002, LPDF_DOC_003, LPDF_DOC_005… |
| `LPDF_OVER` | 6 | LPDF_OVER_003, LPDF_OVER_004, LPDF_OVER_005… |
| `LPDF_PS` | 6 | LPDF_PS_001, LPDF_PS_002, LPDF_PS_003… |
| `AI_FDA` | 5 | AI_FDA_001, AI_FDA_002, AI_FDA_003… |
| `LPDF_AI` | 5 | LPDF_AI_BAND_001, LPDF_AI_CAST_001, LPDF_AI_CDCC_001… |
| `LPDF_ANNOT` | 5 | LPDF_ANNOT_002, LPDF_ANNOT_003, LPDF_ANNOT_004… |
| `LPDF_FONT` | 5 | LPDF_FONT_003, LPDF_FONT_006, LPDF_FONT_007… |
| `LPDF_PRESS` | 5 | LPDF_PRESS_001, LPDF_PRESS_002, LPDF_PRESS_003… |
| `AI_LANG` | 4 | AI_LANG_001, AI_LANG_002, AI_LANG_003… |
| `AI_PHARMA` | 4 | AI_PHARMA_001, AI_PHARMA_002, AI_PHARMA_003… |
| `AI_RSYM` | 4 | AI_RSYM_001, AI_RSYM_002, AI_RSYM_003… |
| `AI_SPC` | 4 | AI_SPC_001, AI_SPC_002, AI_SPC_003… |
| `LPDF_BCQM` | 4 | LPDF_BCQM_001, LPDF_BCQM_002, LPDF_BCQM_003… |
| `LPDF_BD` | 4 | LPDF_BD_001, LPDF_BD_002, LPDF_BD_003… |
| `LPDF_IMG` | 4 | LPDF_IMG_005, LPDF_IMG_006, LPDF_IMG_007… |
| `LPDF_QR` | 4 | LPDF_QR_001, LPDF_QR_002, LPDF_QR_003… |
| `LPDF_TEXT` | 4 | LPDF_TEXT_002, LPDF_TEXT_003, LPDF_TEXT_005… |

(56 prefixes total; top 30 shown.)

## Triage actions

1. **AI_*_*** prefixes (`AI_BAR_*`, `AI_COL_*`, `AI_REG_*`, etc.) — these
   are AI-tier checks. **Keep** by default; they're lintPDF's net-new
   surface beyond the v2 published baselines.

2. **`LPDF_<CAT>_*` items not in v2** — likely candidates for v2 universe
   inclusion or rename to a v2 slot. Triage per-item during Phase 2 design
   notes; default action **NO CHANGE** until evidence for rename surfaces.

3. **Catalog-only / docstring-only items** — verify against `audit/phase-
   0/existing-checks-summary.md` and the catalog generator. Stale entries
   should be deprecated; placeholder analyzers should be flagged for
   completion.

## Full list (machine-readable)

See `audit/phase-1-v2/unmapped-existing.json` for the full list with
human names, source files, and status. The Markdown above is summary only.
