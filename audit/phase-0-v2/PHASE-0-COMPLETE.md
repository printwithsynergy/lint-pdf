# Phase 0 — Complete

**Date:** 2026-04-25
**Operator:** Quincy

## Cliff-notes summary

**Repo:** Monorepo (pnpm + turbo). 9 packages. Engine ~25K LOC Python; App ~30K LOC TS; viewer subcomponent ~8.3K LOC TS; desktop ~4.4K LOC TS.

**Tests:** 185 engine pytest files; 65 app Vitest + 16 Playwright E2E specs. Pre-commit: ruff/mypy/typecheck/lint enforced.

**v1 baseline (already merged to main):** 93/93 v1 gaps closed; 421 inspection IDs in catalog; 38 analyzers; 60+ profiles; full conformance (PDF/X / PDF/A / PDF/UA / PDF/VT). LLM (Anthropic) integrated for audit + dieline + legend + OCR.

**v2 universe vs v1 catalog (rough projection):** 412 artifacts (84 Tier-0 + 328 user-facing). Coarse coverage:
- Strong (>80%): F (Fonts), I (Images), C (Color & Ink) — ~85% each
- Mid (50–80%): WF, T (Trapping), LA (Line Art)
- Low (<50%): TR, S (Substrate), BR (Braille), P (Page Geometry), D (Dieline expansion), ISO, W (White/Varnish)
- **0%:** Tier-0 primitives (84 absent), EPM module, V (Variable Data)

**v2 infrastructure gaps (ranked):**
1. Tier-0 primitive registry (84 absent) — 3.0 EM, blocks everything
2. `remediation` field on FindingResponse — additive schema change
3. Workflow first-class entity — pre-req for §16
4. Toggle registry + cascade resolver — pre-req for any new toggle
5. Lockable toggles — §16.2
6. Config audit log — §16.5
7. Operator-decision schema + viewer drawer — Wave V V-03..V-05
8. Webhook idempotency + outbox state — V-06
9. Per-tenant theming — V-11
10. Device-link engine — EPM-Advanced unblocker
11. BYO §9 schema endpoint — Phase 2.EPM.5
12. PDF/UA Matterhorn HTTP shim around veraPDF

**BYO readiness:** Vendor-format imports (PitStop / Callas / Acrobat / lintpdf-native / custom) shipped at `imports/`. v2 §9 BYO (pre-computed analysis JSON, substitute-for-preflight) is **greenfield** — different semantics, different schema.

**Viewer:**
- Renderer: **canvas + pre-rendered PNG tiles** (NOT pdf.js, NOT mupdf-wasm)
- Existing overlays: TAC heatmap, separation panel, dieline overlay, finding boxes, OCG layers, mobile drawer, approval chain panel
- Coordinate system: user-space at emit; pixel-space at render (server-baked)
- Layer toggle pattern: right-sidebar checkbox list (mature)
- Operator-decision persistence: greenfield (no per-finding decision table)

**Config cascade:**
- Tenant config: `Prisma Tenant.settings` open JSON; entitlements via `TenantEntitlements`
- Workflow concept: **absent** (no first-class entity; profiles + brand specs + endpoints + approval chains are independent scopes, not composite)
- Per-call overrides: form fields on `POST /v1/jobs` (profile_id, brand, external_format, etc.)
- Precedence: per-call > tenant; documented in CLAUDE.md only; **inconsistent merge across endpoints**
- Lockable toggles: **absent**
- Audit logging: **absent for config changes** (Job audit field exists for AI verdict only)
- EPM threshold location: **all hardcoded** in analyzers

**Surface parity (API / SDK / desktop):**
- Same canonical store: yes (server-side; desktop is local mirror)
- Toggle ID consistency: yes (no drift on check IDs / profile IDs / layer IDs)
- Desktop offline mode: **no** (every preflight requires server round-trip)

**Production readiness:** Clean — 0 prod-path TODOs; 5 acceptable AI-stub flags. v2 principle 13 grep-CI gate is achievable today.

**Legacy patterns flagged for remediation:** **14 rows** in `0.7-config-cascade-audit.md` §0.7.2.

## Phase 0 deliverables

| File | Lines | Status |
|------|------:|--------|
| `audit/phase-0-v2/0-bootstrap.md` | 73 | ✅ |
| `audit/phase-0-v2/0.1-repo-inventory.md` | 525 | ✅ |
| `audit/phase-0-v2/0.2-v1-v2-projection.md` | 193 | ✅ |
| `audit/phase-0-v2/0.2-v1-v2-projection.json` | (machine-readable) | ✅ |
| `audit/phase-0-v2/0.3-infrastructure-inventory.md` | 78 | ✅ |
| `audit/phase-0-v2/0.4-blast-radius.md` | 168 | ✅ |
| `audit/phase-0-v2/0.5-byo-readiness.md` | 129 | ✅ |
| `audit/phase-0-v2/0.6-viewer-infrastructure.md` | 166 | ✅ |
| `audit/phase-0-v2/0.7-config-cascade-audit.md` | 241 | ✅ |
| `audit/phase-0-v2/0.8-surface-parity.md` | 107 | ✅ |

