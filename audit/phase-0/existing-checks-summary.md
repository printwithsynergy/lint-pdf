# Phase 0.2 — Existing checks inventory (summary)

**Generated:** 2026-04-24
**Source of truth:** `audit/phase-0/existing-checks.json` (full machine-readable rows)
**Inputs merged:**

- `packages/app/lib/rules/check-catalog.json` (WS-12 catalog, 142 entries, 47 categories)
- `packages/engine/src/lintpdf/analyzers/**/*.py` — `inspection_id="..."` literals
- `packages/engine/src/lintpdf/ai/analyzers/**/*.py` — same
- `packages/engine/src/lintpdf/reports/check_names.py` — friendly-name registry (142 entries)

---

## Headline numbers

| Metric | Count |
|---|---:|
| Unique `inspection_id`s discovered | **373** |
| In WS-12 catalog (= surfaced in app rules editor) | **142** |
| In `check_names.py` friendly-name registry | 142 |
| With at least one `inspection_id="..."` emit site | 360 |
| Catalog ∩ emit site (catalogued + implemented) | **133** |
| Implemented but NOT in catalog (hidden from rules editor) | **227** |
| Stub analyzers (docstring declares ID, body returns `[]`) | **4** |
| Catalog entry with no source emission found | **5** |
| Needs clarification | **9** |

The big delta — **227 implemented IDs not in the WS-12 catalog** — is the headline signal for Phase 1. Every one of those is an analyzer emitting a finding the rules editor can't surface, which means tenants can't tune severity or disable them. Most are AI-tier checks (barcode subfamily, color compliance subfamily) added after WS-12's catalog export ran. Re-running `packages/engine/scripts/export_check_catalog.py` will likely close most of the gap automatically.

## Status breakdown

| Status | Count | Meaning |
|---|---:|---|
| `implemented` | 133 | In catalog AND analyzer emits it. Healthy. |
| `implemented_uncatalogued` | 227 | Analyzer emits but the WS-12 catalog never picked it up. App rules editor can't show it. |
| `stub_documented` | 4 | Catalog entry exists, analyzer docstring declares it, but `analyze()` returns `[]` (e.g. `AlcoholLabelingAnalyzer.AI_ALC_001`). Requires GPU inference service that isn't wired. |
| `docstring_only_uncatalogued` | 4 | Docstring declares the ID, no catalog entry, no real emission. |
| `catalog_only_no_source` | 5 | Catalog claims it, but neither `inspection_id="..."` nor a docstring declaration was found anywhere — likely emitted via a constant indirection or stale catalog row. |

### Catalog-only mystery (5 IDs that need clarification)

| ID | Hit found in | Verdict |
|---|---|---|
| `LPDF_HAIR_001`, `LPDF_HAIR_002` | `reports/check_names.py` only | Likely renamed to `LPDF_STROKE_*` already in catalog. Stale entry. |
| `AI_RSYM_001` | `ai/analyzers/text_analysis/text_as_outlines.py` (docstring), `reports/check_names.py` | Real analyzer but emit pattern not via `inspection_id="..."`. |
| `AI_SCAN_001` | `ai/analyzers/symbol_detection/regulatory_symbols.py`, `ai/analyzers/text_analysis/text_as_outlines.py`, `profiles/orchestrator.py` | Real analyzer hit; emit-site pattern is non-literal. |
| `AI_TAO_001` | `reports/check_names.py` only | Stub or stale. |

These 9 (`needs_clarification`) all carry `needs_clarification: true` in the JSON.

## Category distribution (top 25)

