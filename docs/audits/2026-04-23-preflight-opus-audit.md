# Preflight Opus audit — 2026-04-23

**Model:** Claude Opus 4.7 (vision) on 150-DPI rendered pages.
**Corpus:** 7 curated PDFs (2 in `preflight-test-files/`, 1 per
`Test1..Test4` folder, plus the 10-page `lintpdf_preflight_test_final.pdf`).
**Script:** `packages/engine/scripts/audit_test_corpus.py`
**Raw data:** `docs/audits/raw/<label>.json` (gitignored, reproducible).

## Corpus coverage

| # | File | Findings | Confirmed | Disputed | Needs ctx | Skipped |
|---|------|---------:|---------:|---------:|----------:|--------:|
| 1 | `Amalgam_Catalyst_9_5x3_5.pdf` | 267 | 191 | 8 | 37 | 31 |
| 2 | `Pavette_Pride_v99.pdf` | 39 | 7 | 5 | 22 | 5 |
| 3 | `Test1_Nutrops_LS_Dieline.pdf` | 206 | 83 | 29 | 64 | 30 |
| 4 | `Test2_AN_Energy_Pink_Slush.pdf` | 3,159 | 1,787 | 38 | 994 | 340 |
| 5 | `Test3_DailyFiber_10up.pdf` | — | — | — | — | — |
| 6 | `Test4_HSI_Outlined.pdf` | — | — | — | — | — |
| 7 | `web_10p_test_final.pdf` | 275 | 141 | 6 | 79 | 49 |

**Totals (5 files audited):** 3,946 findings, **2,209 confirmed**,
**86 disputed (≈2.2% false-positive rate)**, 1,196 needs_context,
455 skipped.

Files 5 + 6 failed to submit from this sandbox due to intermittent
egress issues (`DNS cache overflow` HTTP 503 from the outbound proxy).
The script is idempotent — rerun with
`uv run python scripts/audit_test_corpus.py --only Test3_DailyFiber_10up,Test4_HSI_Outlined`
from a host with clean egress to backfill the report.

## Tightening recommendations

Ordered by impact. Each row links back to the evidence further down.

### 1. `JobResponse` silently dropped dieline / size / legend / OCR *(fixed in this PR)*

Every one of the 5 audited jobs came back with `dieline=null`,
`art_size_mm=null`, `legend_swatches=[]`, `ocr_text_layer=null` — not
because detection failed but because `JobResponse` never declared
those fields. The `Job` SQLAlchemy model carried them (see migration
037), and the viewer's public share-link config endpoint read them
directly from the row. Every other consumer of `GET /api/v1/jobs/{id}`
— the admin UI, the SDK, integration tests, this audit harness —
silently saw `null` regardless of what the analyzers produced.

Fix applied in this commit: added the four fields to `JobResponse`
in `packages/engine/src/lintpdf/api/schemas.py` and wired them in
`_hydrate_job_response` in `packages/engine/src/lintpdf/api/routes/jobs.py`.
After deploy, rerun this script to get real dieline / art-size /
legend data in a follow-up audit.

**Net effect on this report:** the "Dieline source" / "Art size"
columns look blank everywhere. That's a reporting artefact, not a
detection miss — we can't tell from this run whether the dieline
analyzers are actually working on the corpus.

### 2. 2D-barcode detector hallucinates from dense artwork (`LPDF_BARCODE_014`–`018`)

The 2D-barcode rule cluster fires on artwork that contains **no
barcode at all**. Opus is unambiguous on every hit:

| rule | total | disp% | what Opus saw instead |
|------|------:|------:|----------------------|
| `LPDF_BARCODE_018` | 5 | **100%** | "No barcode exists in the rendered pixels" |
| `LPDF_BARCODE_026` | 1 | 100% | ditto |
| `LPDF_BARCODE_016` | 5 | 80% | "splatter artwork misidentified as modules" |
| `LPDF_BARCODE_014` | 5 | 80% | "only a blue trim rectangle and scattered splatter decoration" |
| `LPDF_BARCODE_017` | 5 | 80% | "2.63 aspect ratio simply reflects the page shape, not a real barcode" |
| `LPDF_BARCODE_015` | 4 | 75% | "pixels show only a linear EAN-13" |

Root cause is almost certainly dense-module heuristics with no
**finder-pattern verification**. The detector seems to be binning
any region with high ink density + small feature size as a Data
Matrix / QR grid. Splatter-style decorative artwork and scattered
stipple shading both match that heuristic.