**Deferred to operator paste-save** (per §0.0 trade-off):
- `lintpdf-check-audit-playbook-v2.md` at root + audit/
- `lintpdf-v2-universe-enumeration.md` at root + audit/

If you say "retype" I'll write them via Bash heredoc chunks. Until then,
the v2 playbook content lives in conversation context as authoritative
reference for this session.

## Numbered questions before Phase 1

The playbook (§0 Q&A gate) requires Quincy to answer before Phase 1 begins.
INTJ-friendly: 5 grouped questions, each with options.

### 1. Wave V pre-requisites — confirm sequencing?

Wave V V-07 (toggle resolver) + V-08 (audit log) + V-12 (legacy migration)
**must** ship before any new check / threshold introduces a configurable
knob, per playbook principle 13 ("legacy patterns are migrated, not
grandfathered"). This means:

- **(a)** Wave V V-07 + V-08 + V-12 ship FIRST, before Wave 0 Tier-0
  primitives → before all check waves
- **(b)** Wave V V-07 + V-08 + V-12 ship in parallel with Tier-0 primitives;
  no new toggleable knobs land until V-12 completes
- **(c)** Defer V-07 / V-08 / V-12 — accept inconsistent foundation; ship
  Tier-0 + Wave A/B first; remediate later (violates §17.3)

Recommend **(b)** — parallel; primitive registry has no toggleable
knobs; Wave A's first toggleable knob waits for V-07.

### 2. Remediation plan approval?

`0.7-config-cascade-audit.md §0.7.2` lists 14 remediation rows. Hardest:

- **R-Q4:** Workflow first-class entity (additive but breaking; new
  Prisma model + tRPC router + UI + desktop sync)
- **R-Q1:** `TenantConfig` typed model deprecating freeform
  `Tenant.settings` (migration in V-12)
- **R-Q3:** `ConfigAuditLog` Prisma table (additive, low risk)

Approve all 14 remediation rows as listed, or want individual review per row?

- **(a)** Approve as listed; proceed with Wave V V-07/V-08/V-12 design
- **(b)** Review row-by-row in a follow-up batch
- **(c)** Modify specific rows before approval — which ones?

### 3. v2 playbook + universe enumeration — disk persistence?

The two files are deferred. Options:

- **(a)** Operator paste-saves them now in terminal (faster, ~30 sec)
- **(b)** Assistant retypes via Bash heredoc chunks (~15 tool calls, ~30K
  tokens of output context)
- **(c)** Defer until end of Phase 1 — conversation context is authoritative
  in the meantime

Recommend **(a)**; if not feasible, **(c)** is acceptable.

### 4. Phase 1 backlog scope — fine-grained ID projection?

Phase 0.2 produced a coarse category-level v1→v2 projection. Phase 1
backlog generation needs fine-grained per-ID mapping (every v2 ID gets
a `present | partial | absent` status).

- **(a)** Run a full per-ID projection in Phase 1.1 (semantic match every
  v2 ID against engine emit-sites; ~2–3 day exercise)
- **(b)** Run a heuristic projection in Phase 1.1 + manual triage of edge
  cases in batch ahead of each wave
- **(c)** Skip projection; treat every v2 ID as net-new, accept
  re-implementation of overlapping checks

Recommend **(b)** — heuristic + per-wave triage.

### 5. Phase 5 (docs/marketing/legacy reconcile) — incremental or end-loaded?

Per playbook §5.8: incremental Phase 5 ships per-release subset; full Phase
5 ships at major version boundaries. v2 is a major boundary. Options:

- **(a)** Incremental Phase 5 after each wave (V, EPM, A, D, C, E)
- **(b)** Single end-loaded Phase 5 sweep at v2.0 release
- **(c)** Hybrid: incremental for code-facing docs (OpenAPI, Postman, SDK
  reference) per wave; end-loaded for marketing site / sales collateral

Recommend **(c)** — incremental docs prevent drift; marketing sweep at v2.0
gives a coherent launch story.

## Blocking

None. Phase 1 can start immediately on Quincy's answer to Q1–Q5.

## Ready for Phase 1

- Will produce: `audit/phase-1-v2/backlog.json` (per-v2-ID priority list with
  Tier-0 primitives + EPM + Wave V deliverables interleaved)
- Will produce: `audit/phase-1-v2/tier0-primitives.json` (84-row
  present/absent map)
- Will produce: `audit/phase-1-v2/sequencing.md` (per Q1 decision)
- Will produce: `audit/phase-1-v2/wave-v-design-handoff.md` (per Q2 decision)