| Category | Count |
|---|---:|
| `ai_color_compliance` | 38 |
| `barcodes` | 28 |
| `ai_barcode` | 25 |
| `color` | 24 |
| `image` | 17 |
| `advanced` | 15 |
| `fonts` | 14 |
| `structure` | 14 |
| `accessibility` | 13 |
| `strokes` | 12 |
| `spot_colors` | 11 |
| `ai_regulatory_compliance` | 10 |
| `packaging` | 10 |
| `page_geometry` | 9 |
| `color_management` | 9 |
| `document` | 8 |
| `overprint` | 8 |
| `transparency` | 7 |
| `ai_other` | 7 |
| `annotations` | 6 |
| `other` | 5 |
| `ai:fda` | 5 |
| `ai_image_analysis` | 5 |
| `ai_symbol_detection` | 5 |
| `prepress` | 5 |

62 distinct categories total. Catalog uses two parallel naming conventions (`ai:fda`, `ai:alcohol` — colon style) alongside the inferred `ai_*` (underscore style) categories from analyzer subdir paths. That naming inconsistency should be normalised before Phase 1 priority scoring relies on category buckets.

## Severity distribution

| Severity | Count |
|---|---:|
| `warning` | 78 |
| `advisory` | 57 |
| `error` | 7 |
| unspecified (in JSON: `null`) | 231 |

The 231 unspecified are the 227 implemented-uncatalogued + 4 docstring-only — they have no catalog row, so no `default_severity`. Engine-side severity defaulting must be inspected separately (likely each `Finding(...)` emit passes its own `severity=...` keyword).

## Notable gaps spotted inline

1. **Catalog freshness drift.** 227 of 360 implemented checks (≈63%) aren't catalogued. Scripts/export_check_catalog.py needs to run as a CI step or pre-commit hook.
2. **Naming convention split.** Both `ai:fda` (catalog) and `ai_regulatory_compliance` (inferred) coexist. Pick one.
3. **Stub analyzers documented as if real.** `AlcoholLabelingAnalyzer`, `CannabisAnalyzer`, `CosmeticsAnalyzer`, `OrganicAnalyzer` all return `[]` but advertise `AI_ALC_001`/`AI_CANN_001`/etc. in docstrings + catalog. The catalog will surface them in the rules editor, where tenants can toggle severity, but the engine never emits — silent no-op. Mark these in Phase 1 backlog as Tier-3 implementation work.
4. **Hairline rule renaming half-done.** Catalog still carries `LPDF_HAIR_001`/`LPDF_HAIR_002` but the engine emits `LPDF_STROKE_*`. Drop the stale entries.
5. **Two-tier ID space.** `LPDF_*` (deterministic) and `AI_*` (model-backed) coexist. Phase 1 backlog should keep them separate so AI checks aren't forced through deterministic-rule QA gates.

## How to read the JSON

`audit/phase-0/existing-checks.json` is the authoritative dataset. Top-level keys:

- `totals` — headline counts.
- `status_counts`, `category_counts`, `severity_counts` — pre-aggregated buckets.
- `checks[]` — per-check rows. Each row has:
  - `id`, `category_id`, `category_label`, `name`, `description`, `default_severity`
  - `status` — one of `implemented`, `implemented_uncatalogued`, `stub_documented`, `docstring_only_uncatalogued`, `catalog_only_no_source`
  - `in_ws12_catalog`, `in_check_names_registry` — booleans
  - `emit_sites[]` — `[{file, line}]` for every `inspection_id="..."` literal
  - `docstring_declarations[]` — `[{file, line}]` only when no emit site exists
  - `source_files[]` — deduped union of the above
  - `needs_clarification` — boolean; true when row warrants a Phase 0 Q&A

## What's NOT in this inventory

- Profiles (which checks belong to which profile) — covered separately by Phase 0.3 / blast-radius and a Phase 1 follow-up.
- Per-check thresholds (the `_threshold_keys` columns from the catalog generator) — preserved in catalog but not reprojected here.
- Test coverage per check — Phase 0.3 (blast radius) records test-file presence per analyzer module, which is the closest proxy.
- Runtime tier (`gpu` vs `cpu`) and `credits_per_run` from each `BaseAIAnalyzer` subclass — useful for cost modelling in Phase 1, deferred.