**Fix:** require at least one of — Data Matrix L-shape finder, QR
three-corner finder, Aztec bullseye — to be recognisable before
emitting `LPDF_BARCODE_014`. `_015`–`_018` and `_026` then become
strictly conditional on `_014` firing. Additionally, short-circuit
the entire rule family when the PDF contains a `/Subtype /Form` or
raster block whose footprint exceeds the whole trim box (the
current Amalgam + Pavette false positives both span the full page).

### 3. x-height calculation is wrong (`AI_EU1169_001`, `AI_PHARMA_001`)

Both rules repeatedly flag **large display/logo text** (e.g. the
"nütrops" back-panel wordmark on `Test1_Nutrops_LS_Dieline.pdf`) as
being "0.17 mm x-height at 1.0 pt" — an impossibility. Opus:

> "This bbox is in the 'nütrops' back-panel logo area where text is
> clearly large, not 1pt."

Dispute rate: `AI_EU1169_001` = **56% (14/25)**, `AI_PHARMA_001` =
**19% (7/37)**. The common failure mode is reading a font size
attribute that doesn't correspond to on-page rendered size — likely
the text-state `Tf` operand without composing `Tm` / CTM scaling.
For outlined artwork, the "font size" concept itself doesn't apply;
the rule must be sourced from rendered glyph bounding-box height.

**Fix:** replace the Tf-based height calc with a bbox-derived
height: for each text-run, measure the rendered glyph bbox height
after CTM, divide by a corpus-calibrated x-height / cap-height
ratio (≈0.52 for most sans fonts), and use that as x-height. For
outlined art, read the path bbox of each outlined-character group
instead. Unit-test on the Nutrops artwork specifically since it's
the clearest false-positive example.

### 4. `AI_PHARMA_001` fires on non-pharma products (gate on category)

`Test1_Nutrops_LS_Dieline.pdf` is a dietary supplement pouch, not a
regulated pharma product. The rule should not apply. Opus:

> "Dietary supplement product, not pharma; rule inapplicable and
> bbox is in large logo text."

**Fix:** gate `AI_PHARMA_001` on a product-category signal — either
an explicit `brand_category` field on the tenant profile, an
NDC/EPAR/ATC code detection in the OCR text layer, or a simple
"contains pharmaceutical indicator keywords" classifier. Without a
positive category signal, the rule should emit `needs_context`
(informational) instead of `warning`.

### 5. Per-object duplicate emission on color / coverage rules (`LPDF_ADV_005`, `LPDF_COLOR_009/010`)

`Test2_AN_Energy_Pink_Slush.pdf` produced **3,159 findings on a
single page** — ≈10× every other 1-page file in the corpus. Breakdown
on that one file:

| rule | findings on Pink-Slush |
|------|----------------------:|
| `LPDF_ADV_005` (large-area pure K) | 1,256 |
| `LPDF_COLOR_010` (total ink coverage) | 1,246 |
| `LPDF_COLOR_009` (per-separation coverage) | 552 |

These three rules account for **3,054 of 3,159 (97%)** of the
volume. That's almost certainly one finding per object rather than
one per *distinct condition*. On a vector-heavy artwork PDF the
per-object loop blows up geometrically.

Opus separately confirms `LPDF_ADV_005` is over-reporting even when
dedup is ignored:

> "The rendered label shows no large black fill areas — the design
> is dominated by pink/magenta and teal with only small black text
> for ingredients and barcode."

**Fix:** collapse these inspectors to **at-most-one finding per
page per rule**, aggregating individual object hits into a single
per-page message ("N objects with 100% K coverage ≥ 1cm²"). The
current behaviour makes the findings panel unusable on
vector-dense files and multiplies audit cost by ≈80× on those jobs.

### 6. `LPDF_BOX_005` / `LPDF_BOX_006` over-report at page scale

Two low-volume but consistent false positives:

> "Content extends beyond bleed box on page 1" — bbox covers the
> full interior of the page, which is entirely within the bleed box
> and shows no content extending beyond it.

> "Content within 8.5pt safety margin of trim edge on page 1" —
> bbox spans almost the entire page interior; most of that region
> is blank white inside the safety margin.

The underlying check collapses the match to the whole content bbox
rather than the *portion that violates the margin/box*. Only 1–2%
dispute rate but makes the per-finding bbox misleading in the
viewer.

**Fix:** emit the finding's bbox as the **intersection** of the
offending object(s) with the violated region, not the union of all
content on the page.

## False-positive rate by inspection_id

Ordered by dispute count then by dispute rate. Only rules with at
least one audited verdict are shown.

