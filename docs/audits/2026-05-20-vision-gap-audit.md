# Vision gap audit — 2026-05-20

Engine (CPU checks only, no AI) vs Claude Opus vision on rendered pages.
Max pages per PDF: 3. Corpus: 11 PDFs.

## Summary table

| PDF | Engine findings | Vision findings | Vision-only (gaps) | Engine-only (FP?) |
|-----|:--------------:|:---------------:|:------------------:|:-----------------:|
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | 64 | 6 | 3 | 2 |
| `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | 48 | 6 | 2 | 2 |
| `Amalgam_Catalyst_9_5x3_5` | 38 | 5 | 3 | 2 |
| `Cherry-Twist_OUTLINED` | 82 | 8 | 5 | 1 |
| `DailyFiber_10up` | 83 | 8 | 0 | 1 |
| `HSI_OUTLINED` | 55 | 5 | 2 | 1 |
| `Nutrops_LS_Dieline` | 141 | 9 | 2 | 1 |
| `Nutrops_SF_Dieline` | 140 | 0 | 0 | 7 |
| `OrangeKiss_OUTLINED` | 55 | 6 | 3 | 1 |
| `Pavette_Pride_v99` | 33 | 6 | 3 | 1 |
| `Pink-Slush_OUTLINED` | 64 | 6 | 3 | 1 |

## Vision-only findings (engine misses)

These are issues Claude vision found but the engine produced **zero** matching check IDs.
These are the most actionable gaps.

| PDF | Category | Page | Severity | Description |
|-----|----------|:----:|:--------:|-------------|
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | `placeholder_text` | 1 | error | 'LOT NUMBER' placeholder text present on right side panel - needs to be replaced with actual lot number for production |
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | `placeholder_text` | 1 | error | 'DATE CODE' placeholder text present on right side panel - needs to be replaced with actual date code for production |
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | `small_text` | 1 | warning | Ingredients/nutrition text on left and right panels appears very small (likely at or below 4-5pt), verify legibility meets regulatory minimum |
| `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | `placeholder_text` | 1 | error | Placeholder text 'LOT NUMBER' and 'DATE CODE' visible on right side panel - variable data tokens not replaced with actual values |
| `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | `overprint` | 1 | warning | White text and white logo elements over colored backgrounds - confirm overprint is OFF for white objects to prevent dropout |
| `Amalgam_Catalyst_9_5x3_5` | `other` | 1 | error | Page appears essentially blank with only a blue rectangular keyline/die-line visible and no printable artwork inside the live area. |
| `Amalgam_Catalyst_9_5x3_5` | `spot_color` | 1 | warning | Blue rectangle outline appears to be a die/keyline that may print if not set to a non-printing spot color (e.g., 'Dieline'). |
| `Amalgam_Catalyst_9_5x3_5` | `other` | 1 | warning | Stray dark gray spatter/spot marks appear outside the keyline near the trim edges; verify these are intentional design elements and not stray artwork or scanner artifacts. |
| `Cherry-Twist_OUTLINED` | `placeholder_text` | 1 | error | Variable-data placeholder 'LOT NUMBER' visible on right side panel - must be replaced with actual lot number before print |
| `Cherry-Twist_OUTLINED` | `placeholder_text` | 1 | error | Variable-data placeholder 'DATE CODE' visible on right side panel - must be replaced with actual date code before print |
| `Cherry-Twist_OUTLINED` | `small_text` | 1 | warning | Ingredients text (English and French) appears very small, likely below 5pt - verify legibility and compliance with regulatory minimums |
| `Cherry-Twist_OUTLINED` | `small_text` | 1 | warning | Copyright/manufacturer line on far right side panel appears extremely small (<4pt) - may not be legible when printed |
| `Cherry-Twist_OUTLINED` | `font_issue` | 1 | info | File named 'OUTLINED' suggests fonts converted to outlines - verify small text remains crisp and has not become heavier/illegible after outlining |
| `HSI_OUTLINED` | `placeholder_text` | 1 | error | Variable data placeholders 'LOT NUMBER' and 'DATE CODE' visible in white box on right side - must be replaced with actual lot/date data before printing |
| `HSI_OUTLINED` | `small_text` | 1 | warning | Ingredients text on left and bottom panels appears very small (likely below 5pt when printed at 2.44" width) - verify legibility meets regulatory minimums |
| `Nutrops_LS_Dieline` | `spot_color` | 1 | warning | Job is specified as 2 Pantone spots (2725C purple, 7401C cream). Verify all art elements (logo, bear icon, type, fruit illustration with multiple shades, barcode) are built only from these two spots plus any allowed tints—lemon/blueberry illustration appears to contain additional colors that may separate as process or extra plates. |
| `Nutrops_LS_Dieline` | `overprint` | 1 | error | Cream-colored type and shapes reversed out of the purple background should be set to knockout, not overprint—overprinting cream on purple will cause the cream to disappear or shift color. Verify overprint settings on all light-on-dark elements. |
| `OrangeKiss_OUTLINED` | `placeholder_text` | 1 | error | 'LOT NUMBER' and 'DATE CODE' appear as placeholder text that should be replaced with variable data before printing |
| `OrangeKiss_OUTLINED` | `small_text` | 1 | warning | Ingredients lists in both English and French appear very small (likely below 5pt) and may be difficult to read; verify meets minimum legal/regulatory size requirements |
| `OrangeKiss_OUTLINED` | `small_text` | 1 | warning | Copyright/manufacturer line '©2025 ALANI NUTRITION, LLC...' is extremely small and may not be legible when printed |
| `Pavette_Pride_v99` | `hairline_stroke` | 1 | warning | Thin cyan/blue keyline around the circular front label and thin pink/cyan keylines around the back label appear to be hairline strokes that may be die-lines left in the art or will drop out on press if intended to print. |
| `Pavette_Pride_v99` | `small_text` | 1 | warning | Multilingual 'Contains Sulfites' translation block on back label appears to be below 4pt and may be illegible when printed. |
| `Pavette_Pride_v99` | `placeholder_text` | 1 | info | Filename suffix 'v99' and vintage '2025' should be confirmed as final approved values rather than working placeholders. |
| `Pink-Slush_OUTLINED` | `placeholder_text` | 1 | warning | Variable-data placeholders 'LOT NUMBER' and 'DATE CODE' visible — confirm these are intended as imprint zones, not literal text to print. |
| `Pink-Slush_OUTLINED` | `small_text` | 1 | warning | Ingredient lists (English and French) appear very small, likely at or below 5pt; verify legibility meets regulatory minimums. |
| `Pink-Slush_OUTLINED` | `font_issue` | 1 | info | File name indicates 'OUTLINED' — fonts converted to outlines; confirm no text edits are needed since text is no longer editable. |

## Engine-only categories (possible false positives or vision blind spots)

Categories where the engine fired but vision saw nothing.

| PDF | Category |
|-----|----------|
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | `font_issue` |
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | `hairline_stroke` |
| `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | `font_issue` |
| `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | `hairline_stroke` |
| `Amalgam_Catalyst_9_5x3_5` | `barcode` |
| `Amalgam_Catalyst_9_5x3_5` | `color_issue` |
| `Cherry-Twist_OUTLINED` | `hairline_stroke` |
| `DailyFiber_10up` | `font_issue` |
| `HSI_OUTLINED` | `hairline_stroke` |
| `Nutrops_LS_Dieline` | `font_issue` |
| `Nutrops_SF_Dieline` | `small_text` |
| `Nutrops_SF_Dieline` | `hairline_stroke` |
| `Nutrops_SF_Dieline` | `placeholder_text` |
| `Nutrops_SF_Dieline` | `font_issue` |
| `Nutrops_SF_Dieline` | `color_issue` |
| `Nutrops_SF_Dieline` | `bleed_missing` |
| `Nutrops_SF_Dieline` | `barcode` |
| `OrangeKiss_OUTLINED` | `hairline_stroke` |
| `Pavette_Pride_v99` | `font_issue` |
| `Pink-Slush_OUTLINED` | `hairline_stroke` |

## Per-PDF detail

### AN-Energy_StickPack_CA_Pink-Slush_P2_OL

**Engine:** 64 findings  
**Vision:** 6 findings  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
- `LPDF_ADV_005`
- `LPDF_BARCODE_001`
- `LPDF_BARCODE_006`
- `LPDF_BARCODE_007`
- `LPDF_BARCODE_008`
- `LPDF_BARCODE_009`
- `LPDF_BARCODE_010`
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_028`
- `LPDF_BARCODE_DARK_BG`
- `LPDF_BARCODE_QUIET_ZONE_EDGE`
- `LPDF_BOX_003`
- `LPDF_BOX_005`
- `LPDF_BOX_006`
- `LPDF_BOX_BG_NO_BLEED`
- `LPDF_BOX_MULTI_LABEL_PAGE`
- `LPDF_BOX_TRIMBOX_DEFAULTED`
- `LPDF_COLOR_006`
- `LPDF_FONT_005`
- `LPDF_FONT_007`
- `LPDF_GRAIN_MISSING`
- `LPDF_INK_001`
- `LPDF_INK_002`
- `LPDF_INK_003`
- `LPDF_META_003`
- `LPDF_PATH_002`
- `LPDF_STD_001`
- `LPDF_STD_002`
- `LPDF_STD_003`
- `LPDF_VIEWER_DISPLAY_TITLE`
- `LPDF_XMP_GWG_TRAIL`

