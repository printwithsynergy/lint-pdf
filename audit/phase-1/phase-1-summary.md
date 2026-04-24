# Phase 1 — Gap mapping (summary)

**Generated:** 2026-04-24
**Inputs:**

- `audit/phase-1/gap-list.json` — 93 canonical gap entries from the playbook (Tier 1-5).
- `audit/phase-0/existing-checks.json` — 373 unique inspection_ids in the engine.

**Outputs:**

- `audit/phase-1/gap-mapping.json` — per-gap match result: present / partial / absent + matched IDs.
- `audit/phase-1/backlog.json` — 49 absent / partial entries with priority scores.
- `audit/phase-1/unmapped-existing.md` — 311 emit-only IDs that fall outside the canonical gap list, with default keep/rename/deprecate recommendations per category.

---

## Headline numbers

**Gap-list coverage (93 entries):**

| Tier | Total | Present | Partial | Absent | Coverage |
|---|---:|---:|---:|---:|---:|
| 1 — Table stakes | 37 | 31 | 0 | 6 | **84 %** |
| 2 — Strong competitive | 21 | 7 | 0 | 14 | 33 % |
| 3 — Dieline differentiators | 15 | 0 | 0 | 15 | **0 %** |
| 4 — Accessibility / archival | 10 | 4 | 0 | 6 | 40 % |
| 5 — Long-tail niche | 10 | 2 | 2 | 6 | 40 % |
| **Total** | **93** | **44** | **2** | **47** | **49 %** |

**Existing-check fan-out:** of the 373 inspection_ids in inventory, **62 map to gap-list entries** (some cover multiple), and **311 are uncatalogued by the canonical taxonomy** (= the "unmapped existing" pile to triage).

## Backlog priority distribution

49 absent + partial entries scored per the playbook formula
(`Base = 110 - (tier × 20)`; `+15` if guidance, `+10` if Tier 3, `−10` if hard & tier > 2; cap 100, floor 1):

| Score band | Count |
|---|---:|
| 90-100 | 6 |
| 70-89 | 27 |
| 50-69 | 2 |
| 30-49 | 6 |
| 1-29 | 8 |

## Top-10 backlog (priority order)

| # | gap_id | Score | Tier | Difficulty | Check |
|---|---|---:|:--:|:--:|---|
| 1 | `T1-CMP01` | 100 | 1 | hard | PDF/X conformance verify (X-1a…X-6) |
| 2 | `T1-CMP02` | 100 | 1 | easy | PDF version check |
| 3 | `T1-CMP03` | 100 | 1 | easy | Encryption / password set |
| 4 | `T1-F04` | 100 | 1 | medium | Protected font (no-embed license bit) |
| 5 | `T1-I07` | 90 | 1 | easy | Missing image / broken reference |
| 6 | `T1-STR04` | 90 | 1 | easy | Page size matches expected |
| 7 | `T2-GWG01` | 85 | 2 | medium | Full GWG 2022 profile set (sheet/web/mag/news/digital/large-format) |
| 8 | `T2-GWG02` | 85 | 2 | medium | Full GWG 2022 packaging profiles (offset/flexo/gravure × product) |
| 9 | `T2-ISO02` | 85 | 2 | medium | ISO 19593-1 Positions taxonomy |
| 10 | `T2-ISO03` | 85 | 2 | easy | ISO 19593-1 White subtypes |

Full ranked list: `audit/phase-1/backlog.json`.

## Notable findings

### Tier-3 dieline coverage is 0 %

The dieline differentiator wedge — 15 checks the playbook flags as **lintPDF's unique competitive position** — has zero `LPDF_DIE_*` finding-emitting analyzers today. The repo has dieline *detection* (`packages/engine/src/lintpdf/analyzers/dieline.py`, 734 LOC) and *AI dieline-by-name* in `ai/analyzers/dieline_detection/dieline_by_name.py`, but those are data-feeding analyzers — they produce dieline regions for the viewer to display. None emit findings like "content on dieline layer" or "dieline z-order wrong" or "barcode quiet zone vs dieline."

This is the single biggest implementation opportunity in the audit. Phase 2 should sequence T3 work after the cheap T1 cleanups so the existing dieline detector can be reused as input to every T3 rule.

### Tier 2 has the biggest tail

14 of 21 Tier-2 checks are absent — mostly GWG 2022 profile coverage (T2-GWG01/02) and ISO 19593-1 spot taxonomy (T2-ISO01..05). Implementing T2-ISO11 spot-name normaliser + T2-ISO05 auto-suggest unlocks T3-D11 (Spot-name heuristic normaliser) for free since they share infrastructure.

### Tier 1 is mostly there

31/37 Tier-1 = 84 % covered. The 6 absents are operationally cheap:
- `T1-CMP01` PDF/X verify (already have `verapdf` Java sidecar; need a shim)
- `T1-CMP02` PDF version check (one-line pikepdf read)
- `T1-CMP03` encryption check (one-line pikepdf read)
- `T1-CMP06` embedded files check (pikepdf trailer walk)
- `T1-F04` protected font (OS/2 fsType bit read)
- `T1-I07` broken image reference (ResourceDict walk + xref check)
- `T1-STR04` page size matches expected (needs an "expected size" config — likely a profile-level field)

### Stub regulatory analyzers caught

The 4 Phase-0 stubs (`AI_ALC_001`, `AI_CANN_001`, `AI_COSM_001`, `AI_ORG_001`) all match Tier-5 entries (T5-N02 cosmetics, T5-N05 alcohol; cannabis has no canonical T5 row but matches the stub pattern). The matcher correctly classifies them as **partial** — the IDs are advertised but bodies return `[]`. Phase 2 work on T5-N02 and T5-N05 is "implement the stub body" rather than "design from scratch."

### Tier 4 a11y has a partial baseline

Tier 4: 4 present (LPDF_ACCESS_001..006 cover Tag-root presence, Alt text, language). 6 absent — including the two big-ticket items (PDF/UA Matterhorn + PDF/A) that need veraPDF integration. The veraPDF sidecar already runs (`Dockerfile.verapdf`, `railway.verapdf.toml`); only an HTTP shim is missing.

### Tier 5 niche

T5-N02 (cosmetics min type size) and T5-N05 (alcohol warnings) are partial via the existing stub analyzers. T5-N03 (FDA Nutrition Facts) is `present` via `AI_FDA_003/004`.

T5-N07 (WCAG contrast on print artwork) is flagged as **UNIQUE — zero engines cover.** No equivalent in PitStop or pdfToolbox. Combined with the Tier-3 dieline checks, this is the second-strongest competitive differentiator in the gap list.

## Unmapped existing checks

311 of 373 inspection_ids (83 %) fall outside the canonical Tier 1-5 list. Default recommendation per the unmapped-existing.md document is **KEEP** for the AI-tier categories (color compliance, barcode-content, regulatory, dieline-detection, etc.) — these are lintPDF's net-new surface beyond the gap list. The MIXED categories (`color`, `image`, `fonts`, `structure`) are mostly Tier-1-supplements (additional checks within the same family) and likely keep with rename / map-to-gap-id for clarity.

The high "unmapped" count is **not a sign of stale code** — it's a sign that lintPDF has grown past the published competitive baselines, particularly in AI-tier checks. Operator decision needed for any specific subset; default action = no change.

## Profile coverage (forward-looking, deferred to Phase 3)

Phase 1 doesn't audit which checks are wired into which preflight profiles. That's Phase 3.1 work. For now, every absent check listed in the backlog needs a "default profile membership" decision in its Phase-2 design note (per playbook §2.1).