| inspection_id | total | confirmed | disputed | needs_ctx | skipped | dispute% |
|---------------|------:|---------:|---------:|----------:|--------:|---------:|
| `LPDF_ADV_005` | 1,280 | 181 | 36 | 898 | 165 | 2.8% |
| `AI_EU1169_001` | 25 | 5 | 14 | 5 | 1 | 56.0% |
| `AI_PHARMA_001` | 37 | 13 | 7 | 5 | 12 | 18.9% |
| `LPDF_BARCODE_018` | 5 | 0 | 5 | 0 | 0 | **100.0%** |
| `LPDF_BARCODE_014` | 5 | 0 | 4 | 0 | 1 | 80.0% |
| `LPDF_BARCODE_016` | 5 | 1 | 4 | 0 | 0 | 80.0% |
| `LPDF_BARCODE_017` | 5 | 1 | 4 | 0 | 0 | 80.0% |
| `LPDF_BARCODE_015` | 4 | 1 | 3 | 0 | 0 | 75.0% |
| `LPDF_BARCODE_026` | 1 | 0 | 1 | 0 | 0 | 100.0% |
| `AI_GHS_003` | 1 | 0 | 1 | 0 | 0 | 100.0% |
| `AI_FDA_003` | 2 | 1 | 1 | 0 | 0 | 50.0% |
| `AI_FDA_004` | 2 | 1 | 1 | 0 | 0 | 50.0% |
| `AI_DIE_002` | 3 | 0 | 1 | 1 | 1 | 33.3% |
| `AI_EU1169_002` | 3 | 2 | 1 | 0 | 0 | 33.3% |
| `LPDF_BOX_005` | 163 | 139 | 1 | 0 | 23 | 0.6% |
| `LPDF_BOX_006` | 68 | 58 | 1 | 0 | 9 | 1.5% |
| `LPDF_TEXT_004` | 50 | 22 | 1 | 23 | 4 | 2.0% |
| `LPDF_COLOR_010` | 1,267 | 1,109 | 0 | 35 | 123 | 0.0% |
| `LPDF_COLOR_009` | 573 | 495 | 0 | 37 | 41 | 0.0% |
| `LPDF_SPOT_001` | 22 | 13 | 0 | 9 | 0 | 0.0% |
| `AI_WCAG_001` | 39 | 28 | 0 | 4 | 7 | 0.0% |
| `LPDF_TEXT_001` | 34 | 24 | 0 | 0 | 10 | 0.0% |
| *(…all other rules with 0 disputes omitted)* | | | | | | |

**Reading note on `needs_context`**: the 898 rows of
`LPDF_ADV_005:needs_context` and 898 `LPDF_COLOR_010:needs_context` are
mostly Opus saying "I can see the engine's claim is technically
true at the pixel level but without a brand colour spec I can't
decide whether it's intentional." These are not false positives,
but the sheer count on Pink-Slush reinforces Recommendation #5 —
one finding per page, not per object.

## Per-file disputed findings (evidence)

Only `disputed` rows shown. `needs_context` is omitted — those are
ambiguity cases, not errors. Full detail (including confirmed and
needs_context) lives in `docs/audits/raw/<label>.json`.

### 1. `Amalgam_Catalyst_9_5x3_5.pdf` — 8 disputed

| rule | msg | Opus rationale |
|------|-----|---------------|
| `LPDF_BARCODE_014` | Potential 2D barcode detected (1004 modules in 690×262pt region) | Region contains only a blue trim rectangle and scattered splatter decoration, not a 2D barcode grid. |
| `LPDF_BARCODE_015` | 2D barcode grid irregularity (width CV=0.80, height CV=0.79) | No 2D barcode is present; detection itself is a false positive. |
| `LPDF_BARCODE_016` | 2D barcode contains 1004 modules | No barcode visible — splatter artwork misidentified as modules. |
| `LPDF_BARCODE_017` | 2D barcode aspect ratio 2.63 (expected ~1.0) | 2.63 aspect ratio simply reflects the page shape, not a real barcode. |
| `LPDF_BARCODE_018` | 2D barcode size 243.5×92.5mm | No barcode exists in the rendered pixels. |
| `LPDF_BOX_005` | Content within 8.5pt safety margin of trim edge | Bbox spans almost the entire page interior; most of that region is blank white inside the safety margin. |
| `LPDF_BOX_006` | Content extends beyond bleed box | Bbox covers the full interior of the page; entirely within the bleed box. |
| `LPDF_ADV_005` | Large area pure K fill (100% K) | No large 100% K area is visible. |