**Vision findings:**

- p1 `placeholder_text` [error]: 'LOT NUMBER' placeholder text present on right side panel - needs to be replaced with actual lot number for production ← **NO ENGINE MATCH**
- p1 `placeholder_text` [error]: 'DATE CODE' placeholder text present on right side panel - needs to be replaced with actual date code for production ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Ingredients/nutrition text on left and right panels appears very small (likely at or below 4-5pt), verify legibility meets regulatory minimum ← **NO ENGINE MATCH**
- p1 `bleed_missing` [warning]: Verify pink/magenta background art extends fully to bleed marks on top and bottom edges; design appears to end near trim ← engine: LPDF_BOX_003, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_BG_NO_BLEED, LPDF_BOX_TRIMBOX_DEFAULTED, LPDF_BOX_MULTI_LABEL_PAGE
- p1 `barcode` [warning]: UPC barcode is rotated vertically and printed over a white panel - verify minimum X-dimension and quiet zones are maintained for scannability ← engine: LPDF_BARCODE_001, LPDF_BARCODE_006, LPDF_BARCODE_007, LPDF_BARCODE_008, LPDF_BARCODE_009, LPDF_BARCODE_010, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_028, LPDF_BARCODE_QUIET_ZONE_EDGE, LPDF_BARCODE_DARK_BG
- p1 `color_issue` [warning]: Verify white text/elements (e.g., 'PINK SLUSH', 'Alani' logo, 'NET 4.94 g') are set to knockout and not overprint, to prevent disappearance on press ← engine: LPDF_COLOR_006, LPDF_INK_001, LPDF_INK_002, LPDF_INK_002, LPDF_INK_002, LPDF_INK_002, LPDF_INK_003, LPDF_ADV_002, LPDF_ADV_004, LPDF_ADV_005

