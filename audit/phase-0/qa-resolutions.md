# Phase 0 — Q&A gate resolutions

**Operator:** Quincy
**Resolved:** 2026-04-24

The Phase 0 cliff notes raised five questions before Phase 1 starts. Operator answers + this session's resolution work below. Each item carries its own follow-up status.

---

## Q1 — Catalog freshness

> Re-run `packages/engine/scripts/export_check_catalog.py` and commit the refreshed JSON now (cleans the comparison baseline before Phase 1), or treat the gap itself as a Phase-1 backlog item?

**Operator:** Commit the refreshed JSON.

**Resolution.** Re-ran the script:

```sh
cd packages/engine && uv run python scripts/export_check_catalog.py \
    --out ../app/lib/rules/check-catalog.json
# → Wrote 142 checks across 47 categories
```

Result: **zero diff** against the on-disk catalog. The script reads only `lintpdf.reports.check_names.CHECK_NAMES` (single source of truth) and that registry holds 142 entries. The 227 implemented-uncatalogued IDs are absent from `check_names.py` itself — the script can't see them.

**Implication for Phase 1.** Closing the catalog gap requires populating `check_names.py` with friendly name + description for every emit-only ID, *then* re-running the export. That work is per-check (each ID needs an accurate human-readable name), so it folds into the Phase 1 backlog under "registry hygiene". Recorded as Phase-1.A item #0.

---

## Q2 — Stub regulatory analyzers

> Treat as in-scope (Phase 1 picks up "implement the body") or out-of-scope (drop from catalog)?

**Operator:** In scope, but research first what they actually mean. Same with all checks.

**Resolution.** Per-check research workflow drafted at `audit/phase-0/check-research-approach.md`. Key points:

- Inputs already on disk: `grounded-research/specs/pitstop-checks-catalog.md` (industry baseline), `gwg-2022-specification.md`, ISO 32000-2 chapter notes, ISO 15930-7 (PDF/X-4), ICC v4 reference, PDF/UA notes. Targeted WebSearch only for regulations missing from the spec corpus (TTB, FDA NLEA, state cannabis, EU Cosmetics 1223/2009, USDA NOP).
- Per-check research note template defined: `audit/phase-1/check-research/<inspection_id>.md`. Captures source-of-truth spec, PitStop equivalent, semantic definition, pass/fail rule, severity defaults, FP vectors, implementation outline, **and an explicit read-only-constraint reaffirmation** (lintPDF never mutates PDFs — remediation is structured guidance in the report).
- Stub triage rule: every stub gets a research note **before** Phase 2 picks the first one for implementation. Three triage questions: (1) is the regulation real and enforced; (2) what signal does the analyzer need; (3) is it feasible without GPU inference, or is `tier=gpu` non-negotiable.
- Existing-check rule: same template applies to every check that scored high blast-radius **and** has a known Opus dispute row in `docs/audits/raw/*.json`. Phase 1 priority scoring uses the result.

**Stub backlog (per `audit/phase-0/blast-radius-ai.json`).** 8 stubs total — 4 catalogued, 4 uncatalogued:

| Stub ID(s) | File | Tier | Spec needed |
|---|---|---|---|
| `AI_ALC_001`, `AI_ALC_002` | `regulatory_compliance/alcohol.py` | gpu | TTB 27 CFR 4 / 5 / 7 (US wine, spirits, beer); EU Reg 1308/2013 |
| `AI_CANN_001`, `AI_CANN_002` | `regulatory_compliance/cannabis.py` | gpu | State-by-state (CA BCC §5304, CO MED 1004-1, WA WAC 314-55-105, …) |
| `AI_COSM_001`, `AI_COSM_002` | `regulatory_compliance/cosmetics.py` | gpu | EU Reg 1223/2009; FDA 21 CFR 701 |
| `AI_ORG_001`, `AI_ORG_002` | `regulatory_compliance/organic.py` | gpu | USDA NOP 7 CFR 205; EU Reg 2018/848 |