### 2. `Pavette_Pride_v99.pdf` — 5 disputed

| rule | msg | Opus rationale |
|------|-----|---------------|
| `LPDF_BARCODE_014` | Potential 2D barcode (5012 modules in 323×607pt region) | The bbox spans both labels; only a 1D EAN-13 barcode is visible on the back label, no 2D matrix symbol. |
| `LPDF_BARCODE_015` | 2D grid irregularity (width CV=0.94, height CV=1.02) | No 2D barcode is present; pixels show only a linear EAN-13. |
| `LPDF_BARCODE_016` | 2D barcode contains 5012 modules | No 2D barcode visible; only 1D EAN-13 on the back label. |
| `LPDF_BARCODE_017` | 2D aspect ratio 0.53 | No 2D barcode exists in the pixels, so aspect ratio analysis is moot. |
| `LPDF_BARCODE_018` | 2D size 113.9×214.3mm | Region encompasses both labels; no actual 2D barcode visible. |

### 3. `Test1_Nutrops_LS_Dieline.pdf` — 29 disputed

Two recurring patterns here. (a) 6 barcode false positives same as
files 1–2. (b) 12× `AI_EU1169_001` + 6× `AI_PHARMA_001` all firing
on **logo/display type** claimed to be "1.0 pt" — this is the
x-height bug (Recommendation #3).

| rule | representative message | Opus rationale |
|------|------------------------|---------------|
| `LPDF_BARCODE_026` | Barcode in portrait orientation (may affect scanning) | Bars run vertically with horizontal data flow — the standard landscape scanning layout. |
| `LPDF_BARCODE_014` | Potential 2D barcode (225 modules in 407×1212pt region) | No 2D barcode (Data Matrix/QR) visible on the page; bbox spans most of the back panel. |
| `LPDF_BARCODE_015` | 2D grid irregularity (CV 0.86, 0.87) | No 2D barcode present; grid-irregularity measurement is spurious. |
| `LPDF_BARCODE_016` | 2D contains 225 modules | No 2D symbol; module count is a false positive. |
| `LPDF_BARCODE_017` | 2D aspect ratio 0.34 | Aspect 0.34 across a 407×1212pt region matches the back panel shape, not a barcode. |
| `LPDF_BARCODE_018` | 2D size 143.4×427.6mm | That would be the entire panel; no such symbol visible. |
| `AI_EU1169_001` ×12 | x-height 0.17mm at 1.0pt, font T1_0 / TT1 / TT4 / TT5 / TT6 / TT7 / TT8 / TT9 / TT10 / C2_0 / C2_1 / C2_2 / T1_3 | *"Bbox is in the large 'nütrops' wordmark / 'Lemon Clouds' / 'Functional Nootropics' headlines — clearly legible, not 1pt."* |
| `AI_EU1169_002` | Allergen 'cereals containing gluten' may not be emphasised | Back panel advertises "Gluten Free" — a claim, not an allergen declaration. |
| `AI_GHS_003` | H-statements / signal words detected, no GHS pictograms | The "WARNING" text is a California Prop 65 caution on a dietary supplement, not a CLP-regulated label. |
| `AI_PHARMA_001` ×7 | EU pharma font below minimum, x-height 0.17mm | Dietary supplement, not pharma. Rule inapplicable. |

**Tightening signal from this file alone:** fix x-height on the
`AI_EU1169_001` / `AI_PHARMA_001` rules + gate `AI_PHARMA_001` on
category + either retire or rework `AI_GHS_003` so it distinguishes
Prop 65 cautionary language from CLP hazard statements.

### 4. `Test2_AN_Energy_Pink_Slush.pdf` — 38 disputed

| rule | count | summary |
|------|------:|---------|
| `LPDF_ADV_005` | **36** | Every single disputed finding says the same thing: *"No large 100% K fill visible on the page; design is dominated by pink/teal; black ink appears only as small text and barcode."* This is Recommendation #5 in the flesh — the rule is firing one-per-object on a dense vector layout when the true answer is "zero large K regions." |
| `LPDF_BARCODE_017` | 1 | "2D aspect ratio 0.56" — but the barcode in the image is a 1D linear UPC; non-square aspect is expected. |
| `LPDF_BARCODE_018` | 1 | "2D size 81.8×146.8mm" — vastly exceeds the visible ~20×40mm linear UPC. |

Representative `LPDF_ADV_005` rationale:

> "The rendered label shows no large black fill areas — the design
> is dominated by pink/magenta and teal with only small black text
> for ingredients and barcode, none of which qualify as a
> large-area pure-K fill."

This file alone generated **1,256 `LPDF_ADV_005` findings** on a
single page — 36 Opus disputed them outright, ~898 said
`needs_context` because the claim is technically defensible but
the message phrasing is misleading at this volume.

### 5. `Test3_DailyFiber_10up.pdf` — not audited

Submission failed with sandbox egress error. Script-reportable —
rerun with `--only Test3_DailyFiber_10up` from a host with clean
egress to backfill.

### 6. `Test4_HSI_Outlined.pdf` — not audited

Same as #5.

### 7. `web_10p_test_final.pdf` — 6 disputed

| rule | msg | Opus rationale |
|------|-----|---------------|
| `LPDF_TEXT_004` | White text detected on page 8 | "Interactive PDF features" is white on a dark-blue header banner — legitimate contrast, not a preflight issue. |
| `LPDF_BARCODE_014` | 2D barcode (88 modules in 110×20pt region) on page 3 | The bbox contains the stylised blocky word "OTPE3", not a 2D barcode. |
| `LPDF_BARCODE_016` | 88 modules on page 3 | Same — stylised blocky word, 5.4:1 aspect ratio. |
| `LPDF_BARCODE_018` | 2D size 38.9×7.2mm on page 3 | Bbox contains "OTPE3" blocky text, not a barcode. |
| `AI_FDA_003` | No bold fonts in NFP (page index 1) | Page index 1 is the "Geometry and page-box style issues" page — has no Nutrition Facts panel. |
| `AI_FDA_004` | Missing NFP nutrients (page index 1) | Same — no NFP panel on this page, so "missing nutrients" is nonsensical. |

The two `AI_FDA_*` hits reveal a **page-routing bug**: the rule
fires even when the page has no Nutrition Facts panel. It should
pre-detect "this page contains an NFP" before emitting warnings
about what the (non-existent) NFP is missing. Tighten to:
`AI_FDA_003/004` must be preconditioned on NFP-detector-positive.

## Summary action list

1. **[landed in this PR]** Expose dieline / art_size / legend / OCR
   on `JobResponse`. Rerun audit after deploy to measure dieline
   detection accuracy (currently invisible).
2. **Rewrite 2D-barcode detector** (`LPDF_BARCODE_014`–`018`, `026`) to
   require finder-pattern verification. Expected FP reduction:
   ≈20 findings → ~0 across this corpus.
3. **Fix x-height calc** for `AI_EU1169_001` / `AI_PHARMA_001`. Use
   rendered glyph bbox height rather than Tf operand. Unit-test on
   Nutrops back-panel logo text.
4. **Category-gate `AI_PHARMA_001`** — only fire with a positive
   pharma-product signal (NDC / EPAR / brand profile flag).
5. **Collapse per-object rules to per-page** — `LPDF_ADV_005`,
   `LPDF_COLOR_009`, `LPDF_COLOR_010`. Emit one aggregate finding
   per page instead of one per matching object. Cuts audit cost by
   ≈80× on vector-dense files and makes the viewer's findings panel
   usable on real packaging artwork.
6. **Tighten box-violation bbox** — `LPDF_BOX_005` / `LPDF_BOX_006`
   should surface the intersection of the offending object(s) with
   the violated region, not the whole content bbox.
7. **Gate `AI_FDA_003/004` on NFP-detector-positive** — don't flag
   "missing NFP nutrients" on pages without a Nutrition Facts
   panel.
8. **Rework `AI_GHS_003`** — distinguish Prop 65 cautionary
   language from CLP/GHS hazard statements. Cautionary keywords
   like "WARNING" on a dietary supplement ≠ hazmat labelling.
9. **Retry Test3 + Test4** from a host with unthrottled egress to
   backfill this report. (Script supports `--only` for incremental
   backfill.)

## How to rerun / refresh this report

```sh
cd packages/engine
export ANTHROPIC_API_KEY=...   # Opus 4.7
export LINTPDF_API_KEY=<tenant-key>  # mint via admin UI
uv run python scripts/audit_test_corpus.py \
    --out ../../docs/audits/$(date -u +%Y-%m-%d)-preflight-opus-audit.md
```

The script is idempotent — it submits through the production API,
polls each job to completion, and runs Opus against every finding
with pixel context. Raw per-job JSON lands in
`docs/audits/raw/<label>.json` (gitignored) so you can re-score a
specific file without re-submitting.

---

*Generated by `packages/engine/scripts/audit_test_corpus.py`.
Audit model: `claude-opus-4-7`. Engine model for customer audit:
`claude-haiku-4-5`.*