### AN_Energy_StickPack_CA_HSI_ADM_P1_OL

**Engine:** 48 findings  
**Vision:** 6 findings  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
- `LPDF_ADV_005`
- `LPDF_BARCODE_001`
- `LPDF_BARCODE_007`
- `LPDF_BARCODE_008`
- `LPDF_BARCODE_010`
- `LPDF_BARCODE_013`
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_029`
- `LPDF_BARCODE_DARK_BG`
- `LPDF_BARCODE_QUIET_ZONE_INK`
- `LPDF_BOX_003`
- `LPDF_BOX_TRIMBOX_DEFAULTED`
- `LPDF_COLOR_006`
- `LPDF_FONT_005`
- `LPDF_FONT_007`
- `LPDF_GRAIN_MISSING`
- `LPDF_INK_001`
- `LPDF_INK_002`
- `LPDF_INK_003`
- `LPDF_LANG_001`
- `LPDF_LEGALCOPY_001`
- `LPDF_META_003`
- `LPDF_PATH_002`
- `LPDF_STD_001`
- `LPDF_STD_002`
- `LPDF_STD_003`
- `LPDF_TEXT_001`
- `LPDF_TEXT_LEGIBILITY_VERIFY`
- `LPDF_VIEWER_DISPLAY_TITLE`
- `LPDF_XMP_GWG_TRAIL`

**Vision findings:**

- p1 `placeholder_text` [error]: Placeholder text 'LOT NUMBER' and 'DATE CODE' visible on right side panel - variable data tokens not replaced with actual values ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Ingredients text on left and bottom side panels appears very small, likely at or below 5pt, which may be difficult to read and risky for legal/regulatory compliance ← engine: LPDF_TEXT_001, LPDF_TEXT_LEGIBILITY_VERIFY
- p1 `color_issue` [warning]: Black ingredient text on dark purple/magenta background has low contrast and may suffer from registration issues if not set to overprint or knockout properly ← engine: LPDF_COLOR_006, LPDF_INK_001, LPDF_INK_002, LPDF_INK_003, LPDF_ADV_002, LPDF_ADV_004, LPDF_ADV_005
- p1 `barcode` [warning]: Barcode is rotated 90 degrees and placed on side panel - verify minimum bar height/width and quiet zones meet GS1 standards for scannability ← engine: LPDF_BARCODE_001, LPDF_BARCODE_007, LPDF_BARCODE_008, LPDF_BARCODE_010, LPDF_BARCODE_013, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_029, LPDF_BARCODE_QUIET_ZONE_INK, LPDF_BARCODE_DARK_BG
- p1 `bleed_missing` [warning]: Verify bleed extends beyond trim on all four sides; teal background appears to end near trim edges on top/bottom panels ← engine: LPDF_BOX_003, LPDF_BOX_TRIMBOX_DEFAULTED
- p1 `overprint` [warning]: White text and white logo elements over colored backgrounds - confirm overprint is OFF for white objects to prevent dropout ← **NO ENGINE MATCH**

### Amalgam_Catalyst_9_5x3_5

**Engine:** 38 findings  
**Vision:** 5 findings  
**Expected IDs missed by engine:** AI_DIE_002, AI_SCAN_001, LPDF_AI_CDCC_001, LPDF_BARCODE_014, LPDF_BARCODE_015, LPDF_BARCODE_016, LPDF_BARCODE_017, LPDF_BOX_006, LPDF_COLOR_003, LPDF_COLOR_014, LPDF_OVER_001, LPDF_OVER_004, LPDF_OVER_005, LPDF_SPOT_001, LPDF_SPOT_003, LPDF_SPOT_007, LPDF_STRUCT_003, PDFX4-001, PDFX4-006  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
- `LPDF_BARCODE_001`
- `LPDF_BARCODE_006`
- `LPDF_BARCODE_007`
- `LPDF_BARCODE_008`
- `LPDF_BARCODE_009`
- `LPDF_BARCODE_010`
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_029`
- `LPDF_BARCODE_031`
- `LPDF_BARCODE_QUIET_ZONE_EDGE`
- `LPDF_BOX_003`
- `LPDF_BOX_005`
- `LPDF_BOX_BG_NO_BLEED`
- `LPDF_BOX_TRIMBOX_DEFAULTED`
- `LPDF_GRAIN_MISSING`
- `LPDF_ICC_004`
- `LPDF_INK_001`
- `LPDF_INK_003`
- `LPDF_META_003`
- `LPDF_PATH_002`
- `LPDF_STD_001`
- `LPDF_STD_002`
- `LPDF_STD_003`
- `LPDF_STROKE_003`
- `LPDF_VIEWER_DISPLAY_TITLE`
- `LPDF_XMP_GWG_TRAIL`