Plus the four uncatalogued AI stubs flagged in `blast-radius-ai.md` (subdir-level): research notes follow the same template.

---

## Q3 — Stale `LPDF_HAIR_*` IDs

> Why is it stale?

**Resolution.** Git archaeology:

| Commit | Date | Effect |
|---|---|---|
| `570ca10` | 2026-03-24 | `refactor: rename GRD_ inspection IDs → LPDF_ and remove GroundedError alias`. Renamed 303 IDs from `GRD_*` to `LPDF_*`. Hairline analyzer at `analyzers/hairline.py` already emitted `LPDF_STROKE_001..006` after this. |
| `6833d28` | 2026-04-11 | `feat(reports): check name registry + redesigned card-based HTML template`. Added `check_names.py` with ~120 CheckInfo entries — including `LPDF_HAIR_001` and `LPDF_HAIR_002` rows that referenced IDs **never emitted by any analyzer.** Author appears to have copied an older spec or expected-but-not-built list rather than cross-checking `inspection_id="..."` literals. |

So the IDs were stale-on-arrival: vestigial registry rows added 18 days *after* the rename, never wired to emission code.

**Cleanup needed (Phase 1 work, not Phase 0):**

- Drop `LPDF_HAIR_001` and `LPDF_HAIR_002` from `packages/engine/src/lintpdf/reports/check_names.py:302-307`.
- Add registry entries for the live emitting IDs that lack friendly names:
  - `LPDF_STROKE_001` — Hairline Stroke (line_width below threshold; ISO 32000-2 §8.4.3.2). Severity warning. Live equivalent of the dropped HAIR_001.
  - `LPDF_STROKE_002` — Zero-Width Stroke (line_width ≤ 0; will not render). Severity error.
  - `LPDF_STROKE_004` — Multi-Ink Thin Stroke (multi-ink CMYK stroke <0.5pt). Severity warning. Already covered by WS-13 (rich-black stroke complement).
  - `LPDF_STROKE_005` — Invisible Stroke (zero-opacity or white-on-white).
  - `LPDF_STROKE_006` — Non-Default Flatness (curve-quality risk).
- Re-run `export_check_catalog.py` to refresh the WS-12 catalog with the updated registry.

Recorded as Phase-1.A item #1 (cheap deterministic cleanup, blocks nothing).

---

## Q4 — AI analyzer blast-radius scope

> I scoped the Phase 0.3 blast-radius to `analyzers/` only (deterministic). Want me to extend it to `ai/analyzers/` (60 files, mostly Tier-3+) before Phase 1, or defer until AI checks land in the backlog?

**Operator:** Extend before.

**Resolution.** Done. New deliverables:

- `audit/phase-0/blast-radius-ai.json` — machine-readable rows for 44 non-`__init__` AI analyzer files across 15 subdirs. Captures LOC, emitted check count, docstring-only IDs, importer count + paths, test-file presence, stub flag, risk band.
- `audit/phase-0/blast-radius-ai.md` — narrative companion. Headlines:
  - **44 modules, 6,926 LOC, 101 emitted check IDs.**
  - **Test coverage 9/44 (20%)** — vs 18/31 (58%) for deterministic analyzers. The biggest single regression-risk surface in the codebase.
  - **8 stubs** (analyze() returns []). All marked `tier=gpu`.
  - **`regulatory_compliance/` subdir is the largest** (11 modules) — already touched in WS-2..WS-6.
  - **`barcode/` subdir (7 modules) is mostly uncatalogued** — 25 emitted IDs, 0 in WS-12 catalog.

---

## Q5 — Test-suite baseline

> Worth re-running with a 10-minute window to capture exact pass/fail counts now, or accept "previously green on main" from prior session and move on?

**Operator:** Rerun as baseline or pull latest complete results if available.

