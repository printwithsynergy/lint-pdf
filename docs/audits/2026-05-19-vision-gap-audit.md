# Vision gap audit — 2026-05-19

Engine (CPU checks only, no AI) vs Claude Opus vision on rendered pages.
Max pages per PDF: 2. Corpus: 11 PDFs.

## Summary table

| PDF | Engine findings | Vision findings | Vision-only (gaps) | Engine-only (FP?) |
|-----|:--------------:|:---------------:|:------------------:|:-----------------:|
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | 49 | 5 | 4 | 3 |
| `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | 34 | 5 | 3 | 3 |
| `Amalgam_Catalyst_9_5x3_5` | 23 | 4 | 2 | 1 |
| `Cherry-Twist_OUTLINED` | 78 | 6 | 4 | 2 |
| `DailyFiber_10up` | 74 | 8 | 4 | 2 |
| `HSI_OUTLINED` | 49 | 6 | 3 | 1 |
| `Nutrops_LS_Dieline` | 133 | 8 | 4 | 2 |
| `Nutrops_SF_Dieline` | 132 | 6 | 2 | 2 |
| `OrangeKiss_OUTLINED` | 51 | 6 | 4 | 2 |
| `Pavette_Pride_v99` | 20 | 6 | 5 | 2 |
| `Pink-Slush_OUTLINED` | 60 | 6 | 3 | 1 |

## Vision-only findings (engine misses)

These are issues Claude vision found but the engine produced **zero** matching check IDs.
These are the most actionable gaps.

| PDF | Category | Page | Severity | Description |
|-----|----------|:----:|:--------:|-------------|
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | `placeholder_text` | 1 | error | Placeholder text 'LOT NUMBER' and 'DATE CODE' visible on right side - variable data tokens not yet replaced with actual values |
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | `small_text` | 1 | warning | Ingredients text in both English and French panels appears very small (likely below 5pt) and may be difficult to read when printed |
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | `registration` | 1 | info | Dashed cut/fold lines and dimension marks (2.4409", 5.750", 10mm) visible - ensure these are on a non-printing technical layer |
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | `barcode` | 1 | warning | UPC barcode is rotated vertically and appears compressed/narrow - verify scan quality and minimum bar width at final print size |
| `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | `placeholder_text` | 1 | error | Placeholder text 'LOT NUMBER' and 'DATE CODE' visible on right side panel - variable data tokens not replaced with actual values |
| `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | `barcode` | 1 | warning | Barcode is placed on a narrow side panel with tight quiet zone; verify scannability and that bars are pure K only |
| `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | `registration` | 1 | info | Dashed trim/fold guides and dimension callouts (2.4409", 5.7500", 10mm) are visible in artwork file - confirm these are on a non-printing technical layer |
| `Amalgam_Catalyst_9_5x3_5` | `registration` | 1 | info | Crop marks visible at all four corners of the page; ensure these are outside the trim area and not in the live print area |
| `Amalgam_Catalyst_9_5x3_5` | `other` | 1 | warning | Page appears largely empty with only decorative ink splatter graphics and no content within the trim box; verify this is intentional (possibly a back side or template) and not a missing artwork issue |
| `Cherry-Twist_OUTLINED` | `placeholder_text` | 1 | error | Variable-data placeholder 'LOT NUMBER' visible on right side panel - must be replaced with actual lot data before print |
| `Cherry-Twist_OUTLINED` | `placeholder_text` | 1 | error | Variable-data placeholder 'DATE CODE' visible on right side panel - must be replaced with actual date code before print |
| `Cherry-Twist_OUTLINED` | `registration` | 1 | warning | Dashed guide/fold lines and dimension marks (2.4409", 5.7500", 10mm) visible in artwork area - confirm these are on a non-printing layer |
| `Cherry-Twist_OUTLINED` | `small_text` | 1 | warning | Ingredients/bilingual legal copy on left and right panels appears very small (likely near or below 5pt) - verify legibility meets regulatory minimums |
| `DailyFiber_10up` | `placeholder_text` | 1 | error | Template marker 'Template # 114511' visible on one panel - must be removed before print |
| `DailyFiber_10up` | `placeholder_text` | 1 | error | Panel labels 'FRONT PANEL', 'BACK PANEL', 'END SEAL', 'OVERLAP FIN SEAL', 'UNDERLAP FIN SEAL', 'UNDERLAP HIDDEN AREA', 'Side Panel' appear as live text across all 10-up positions |
| `DailyFiber_10up` | `placeholder_text` | 1 | error | Instructional text 'Copy not recommended - Color and images OK' present in artwork |
| `DailyFiber_10up` | `registration` | 1 | warning | Dimensional callouts/measurement marks (3.483in, 86.41mm, 0.247, 0.500, 0.750 etc.) visible in top-right of layout - technical marks must be outside print area |
| `HSI_OUTLINED` | `placeholder_text` | 1 | error | 'LOT NUMBER' and 'DATE CODE' placeholder text visible on right side panel - needs to be replaced with actual variable data or confirmed as imprint area |
| `HSI_OUTLINED` | `small_text` | 1 | warning | Ingredients text on both English and French panels appears very small, likely at or below 4-5pt, which may be difficult to read and risky for press reproduction |
| `HSI_OUTLINED` | `registration` | 1 | warning | Dashed die/cut lines and 'TEAR ACROSS / DÉCHIRER ICI' guide marks visible - confirm these are on a separate die/technical layer and not printing |
| `Nutrops_LS_Dieline` | `placeholder_text` | 1 | info | Panel labels 'FRONT PANEL' and 'BACK PANEL' visible outside artwork area - confirm these are on a non-printing layer |
| `Nutrops_LS_Dieline` | `registration` | 1 | warning | Dieline/dimension marks and measurements (21 x 6.5 x 2 Gusset V2, 9.5000", 21.000", 6.5000", etc.) visible - ensure dieline layer is set to non-printing |
| `Nutrops_LS_Dieline` | `spot_color` | 1 | info | Document specifies Pantone 2725C and 7401C spot colors - confirm separations are intended as spot vs. converted to CMYK for production |
| `Nutrops_LS_Dieline` | `overprint` | 1 | warning | Light-colored text and bear logo on dark purple - verify these elements are set to knock out (not overprint), otherwise they may disappear |
| `Nutrops_SF_Dieline` | `registration` | 1 | error | Dieline markings, dimension callouts (21 x 6.5 x 2 Gusset V2, 9.5000", 21.000", etc.), and Pantone color swatches (2725C, 7401C) are visible in the artwork area - these must be on a non-printing layer or removed before production |
| `Nutrops_SF_Dieline` | `spot_color` | 1 | info | File uses Pantone 2725C and 7401C spot colors - confirm with printer whether these should be spot or converted to CMYK/process |
| `OrangeKiss_OUTLINED` | `placeholder_text` | 1 | warning | Variable data placeholders 'LOT NUMBER' and 'DATE CODE' visible on right side of label - confirm these will be replaced with actual data at print time |
| `OrangeKiss_OUTLINED` | `registration` | 1 | info | Dashed die-line/cut guides visible inside artwork area - verify these are on a non-printing technical layer |
| `OrangeKiss_OUTLINED` | `small_text` | 1 | warning | Ingredients text on both English and French side panels appears very small (likely at or below 5pt) - verify legibility meets regulatory minimums |
| `OrangeKiss_OUTLINED` | `small_text` | 1 | info | Footnote markers and suggested use text are very small and may be difficult to read after printing |
| `Pavette_Pride_v99` | `hairline_stroke` | 1 | warning | Cyan/blue thin border line around the circular front label appears to be a hairline stroke that may drop out on press |
| `Pavette_Pride_v99` | `hairline_stroke` | 1 | warning | Thin cyan/blue inner border around the back label appears to be a hairline stroke at risk of dropout |
| `Pavette_Pride_v99` | `small_text` | 1 | warning | Multilingual 'CONTAINS SULFITES' translations block on back label appears very small, likely below 5pt and difficult to read |
| `Pavette_Pride_v99` | `registration` | 1 | error | Cyan keylines around both labels may be registration/dieline marks that should be on a non-printing layer rather than printing in live area |
| `Pavette_Pride_v99` | `barcode` | 1 | info | UPC barcode appears clean but verify minimum bar width and quiet zones; surrounding pink keyline is close to barcode area |
| `Pink-Slush_OUTLINED` | `placeholder_text` | 1 | warning | Variable data placeholders 'LOT NUMBER' and 'DATE CODE' visible on right side of label - confirm these are intended as templates to be filled with actual values during production |
| `Pink-Slush_OUTLINED` | `small_text` | 1 | warning | Ingredients text and bilingual usage instructions appear very small (likely 4-5pt), risk of legibility issues on printed product |
| `Pink-Slush_OUTLINED` | `font_issue` | 1 | info | File name indicates 'OUTLINED' - confirm all fonts have been converted to outlines/paths; no embedded font issues should remain but verify no live text needs replacement |

## Engine-only categories (possible false positives or vision blind spots)

Categories where the engine fired but vision saw nothing.

| PDF | Category |
|-----|----------|
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | `font_issue` |
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | `hairline_stroke` |
| `AN-Energy_StickPack_CA_Pink-Slush_P2_OL` | `color_issue` |
| `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | `font_issue` |
| `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | `hairline_stroke` |
| `AN_Energy_StickPack_CA_HSI_ADM_P1_OL` | `color_issue` |
| `Amalgam_Catalyst_9_5x3_5` | `hairline_stroke` |
| `Cherry-Twist_OUTLINED` | `hairline_stroke` |
| `Cherry-Twist_OUTLINED` | `color_issue` |
| `DailyFiber_10up` | `font_issue` |
| `DailyFiber_10up` | `color_issue` |
| `HSI_OUTLINED` | `color_issue` |
| `Nutrops_LS_Dieline` | `font_issue` |
| `Nutrops_LS_Dieline` | `hairline_stroke` |
| `Nutrops_SF_Dieline` | `font_issue` |
| `Nutrops_SF_Dieline` | `color_issue` |
| `OrangeKiss_OUTLINED` | `hairline_stroke` |
| `OrangeKiss_OUTLINED` | `color_issue` |
| `Pavette_Pride_v99` | `font_issue` |
| `Pavette_Pride_v99` | `bleed_missing` |
| `Pink-Slush_OUTLINED` | `hairline_stroke` |

## Per-PDF detail

### AN-Energy_StickPack_CA_Pink-Slush_P2_OL

**Engine:** 49 findings  
**Vision:** 5 findings  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
- `LPDF_ADV_005`
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

- p1 `placeholder_text` [error]: Placeholder text 'LOT NUMBER' and 'DATE CODE' visible on right side - variable data tokens not yet replaced with actual values ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Ingredients text in both English and French panels appears very small (likely below 5pt) and may be difficult to read when printed ← **NO ENGINE MATCH**
- p1 `registration` [info]: Dashed cut/fold lines and dimension marks (2.4409", 5.750", 10mm) visible - ensure these are on a non-printing technical layer ← **NO ENGINE MATCH**
- p1 `barcode` [warning]: UPC barcode is rotated vertically and appears compressed/narrow - verify scan quality and minimum bar width at final print size ← **NO ENGINE MATCH**
- p1 `bleed_missing` [warning]: Artwork extends to edges but bleed area beyond trim should be verified - confirm minimum 1/8" bleed on all sides ← engine: LPDF_BOX_003, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_BG_NO_BLEED, LPDF_BOX_TRIMBOX_DEFAULTED, LPDF_BOX_MULTI_LABEL_PAGE

### AN_Energy_StickPack_CA_HSI_ADM_P1_OL

**Engine:** 34 findings  
**Vision:** 5 findings  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
- `LPDF_ADV_005`
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
- p1 `small_text` [warning]: Ingredients text on left and bottom side panels appears very small (likely under 5pt) and rotated; legibility risk on press ← engine: LPDF_TEXT_001, LPDF_TEXT_LEGIBILITY_VERIFY
- p1 `barcode` [warning]: Barcode is placed on a narrow side panel with tight quiet zone; verify scannability and that bars are pure K only ← **NO ENGINE MATCH**
- p1 `bleed_missing` [warning]: Verify bleed extends fully beyond trim on all four edges - background art appears to stop near trim lines on some edges ← engine: LPDF_BOX_003, LPDF_BOX_TRIMBOX_DEFAULTED
- p1 `registration` [info]: Dashed trim/fold guides and dimension callouts (2.4409", 5.7500", 10mm) are visible in artwork file - confirm these are on a non-printing technical layer ← **NO ENGINE MATCH**

### Amalgam_Catalyst_9_5x3_5

**Engine:** 23 findings  
**Vision:** 4 findings  
**Expected IDs missed by engine:** AI_DIE_002, AI_SCAN_001, LPDF_AI_CDCC_001, LPDF_BARCODE_014, LPDF_BARCODE_015, LPDF_BARCODE_016, LPDF_BARCODE_017, LPDF_BOX_006, LPDF_COLOR_003, LPDF_COLOR_014, LPDF_OVER_001, LPDF_OVER_004, LPDF_OVER_005, LPDF_SPOT_001, LPDF_SPOT_003, LPDF_SPOT_007, LPDF_STRUCT_003, PDFX4-001, PDFX4-006  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ADV_002`
- `LPDF_ADV_004`
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

- p1 `registration` [info]: Crop marks visible at all four corners of the page; ensure these are outside the trim area and not in the live print area ← **NO ENGINE MATCH**
- p1 `bleed_missing` [warning]: Decorative ink splatter elements extend beyond the trim box (blue line) into the bleed area, but several splatters are cut off at the page edge suggesting insufficient bleed coverage on the top and bottom edges ← engine: LPDF_BOX_003, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_BG_NO_BLEED, LPDF_BOX_TRIMBOX_DEFAULTED
- p1 `other` [warning]: Page appears largely empty with only decorative ink splatter graphics and no content within the trim box; verify this is intentional (possibly a back side or template) and not a missing artwork issue ← **NO ENGINE MATCH**
- p1 `color_issue` [warning]: Trim/cut guide line appears in bright blue (likely RGB); ensure this is a non-printing guide layer and not output to plates ← engine: LPDF_ICC_004, LPDF_ICC_004, LPDF_INK_001, LPDF_INK_003, LPDF_ADV_002, LPDF_ADV_004

### Cherry-Twist_OUTLINED

**Engine:** 78 findings  
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
- `LPDF_BARCODE_010`
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

- p1 `placeholder_text` [error]: Variable-data placeholder 'LOT NUMBER' visible on right side panel - must be replaced with actual lot data before print ← **NO ENGINE MATCH**
- p1 `placeholder_text` [error]: Variable-data placeholder 'DATE CODE' visible on right side panel - must be replaced with actual date code before print ← **NO ENGINE MATCH**
- p1 `registration` [warning]: Dashed guide/fold lines and dimension marks (2.4409", 5.7500", 10mm) visible in artwork area - confirm these are on a non-printing layer ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Ingredients/bilingual legal copy on left and right panels appears very small (likely near or below 5pt) - verify legibility meets regulatory minimums ← **NO ENGINE MATCH**
- p1 `barcode` [warning]: UPC barcode is rotated 90° and printed over a dark/colored background area - verify sufficient quiet zone and contrast for scanning ← engine: LPDF_BARCODE_001, LPDF_BARCODE_010, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_029, LPDF_BARCODE_QUIET_ZONE_INK, LPDF_BARCODE_DARK_BG
- p1 `bleed_missing` [warning]: Confirm artwork extends fully to bleed line on all four sides; magenta/teal background appears to stop near trim in some areas ← engine: LPDF_BOX_003, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_BG_NO_BLEED, LPDF_BOX_TRIMBOX_DEFAULTED

### DailyFiber_10up

**Engine:** 74 findings  
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

- p1 `placeholder_text` [error]: Template marker 'Template # 114511' visible on one panel - must be removed before print ← **NO ENGINE MATCH**
- p1 `placeholder_text` [error]: Panel labels 'FRONT PANEL', 'BACK PANEL', 'END SEAL', 'OVERLAP FIN SEAL', 'UNDERLAP FIN SEAL', 'UNDERLAP HIDDEN AREA', 'Side Panel' appear as live text across all 10-up positions ← **NO ENGINE MATCH**
- p1 `placeholder_text` [error]: Instructional text 'Copy not recommended - Color and images OK' present in artwork ← **NO ENGINE MATCH**
- p1 `registration` [warning]: Dimensional callouts/measurement marks (3.483in, 86.41mm, 0.247, 0.500, 0.750 etc.) visible in top-right of layout - technical marks must be outside print area ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Supplement Facts panel text and distributor/address text appears extremely small, likely at or below 4pt - verify legibility minimums for dietary supplement labeling ← engine: LPDF_TEXT_001, LPDF_TEXT_004, LPDF_TEXT_REVERSE_THIN, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_LEGIBILITY_001, LPDF_TEXT_INVERTED_180, LPDF_TEXT_LEGIBILITY_VERIFY, LPDF_TEXT_LEGIBILITY_VERIFY, LPDF_TEXT_LEGIBILITY_VERIFY, LPDF_TEXT_LEGIBILITY_VERIFY, LPDF_TEXT_LEGIBILITY_VERIFY
- p1 `barcode` [warning]: UPC barcodes appear very small on narrow stick-pack panels; verify scan quality and minimum bar width/quiet zone ← engine: LPDF_BARCODE_001, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_QUIET_ZONE_INK, LPDF_BARCODE_DARK_BG
- p1 `bleed_missing` [warning]: Pink background art appears to run to die edges across panels; verify adequate bleed beyond trim/seal lines on all 10 positions ← engine: LPDF_BOX_003, LPDF_BOX_TRIMBOX_DEFAULTED
- p1 `hairline_stroke` [warning]: Thin division/seal guideline strokes between panels may be below 0.25pt - confirm these are non-printing guides only ← engine: LPDF_PATH_002, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_TEXT_001

### HSI_OUTLINED

**Engine:** 49 findings  
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

- p1 `placeholder_text` [error]: 'LOT NUMBER' and 'DATE CODE' placeholder text visible on right side panel - needs to be replaced with actual variable data or confirmed as imprint area ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Ingredients text on both English and French panels appears very small, likely at or below 4-5pt, which may be difficult to read and risky for press reproduction ← **NO ENGINE MATCH**
- p1 `registration` [warning]: Dashed die/cut lines and 'TEAR ACROSS / DÉCHIRER ICI' guide marks visible - confirm these are on a separate die/technical layer and not printing ← **NO ENGINE MATCH**
- p1 `bleed_missing` [warning]: Artwork extends to trim edge (pink/purple background) - verify full 1/8" bleed is present beyond the trim box on all sides ← engine: LPDF_BOX_003, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_TRIMBOX_DEFAULTED
- p1 `barcode` [info]: UPC barcode is rotated 90° and positioned at left edge - confirm minimum quiet zones and that orientation is acceptable for scanning on final package ← engine: LPDF_BARCODE_001, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_029, LPDF_BARCODE_QUIET_ZONE_INK, LPDF_BARCODE_DARK_BG
- p1 `hairline_stroke` [warning]: Thin outlined strokes around 'LOT NUMBER' and 'DATE CODE' boxes and dashed tear lines may be below 0.25pt - verify stroke weights ← engine: LPDF_PATH_002, LPDF_STROKE_001, LPDF_STROKE_003

### Nutrops_LS_Dieline

**Engine:** 133 findings  
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
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_DARK_BG`
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

- p1 `placeholder_text` [info]: Panel labels 'FRONT PANEL' and 'BACK PANEL' visible outside artwork area - confirm these are on a non-printing layer ← **NO ENGINE MATCH**
- p1 `registration` [warning]: Dieline/dimension marks and measurements (21 x 6.5 x 2 Gusset V2, 9.5000", 21.000", 6.5000", etc.) visible - ensure dieline layer is set to non-printing ← **NO ENGINE MATCH**
- p1 `spot_color` [info]: Document specifies Pantone 2725C and 7401C spot colors - confirm separations are intended as spot vs. converted to CMYK for production ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Supplement Facts panel body text, ingredient list, and CALIFORNIA WARNING text appear very small - verify all legally required text meets minimum 6pt (and warnings meet FDA/Prop 65 minimum sizes) ← engine: LPDF_TEXT_002, LPDF_TEXT_002, LPDF_TEXT_002, LPDF_TEXT_004, LPDF_TEXT_REVERSE_THIN, LPDF_TEXT_INVERTED_180
- p1 `barcode` [info]: UPC barcode placed on white knockout panel - verify minimum bar width, quiet zones, and that scale is at least 80% nominal for reliable scanning ← engine: LPDF_BARCODE_001, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_DARK_BG
- p1 `bleed_missing` [warning]: Confirm purple background extends fully past trim/dieline edges on all sides to provide adequate bleed (typically 0.125") ← engine: LPDF_BOX_003, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_TRIMBOX_DEFAULTED, LPDF_BOX_MULTI_LABEL_PAGE
- p1 `color_issue` [info]: Light cream/yellow text and graphics on purple background - verify cream color is built as solid spot 7401C and not as a tint that could appear washed out or cause trapping issues ← engine: LPDF_COLOR_006, LPDF_INK_001, LPDF_INK_002, LPDF_INK_002, LPDF_INK_002, LPDF_INK_002, LPDF_INK_003, LPDF_ADV_002, LPDF_ADV_004, LPDF_ADV_005
- p1 `overprint` [warning]: Light-colored text and bear logo on dark purple - verify these elements are set to knock out (not overprint), otherwise they may disappear ← **NO ENGINE MATCH**

### Nutrops_SF_Dieline

**Engine:** 132 findings  
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
- `LPDF_BARCODE_019`
- `LPDF_BARCODE_020`
- `LPDF_BARCODE_021`
- `LPDF_BARCODE_022`
- `LPDF_BARCODE_023`
- `LPDF_BARCODE_024`
- `LPDF_BARCODE_DARK_BG`
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

- p1 `registration` [error]: Dieline markings, dimension callouts (21 x 6.5 x 2 Gusset V2, 9.5000", 21.000", etc.), and Pantone color swatches (2725C, 7401C) are visible in the artwork area - these must be on a non-printing layer or removed before production ← **NO ENGINE MATCH**
- p1 `spot_color` [info]: File uses Pantone 2725C and 7401C spot colors - confirm with printer whether these should be spot or converted to CMYK/process ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Supplement Facts panel contains very small text (ingredients list, daily value disclaimer, distributor info, California warning) that should be verified to meet minimum 6pt regulatory requirements ← engine: LPDF_TEXT_002, LPDF_TEXT_002, LPDF_TEXT_002, LPDF_TEXT_004, LPDF_TEXT_REVERSE_THIN, LPDF_TEXT_INVERTED_180
- p1 `bleed_missing` [warning]: Verify that purple background art extends fully to the bleed line on all edges of the gusseted bag dieline - bleed appears tight in some areas ← engine: LPDF_BOX_003, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_TRIMBOX_DEFAULTED, LPDF_BOX_MULTI_LABEL_PAGE
- p1 `barcode` [warning]: UPC barcode (8 10205 28008 0) is placed on purple background - ensure background knocks out to white behind barcode and that bar width reduction is applied for flexo/print process to maintain scannability ← engine: LPDF_BARCODE_001, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_DARK_BG
- p1 `hairline_stroke` [warning]: Dieline/cut lines and thin decorative strokes around bear icon outlines should be verified at minimum 0.25pt and confirmed they are on the dieline (non-printing) layer ← engine: LPDF_PATH_002, LPDF_TEXT_002, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_STROKE_003, LPDF_TEXT_002, LPDF_TEXT_002

### OrangeKiss_OUTLINED

**Engine:** 51 findings  
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
- `LPDF_BARCODE_010`
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

- p1 `placeholder_text` [warning]: Variable data placeholders 'LOT NUMBER' and 'DATE CODE' visible on right side of label - confirm these will be replaced with actual data at print time ← **NO ENGINE MATCH**
- p1 `registration` [info]: Dashed die-line/cut guides visible inside artwork area - verify these are on a non-printing technical layer ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Ingredients text on both English and French side panels appears very small (likely at or below 5pt) - verify legibility meets regulatory minimums ← **NO ENGINE MATCH**
- p1 `small_text` [info]: Footnote markers and suggested use text are very small and may be difficult to read after printing ← **NO ENGINE MATCH**
- p1 `barcode` [warning]: UPC barcode placed close to product graphic (flamingo) - verify quiet zones are maintained and contrast is adequate for scanning ← engine: LPDF_BARCODE_001, LPDF_BARCODE_010, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_029, LPDF_BARCODE_QUIET_ZONE_INK, LPDF_BARCODE_DARK_BG
- p1 `bleed_missing` [warning]: Verify background art extends fully to bleed line on all sides; some edges appear to align tightly with trim ← engine: LPDF_BOX_003, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_TRIMBOX_DEFAULTED

### Pavette_Pride_v99

**Engine:** 20 findings  
**Vision:** 6 findings  

**Engine check IDs:**

- `LPDF_ACCESS_001`
- `LPDF_ACCESS_002`
- `LPDF_ACCESS_004`
- `LPDF_ACCESS_012`
- `LPDF_ADV_004`
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

- p1 `hairline_stroke` [warning]: Cyan/blue thin border line around the circular front label appears to be a hairline stroke that may drop out on press ← **NO ENGINE MATCH**
- p1 `hairline_stroke` [warning]: Thin cyan/blue inner border around the back label appears to be a hairline stroke at risk of dropout ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Multilingual 'CONTAINS SULFITES' translations block on back label appears very small, likely below 5pt and difficult to read ← **NO ENGINE MATCH**
- p1 `color_issue` [warning]: Front label peacock artwork uses vibrant rainbow gradients (bright greens, oranges, magentas, purples) that may be out of CMYK gamut and shift on press ← engine: LPDF_COLOR_006, LPDF_INK_003, LPDF_ADV_004
- p1 `registration` [error]: Cyan keylines around both labels may be registration/dieline marks that should be on a non-printing layer rather than printing in live area ← **NO ENGINE MATCH**
- p1 `barcode` [info]: UPC barcode appears clean but verify minimum bar width and quiet zones; surrounding pink keyline is close to barcode area ← **NO ENGINE MATCH**

### Pink-Slush_OUTLINED

**Engine:** 60 findings  
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
- `LPDF_BARCODE_010`
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

- p1 `placeholder_text` [warning]: Variable data placeholders 'LOT NUMBER' and 'DATE CODE' visible on right side of label - confirm these are intended as templates to be filled with actual values during production ← **NO ENGINE MATCH**
- p1 `small_text` [warning]: Ingredients text and bilingual usage instructions appear very small (likely 4-5pt), risk of legibility issues on printed product ← **NO ENGINE MATCH**
- p1 `bleed_missing` [warning]: Artwork appears to extend to the die-cut/trim edge; verify minimum 0.125" bleed beyond trim on all sides - some pink background imagery may be tight to edge ← engine: LPDF_BOX_003, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_006, LPDF_BOX_006, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_005, LPDF_BOX_BG_NO_BLEED, LPDF_BOX_TRIMBOX_DEFAULTED, LPDF_BOX_MULTI_LABEL_PAGE
- p1 `barcode` [warning]: UPC barcode is rotated 90° and printed over a busy/dark background area - verify sufficient quiet zone and contrast for scan reliability ← engine: LPDF_BARCODE_001, LPDF_BARCODE_010, LPDF_BARCODE_019, LPDF_BARCODE_020, LPDF_BARCODE_021, LPDF_BARCODE_022, LPDF_BARCODE_023, LPDF_BARCODE_024, LPDF_BARCODE_029, LPDF_BARCODE_QUIET_ZONE_INK, LPDF_BARCODE_DARK_BG
- p1 `color_issue` [info]: Verify all artwork is CMYK (or correct spot color separations); bright pink/magenta tones suggest possible RGB source - confirm color mode for press ← engine: LPDF_COLOR_006, LPDF_INK_001, LPDF_INK_002, LPDF_INK_002, LPDF_INK_002, LPDF_INK_002, LPDF_INK_003, LPDF_ADV_002, LPDF_ADV_004, LPDF_ADV_005
- p1 `font_issue` [info]: File name indicates 'OUTLINED' - confirm all fonts have been converted to outlines/paths; no embedded font issues should remain but verify no live text needs replacement ← **NO ENGINE MATCH**