**Vision findings:**

- p1 `other` [error]: Page appears essentially blank with only a blue rectangular keyline/die-line visible and no printable artwork inside the live area. ← **NO ENGINE MATCH**
- p1 `spot_color` [warning]: Blue rectangle outline appears to be a die/keyline that may print if not set to a non-printing spot color (e.g., 'Dieline'). ← **NO ENGINE MATCH**
- p1 `hairline_stroke` [warning]: Blue die-line stroke appears very thin and could be below 0.25pt; verify it is set to non-printing regardless. ← engine: LPDF_STROKE_003, LPDF_PATH_002
- p1 `bleed_missing` [warning]: Small gray ink-splatter graphics extend to/beyond the trim crop marks but there is no consistent bleed area filled; if intended as design elements they need full bleed coverage. ← engine: LPDF_BOX_003, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_BG_NO_BLEED, LPDF_BOX_TRIMBOX_DEFAULTED
- p1 `other` [warning]: Stray dark gray spatter/spot marks appear outside the keyline near the trim edges; verify these are intentional design elements and not stray artwork or scanner artifacts. ← **NO ENGINE MATCH**

### Cherry-Twist_OUTLINED

**Engine:** 82 findings  
**Vision:** 8 findings  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
- `LPDF_ADV_005`
- `LPDF_BARCODE_001`
- `LPDF_BARCODE_008`
- `LPDF_BARCODE_009`
- `LPDF_BARCODE_010`
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_029`
- `LPDF_BARCODE_031`
- `LPDF_BARCODE_DARK_BG`
- `LPDF_BARCODE_QUIET_ZONE_EDGE`
- `LPDF_BARCODE_QUIET_ZONE_INK`
- `LPDF_BOX_003`
- `LPDF_BOX_005`
- `LPDF_BOX_006`
- `LPDF_BOX_BG_NO_BLEED`
- `LPDF_BOX_TRIMBOX_DEFAULTED`
- `LPDF_COLOR_006`
- `LPDF_GRAIN_MISSING`
- `LPDF_INK_001`
- `LPDF_INK_002`
- `LPDF_INK_003`
- `LPDF_META_003`
- `LPDF_PATH_002`
- `LPDF_STD_001`
- `LPDF_STD_002`
- `LPDF_STD_003`
- `LPDF_STROKE_001`
- `LPDF_STROKE_003`
- `LPDF_VIEWER_DISPLAY_TITLE`
- `LPDF_XMP_GWG_TRAIL`

**Vision findings:**

- p1 `placeholder_text` [error]: Variable-data placeholder 'LOT NUMBER' visible on right side panel - must be replaced with actual lot number before print ← **NO ENGINE MATCH**
- p1 `placeholder_text` [error]: Variable-data placeholder 'DATE CODE' visible on right side panel - must be replaced with actual date code before print ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Ingredients text (English and French) appears very small, likely below 5pt - verify legibility and compliance with regulatory minimums ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Copyright/manufacturer line on far right side panel appears extremely small (<4pt) - may not be legible when printed ← **NO ENGINE MATCH**
- p1 `barcode` [warning]: UPC barcode is rotated and printed on colored/dark background area - verify sufficient quiet zone and contrast for scanning reliability ← engine: LPDF_BARCODE_001, LPDF_BARCODE_008, LPDF_BARCODE_009, LPDF_BARCODE_010, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_031, LPDF_BARCODE_029, LPDF_BARCODE_QUIET_ZONE_EDGE, LPDF_BARCODE_QUIET_ZONE_INK, LPDF_BARCODE_DARK_BG
- p1 `color_issue` [warning]: White text/elements (e.g., 'NATURALLY FLAVOURED', 'NET 5.3 g', 'ACTIVATE WITH WATER') over colored backgrounds - ensure overprint is OFF to prevent knockout failure ← engine: LPDF_COLOR_006, LPDF_INK_001, LPDF_INK_002, LPDF_INK_002, LPDF_INK_003, LPDF_ADV_002, LPDF_ADV_004, LPDF_ADV_005
- p1 `bleed_missing` [info]: Verify artwork extends fully to bleed lines on all edges - some areas near die-cut/tear line should be checked for adequate bleed ← engine: LPDF_BOX_003, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_BG_NO_BLEED, LPDF_BOX_TRIMBOX_DEFAULTED
- p1 `font_issue` [info]: File named 'OUTLINED' suggests fonts converted to outlines - verify small text remains crisp and has not become heavier/illegible after outlining ← **NO ENGINE MATCH**

### DailyFiber_10up

**Engine:** 83 findings  
**Vision:** 8 findings  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
- `LPDF_ADV_005`
- `LPDF_BARCODE_001`
- `LPDF_BARCODE_010`
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_DARK_BG`
- `LPDF_BARCODE_QUIET_ZONE_INK`
- `LPDF_BOX_003`
- `LPDF_BOX_TRIMBOX_DEFAULTED`
- `LPDF_COLOR_006`
- `LPDF_DIM_CALLOUT_001`
- `LPDF_FONT_005`
- `LPDF_FONT_007`
- `LPDF_GRAIN_MISSING`
- `LPDF_INK_001`
- `LPDF_INK_002`
- `LPDF_INK_003`
- `LPDF_LANG_001`
- `LPDF_LEGALCOPY_001`
- `LPDF_LEGIBILITY_001`
- `LPDF_META_003`
- `LPDF_PATH_002`
- `LPDF_PLACEHOLDER_001`
- `LPDF_STD_001`
- `LPDF_STD_002`
- `LPDF_STD_003`
- `LPDF_STROKE_003`
- `LPDF_TEXT_001`
- `LPDF_TEXT_004`
- `LPDF_TEXT_INVERTED_180`
- `LPDF_TEXT_LEGIBILITY_VERIFY`
- `LPDF_TEXT_REVERSE_THIN`
- `LPDF_VIEWER_DISPLAY_TITLE`
- `LPDF_XMP_GWG_TRAIL`