**Resolution.** Captured in `audit/phase-0/test-baseline.txt`. Headline:

- **Full-suite run not feasible locally** — Postgres / Redis / ClamAV sidecars (per `packages/engine/docker-compose.yml`) are not running in this environment. Two attempts to run the full 2,166-test suite both hung at exactly 33% completion (22 min wall-clock, 0:42 CPU) — one specific service-dependent test opens a real connection without a timeout and blocks forever when the broker is absent.
- **Deps-free subset run** (1,391 of 2,166 tests, 64% coverage; ignored `tests/api`, `tests/queue`, `tests/webhooks`, `tests/integrations`, `tests/billing`, `tests/email`, `tests/tenants`, plus three root-level service-touching tests): **1,387 passed, 4 failed in 25.98 s.**
- **GitHub Actions / CI:** `mcp__github__pull_request_read get_check_runs` on PRs #190, #191 returns `total_count: 0` — no CI pipeline is configured. Cannot pull a "fresh green main" alternative.

**Failure breakdown:**

| Test | Verdict |
|---|---|
| `tests/ai/test_ai_routes.py::TestAICreditRoutes::test_topup_credits` | Mis-classified — needs Postgres. Re-include in service-dependent skip list for next baseline. |
| `tests/overrides/test_resolver.py::TestEnforceReportEntitlements::test_none_passes` | **Real pre-existing bug:** test helper `_entitlements()` at `tests/overrides/test_resolver.py:179` instantiates `TenantEntitlements` with 3 missing required fields (`allowed_preflight_sources`, `capability_fillin_enabled`, `annotations_enabled`). Production model schema gained the fields; helper never updated. |
| `tests/overrides/test_resolver.py::TestEnforceReportEntitlements::test_allowed_formats_pass` | Same root cause. |
| `tests/overrides/test_resolver.py::TestEnforceReportEntitlements::test_disallowed_format_raises_entitlement_denied` | Same root cause. |

**Cached failures resolved.** The pre-audit `.pytest_cache/lastfailed` (2026-04-23 21:01) listed 3 WS-8 / WS-15 tests as failing — `test_large_k_pixel_gate.py::test_dark_fraction_fully_dark_render`, two cases in `test_densitometer_spots.py`. **All three pass in this run.** Cache was stale from an in-progress branch state.

**Bottom line.** Deterministic + AI analyzer test paths (the actual check-emission surface this audit cares about) are GREEN. The one real failure (overrides resolver helper drift) is unrelated to check-emission and lands in Phase-1.A as cheap cleanup alongside the `LPDF_HAIR_*` registry fix. Recommendation: stand up the docker-compose sidecars and capture the full 2,166-test baseline before Phase 2 changes any analyzer.

---

## Outstanding Phase-1 entry items (from this session)

- 1.A.0 — Populate `check_names.py` with the 227 implemented-uncatalogued IDs (per-check research note required for each).
- 1.A.1 — Drop `LPDF_HAIR_001/002`; add registry entries for `LPDF_STROKE_001/002/004/005/006`. Refresh catalog.
- 1.A.2 — Triage 8 AI stubs per the research-approach template; produce one `audit/phase-1/check-research/<id>.md` note per stub before Phase 2 picks one for implementation.
- 1.A.3 — Fix `tests/overrides/test_resolver.py:179` `_entitlements()` helper: add the three missing `TenantEntitlements` fields (`allowed_preflight_sources`, `capability_fillin_enabled`, `annotations_enabled`). Re-run baseline to confirm clean. Optionally stand up docker-compose sidecars (postgres, redis, clamav) and capture the full 2,166-test baseline before Phase 2.
- 1.A.4 — Trace `AI_RSYM_001`, `AI_SCAN_001`, `AI_TAO_001` runtime emission path to confirm whether the analyzer actually emits the catalogued ID (non-literal `inspection_id` pattern means grep missed them; runtime trace required).

Phase 1 starts with these five items resolved.