**Vision findings:**

- p1 `placeholder_text` [error]: Template marker 'Template # 114511' visible on rightmost panel - must be removed before print ← engine: LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001
- p1 `placeholder_text` [error]: Panel labels 'END SEAL', 'FRONT PANEL', 'BACK PANEL', 'Side Panel', 'OVERLAP FIN SEAL', 'UNDERLAP FIN SEAL', 'UNDERLAP HIDDEN AREA' appear as live text on all 10 units - these are template/guide markers that must be removed ← engine: LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001
- p1 `placeholder_text` [error]: Instructional text 'Copy not recommended - Color and Images OK' appears repeatedly across panels - template guidance text that must not print ← engine: LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001
- p1 `small_text` [warning]: Supplement Facts panel and distributor/address copy appears extremely small; verify legibility meets FDA 6pt minimum and reproduces cleanly at press resolution ← engine: LPDF_TEXT_001, LPDF_TEXT_004, LPDF_TEXT_REVERSE_THIN, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_TEXT_INVERTED_180, LPDF_TEXT_LEGIBILITY_VERIFY, LPDF_TEXT_LEGIBILITY_VERIFY, LPDF_TEXT_LEGIBILITY_VERIFY, LPDF_TEXT_LEGIBILITY_VERIFY, LPDF_TEXT_LEGIBILITY_VERIFY
- p1 `barcode` [warning]: UPC barcodes are rendered at very small size with pink background; verify quiet zones, contrast ratio against pink, and scan-test before production ← engine: LPDF_BARCODE_001, LPDF_BARCODE_010, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_QUIET_ZONE_INK, LPDF_BARCODE_DARK_BG
- p1 `color_issue` [warning]: Pink background combined with cyan/blue logo type - confirm CMYK build and that strawberry/lemon photography is CMYK (not RGB) for accurate reproduction ← engine: LPDF_COLOR_006, LPDF_INK_001, LPDF_INK_002, LPDF_INK_003, LPDF_ADV_002, LPDF_ADV_004, LPDF_ADV_005
- p1 `bleed_missing` [warning]: Art appears to terminate at trim/seal edges on top and bottom (END SEAL areas); verify adequate bleed beyond trim on all panels ← engine: LPDF_BOX_003, LPDF_BOX_TRIMBOX_DEFAULTED
- p1 `hairline_stroke` [warning]: Dimension/registration lines and template outline strokes appear very thin; confirm these are non-printing guides and not embedded as printable hairlines ← engine: LPDF_PATH_002, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_TEXT_001

### HSI_OUTLINED

**Engine:** 55 findings  
**Vision:** 5 findings  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
- `LPDF_ADV_005`
- `LPDF_BARCODE_001`
- `LPDF_BARCODE_007`
- `LPDF_BARCODE_008`
- `LPDF_BARCODE_009`
- `LPDF_BARCODE_010`
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_029`
- `LPDF_BARCODE_031`
- `LPDF_BARCODE_DARK_BG`
- `LPDF_BARCODE_QUIET_ZONE_EDGE`
- `LPDF_BARCODE_QUIET_ZONE_INK`
- `LPDF_BOX_003`
- `LPDF_BOX_005`
- `LPDF_BOX_TRIMBOX_DEFAULTED`
- `LPDF_COLOR_006`
- `LPDF_GRAIN_MISSING`
- `LPDF_INK_001`
- `LPDF_INK_002`
- `LPDF_INK_003`
- `LPDF_META_003`
- `LPDF_PATH_002`
- `LPDF_STD_001`
- `LPDF_STD_002`
- `LPDF_STD_003`
- `LPDF_STROKE_001`
- `LPDF_STROKE_003`
- `LPDF_VIEWER_DISPLAY_TITLE`
- `LPDF_XMP_GWG_TRAIL`

**Vision findings:**

- p1 `placeholder_text` [error]: Variable data placeholders 'LOT NUMBER' and 'DATE CODE' visible in white box on right side - must be replaced with actual lot/date data before printing ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Ingredients text on left and bottom panels appears very small (likely below 5pt when printed at 2.44" width) - verify legibility meets regulatory minimums ← **NO ENGINE MATCH**
- p1 `barcode` [warning]: UPC/EAN barcode is rotated and very narrow; verify minimum bar width and quiet zones meet GS1 specs at final printed size ← engine: LPDF_BARCODE_001, LPDF_BARCODE_007, LPDF_BARCODE_008, LPDF_BARCODE_009, LPDF_BARCODE_010, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_031, LPDF_BARCODE_029, LPDF_BARCODE_QUIET_ZONE_EDGE, LPDF_BARCODE_QUIET_ZONE_INK, LPDF_BARCODE_DARK_BG
- p1 `bleed_missing` [warning]: Verify pink/purple background extends fully to bleed line on all four sides - artwork appears to align to trim in some areas near top tear-strip region ← engine: LPDF_BOX_003, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_TRIMBOX_DEFAULTED
- p1 `color_issue` [warning]: Small white text reversed out of magenta/purple background (ingredients, NET 6.9g) - confirm white is set to knockout, not overprint, to prevent disappearing ← engine: LPDF_COLOR_006, LPDF_INK_001, LPDF_INK_002, LPDF_INK_003, LPDF_ADV_002, LPDF_ADV_004, LPDF_ADV_005

### Nutrops_LS_Dieline

**Engine:** 141 findings  
**Vision:** 9 findings  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
- `LPDF_ADV_005`
- `LPDF_BARCODE_001`
- `LPDF_BARCODE_006`
- `LPDF_BARCODE_008`
- `LPDF_BARCODE_009`
- `LPDF_BARCODE_010`
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_028`
- `LPDF_BARCODE_DARK_BG`
- `LPDF_BARCODE_QUIET_ZONE_EDGE`
- `LPDF_BOX_003`
- `LPDF_BOX_006`
- `LPDF_BOX_MULTI_LABEL_PAGE`
- `LPDF_BOX_TRIMBOX_DEFAULTED`
- `LPDF_COLOR_006`
- `LPDF_FONT_005`
- `LPDF_FONT_007`
- `LPDF_GRAIN_MISSING`
- `LPDF_INK_001`
- `LPDF_INK_002`
- `LPDF_INK_003`
- `LPDF_LANG_001`
- `LPDF_LEGALCOPY_001`
- `LPDF_META_003`
- `LPDF_PATH_002`
- `LPDF_PLACEHOLDER_001`
- `LPDF_STD_001`
- `LPDF_STD_002`
- `LPDF_STD_003`
- `LPDF_STROKE_003`
- `LPDF_TEXT_002`
- `LPDF_TEXT_004`
- `LPDF_TEXT_INVERTED_180`
- `LPDF_TEXT_REVERSE_THIN`
- `LPDF_VIEWER_DISPLAY_TITLE`
- `LPDF_XMP_GWG_TRAIL`

**Vision findings:**

- p1 `placeholder_text` [warning]: Panel labels 'FRONT PANEL' and 'BACK PANEL' appear outside the dieline as template markers; ensure these are on a non-printing layer. ← engine: LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001
- p1 `placeholder_text` [error]: Dimension callouts ('21 x 6.5 x 2 Gusset V2', '9.5000"', '21.000"', '6.5000"', '.8750"', '1.5000"', '2.0000"') and the 'PANTONE COLORS 2725C / 7401C' swatch block are dieline/template annotations that must be removed or set to non-printing before plating. ← engine: LPDF_PLACEHOLDER_001, LPDF_PLACEHOLDER_001
- p1 `spot_color` [warning]: Job is specified as 2 Pantone spots (2725C purple, 7401C cream). Verify all art elements (logo, bear icon, type, fruit illustration with multiple shades, barcode) are built only from these two spots plus any allowed tints—lemon/blueberry illustration appears to contain additional colors that may separate as process or extra plates. ← **NO ENGINE MATCH**
- p1 `bleed_missing` [warning]: Confirm purple background extends fully to the bleed line on all four sides of the dieline; some edges (top and bottom gusset flaps) appear close to trim with limited bleed margin. ← engine: LPDF_BOX_003, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_TRIMBOX_DEFAULTED, LPDF_BOX_MULTI_LABEL_PAGE
- p1 `small_text` [warning]: Back-panel legal/disclaimer copy (FDA disclaimer, California Prop 65 warning, distributor address, ingredients line) appears very small—verify it is at least 6pt (4pt minimum for legal) and remains legible after print. ← engine: LPDF_TEXT_002, LPDF_TEXT_002, LPDF_TEXT_002, LPDF_TEXT_004, LPDF_TEXT_REVERSE_THIN, LPDF_TEXT_INVERTED_180
- p1 `color_issue` [warning]: Small reversed (cream-on-purple) body text on the back panel risks fill-in on press; ensure type is built as a single spot (not a tint/overprint build) to avoid registration issues and illegibility. ← engine: LPDF_COLOR_006, LPDF_INK_001, LPDF_INK_002, LPDF_INK_002, LPDF_INK_002, LPDF_INK_002, LPDF_INK_003, LPDF_ADV_002, LPDF_ADV_004, LPDF_ADV_005
- p1 `barcode` [info]: UPC barcode sits in a white knockout box—good for scan contrast—but verify bar width reduction (BWR) for the print process and that the barcode is built in 100% of a dark spot (not a tint or rich build) to ensure scannability. ← engine: LPDF_BARCODE_001, LPDF_BARCODE_006, LPDF_BARCODE_008, LPDF_BARCODE_009, LPDF_BARCODE_010, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_028, LPDF_BARCODE_QUIET_ZONE_EDGE, LPDF_BARCODE_DARK_BG
- p1 `hairline_stroke` [warning]: Dieline/registration guides and thin decorative outlines (bear icon line work, box around 'Lemon Clouds') should be checked to ensure printed strokes are ≥0.25pt; dieline itself must be on a non-printing spot layer. ← engine: LPDF_PATH_002, LPDF_TEXT_002, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_TEXT_002, LPDF_TEXT_002
- p1 `overprint` [error]: Cream-colored type and shapes reversed out of the purple background should be set to knockout, not overprint—overprinting cream on purple will cause the cream to disappear or shift color. Verify overprint settings on all light-on-dark elements. ← **NO ENGINE MATCH**

### Nutrops_SF_Dieline

**Engine:** 140 findings  
**Vision:** 0 findings  
**Vision error:** `Expecting ',' delimiter: line 9 column 31 (char 1644)`  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
- `LPDF_ADV_005`
- `LPDF_BARCODE_001`
- `LPDF_BARCODE_006`
- `LPDF_BARCODE_008`
- `LPDF_BARCODE_009`
- `LPDF_BARCODE_010`
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_028`
- `LPDF_BARCODE_DARK_BG`
- `LPDF_BARCODE_QUIET_ZONE_EDGE`
- `LPDF_BOX_003`
- `LPDF_BOX_006`
- `LPDF_BOX_MULTI_LABEL_PAGE`
- `LPDF_BOX_TRIMBOX_DEFAULTED`
- `LPDF_COLOR_006`
- `LPDF_FONT_005`
- `LPDF_FONT_007`
- `LPDF_GRAIN_MISSING`
- `LPDF_INK_001`
- `LPDF_INK_002`
- `LPDF_INK_003`
- `LPDF_LANG_001`
- `LPDF_LEGALCOPY_001`
- `LPDF_META_003`
- `LPDF_PATH_002`
- `LPDF_PLACEHOLDER_001`
- `LPDF_STD_001`
- `LPDF_STD_002`
- `LPDF_STD_003`
- `LPDF_STROKE_003`
- `LPDF_TEXT_002`
- `LPDF_TEXT_004`
- `LPDF_TEXT_INVERTED_180`
- `LPDF_TEXT_REVERSE_THIN`
- `LPDF_VIEWER_DISPLAY_TITLE`
- `LPDF_XMP_GWG_TRAIL`

### OrangeKiss_OUTLINED

**Engine:** 55 findings  
**Vision:** 6 findings  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
- `LPDF_ADV_005`
- `LPDF_BARCODE_001`
- `LPDF_BARCODE_008`
- `LPDF_BARCODE_009`
- `LPDF_BARCODE_010`
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_029`
- `LPDF_BARCODE_031`
- `LPDF_BARCODE_DARK_BG`
- `LPDF_BARCODE_QUIET_ZONE_EDGE`
- `LPDF_BARCODE_QUIET_ZONE_INK`
- `LPDF_BOX_003`
- `LPDF_BOX_005`
- `LPDF_BOX_TRIMBOX_DEFAULTED`
- `LPDF_COLOR_006`
- `LPDF_GRAIN_MISSING`
- `LPDF_INK_001`
- `LPDF_INK_002`
- `LPDF_INK_003`
- `LPDF_META_003`
- `LPDF_PATH_002`
- `LPDF_STD_001`
- `LPDF_STD_002`
- `LPDF_STD_003`
- `LPDF_STROKE_001`
- `LPDF_STROKE_003`
- `LPDF_VIEWER_DISPLAY_TITLE`
- `LPDF_XMP_GWG_TRAIL`

**Vision findings:**

- p1 `placeholder_text` [error]: 'LOT NUMBER' and 'DATE CODE' appear as placeholder text that should be replaced with variable data before printing ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Ingredients lists in both English and French appear very small (likely below 5pt) and may be difficult to read; verify meets minimum legal/regulatory size requirements ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Copyright/manufacturer line '©2025 ALANI NUTRITION, LLC...' is extremely small and may not be legible when printed ← **NO ENGINE MATCH**
- p1 `barcode` [warning]: UPC barcode is rotated and appears narrow; verify quiet zones and minimum bar width meet scanning requirements (BWR considerations for flexo) ← engine: LPDF_BARCODE_001, LPDF_BARCODE_008, LPDF_BARCODE_009, LPDF_BARCODE_010, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_031, LPDF_BARCODE_029, LPDF_BARCODE_QUIET_ZONE_EDGE, LPDF_BARCODE_QUIET_ZONE_INK, LPDF_BARCODE_DARK_BG
- p1 `bleed_missing` [info]: Verify artwork extends fully to bleed marks on all sides; tropical leaf artwork and color fills should extend beyond trim ← engine: LPDF_BOX_003, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_TRIMBOX_DEFAULTED
- p1 `color_issue` [info]: Vibrant orange/teal/pink colors should be verified as CMYK-achievable or specified as spot colors to ensure brand color consistency ← engine: LPDF_COLOR_006, LPDF_INK_001, LPDF_INK_002, LPDF_INK_003, LPDF_ADV_002, LPDF_ADV_004, LPDF_ADV_005

### Pavette_Pride_v99

**Engine:** 33 findings  
**Vision:** 6 findings  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_004`
- `LPDF_BARCODE_001`
- `LPDF_BARCODE_005`
- `LPDF_BARCODE_007`
- `LPDF_BARCODE_008`
- `LPDF_BARCODE_010`
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_029`
- `LPDF_BARCODE_QUIET_ZONE_INK`
- `LPDF_BOX_003`
- `LPDF_BOX_NO_MARKS_ON_SHEET`
- `LPDF_BOX_TRIMBOX_DEFAULTED`
- `LPDF_COLOR_006`
- `LPDF_FONT_005`
- `LPDF_FONT_007`
- `LPDF_GRAIN_MISSING`
- `LPDF_INK_003`
- `LPDF_LANG_001`
- `LPDF_META_003`
- `LPDF_STD_001`
- `LPDF_STD_002`
- `LPDF_STD_003`
- `LPDF_VIEWER_DISPLAY_TITLE`
- `LPDF_XMP_GWG_TRAIL`

**Vision findings:**

- p1 `hairline_stroke` [warning]: Thin cyan/blue keyline around the circular front label and thin pink/cyan keylines around the back label appear to be hairline strokes that may be die-lines left in the art or will drop out on press if intended to print. ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Multilingual 'Contains Sulfites' translation block on back label appears to be below 4pt and may be illegible when printed. ← **NO ENGINE MATCH**
- p1 `color_issue` [warning]: Rainbow peacock artwork uses highly saturated RGB-style gradients (especially vibrant greens, blues, and purples) that may shift significantly when converted to CMYK. ← engine: LPDF_COLOR_006, LPDF_INK_003, LPDF_ADV_004
- p1 `bleed_missing` [error]: No visible bleed beyond the die-line/keyline edges on either label; circular and rectangular labels appear to end exactly at the cut line. ← engine: LPDF_BOX_003, LPDF_BOX_TRIMBOX_DEFAULTED, LPDF_BOX_NO_MARKS_ON_SHEET
- p1 `barcode` [info]: UPC barcode on back label should be verified for correct width/BWR and minimum quiet zones; ensure it is pure 100% K and not built from process colors. ← engine: LPDF_BARCODE_001, LPDF_BARCODE_005, LPDF_BARCODE_007, LPDF_BARCODE_008, LPDF_BARCODE_010, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_029, LPDF_BARCODE_QUIET_ZONE_INK
- p1 `placeholder_text` [info]: Filename suffix 'v99' and vintage '2025' should be confirmed as final approved values rather than working placeholders. ← **NO ENGINE MATCH**

### Pink-Slush_OUTLINED

**Engine:** 64 findings  
**Vision:** 6 findings  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
- `LPDF_ADV_005`
- `LPDF_BARCODE_001`
- `LPDF_BARCODE_006`
- `LPDF_BARCODE_007`
- `LPDF_BARCODE_008`
- `LPDF_BARCODE_009`
- `LPDF_BARCODE_010`
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_028`
- `LPDF_BARCODE_DARK_BG`
- `LPDF_BARCODE_QUIET_ZONE_EDGE`
- `LPDF_BOX_003`
- `LPDF_BOX_005`
- `LPDF_BOX_006`
- `LPDF_BOX_BG_NO_BLEED`
- `LPDF_BOX_MULTI_LABEL_PAGE`
- `LPDF_BOX_TRIMBOX_DEFAULTED`
- `LPDF_COLOR_006`
- `LPDF_GRAIN_MISSING`
- `LPDF_INK_001`
- `LPDF_INK_002`
- `LPDF_INK_003`
- `LPDF_META_003`
- `LPDF_PATH_002`
- `LPDF_STD_001`
- `LPDF_STD_002`
- `LPDF_STD_003`
- `LPDF_STROKE_001`
- `LPDF_STROKE_003`
- `LPDF_VIEWER_DISPLAY_TITLE`
- `LPDF_XMP_GWG_TRAIL`

**Vision findings:**

- p1 `placeholder_text` [warning]: Variable-data placeholders 'LOT NUMBER' and 'DATE CODE' visible — confirm these are intended as imprint zones, not literal text to print. ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Ingredient lists (English and French) appear very small, likely at or below 5pt; verify legibility meets regulatory minimums. ← **NO ENGINE MATCH**
- p1 `bleed_missing` [warning]: Pink background artwork appears to extend to the trim edge; verify a full 1/8" bleed exists beyond the trim on all sides. ← engine: LPDF_BOX_003, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_BG_NO_BLEED, LPDF_BOX_TRIMBOX_DEFAULTED, LPDF_BOX_MULTI_LABEL_PAGE
- p1 `barcode` [warning]: UPC barcode is rotated and positioned near the edge; confirm minimum quiet zones and that bar width reduction is appropriate for the substrate to maintain scannability. ← engine: LPDF_BARCODE_001, LPDF_BARCODE_006, LPDF_BARCODE_007, LPDF_BARCODE_008, LPDF_BARCODE_009, LPDF_BARCODE_010, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_028, LPDF_BARCODE_QUIET_ZONE_EDGE, LPDF_BARCODE_DARK_BG
- p1 `color_issue` [info]: Bright magenta/pink and teal brand colors — verify whether these are intended spot colors or process build, and confirm color model is CMYK (or CMYK+spot) rather than RGB. ← engine: LPDF_COLOR_006, LPDF_INK_001, LPDF_INK_002, LPDF_INK_002, LPDF_INK_002, LPDF_INK_002, LPDF_INK_003, LPDF_ADV_002, LPDF_ADV_004, LPDF_ADV_005
- p1 `font_issue` [info]: File name indicates 'OUTLINED' — fonts converted to outlines; confirm no text edits are needed since text is no longer editable. ← **NO ENGINE MATCH**
