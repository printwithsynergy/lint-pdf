# Grounded brand scrub — Phase 1 Track C

**Branch:** `claude/grounded-scrub`
**Scope:** Remove "Grounded" (the dead product brand) from the LintPDF monorepo. Companion to Phase-1 Tracks A (engine plugin protocol) and B (viewer core/lintpdf split).

## Why this matters

The codebase was rebranded "Grounded" → "LintPDF" but two workspace package
names and a handful of doc strings still carried the old brand. Stale brand
references confuse new contributors landing on the repo and create friction
when we extract the engine and viewer to their own OSS repos in Phase 3
(`thinkneverland/sift-pdf`, `thinkneverland/loupe-pdf`). This PR closes the
gap so Phase 1 ships with a single, current brand.

## Discovery summary

Initial case-insensitive grep across tracked source/doc/config (excluding
`node_modules`, `.venv`, `__pycache__`, `.next`):

- **57 files** with at least one "grounded" hit.
- After classification, **~14 files** required edits; the rest are either
  legitimate proper nouns, a versioned research vault, or English-language
  uses of the word "grounded".

## Rename mapping (applied)

### Package names

| Old | New |
|---|---|
| `@thinkneverland/grounded-plugin` | `@thinkneverland/lintpdf-plugin` |
| `@thinkneverland/grounded-web` | `@thinkneverland/lintpdf-web` |

### Module paths in docs

| Old (in docs) | Current (in code) |
|---|---|
| `src/grounded/` | `packages/engine/src/lintpdf/` |
| `grounded.worker` | `lintpdf.queue.app` |
| `grounded.api` | `lintpdf.api.app` |

### Brand-language terms in docs

`.atlas/docs/project.md` and `.thinkneverland/ATLAS-CONTEXT.md` carried the
original aviation-themed brand language. Replaced with the current production
terms (also documented in `.thinkneverland/PROJECT.md` "Brand language"):

| Old | New |
|---|---|
| Check-In | Submit |
| Flight Plan | Ruleset |
| Flight Log | Report |
| Clear to Fly | Pass |
| No-Fly | Fail (critical severity) |
| Radio | Webhook |
| Taxiing | Processing |
| Arrived | Complete |
| `grounded` (verdict) | `fail` |

## Files edited (commit 1: package renames + imports)

| File | Change |
|---|---|
| `packages/plugin/package.json` | `name` → `@thinkneverland/lintpdf-plugin` |
| `packages/web/package.json` | `name` → `@thinkneverland/lintpdf-web` |
| `packages/app/package.json` | workspace dep updated |
| `packages/app/lib/plugins.ts` | import path updated |
| `packages/app/app/dashboard/layout.tsx` | import path updated |
| `packages/app/next.config.mjs` | `transpilePackages` entry updated |
| `packages/web/Dockerfile` | `pnpm --filter` target updated |
| `scripts/e2e-local.sh` | `pnpm --filter` target updated |

## Files edited (commit 2: docs)

| File | Change |
|---|---|
| `CLAUDE.md` | line 42 package ref + new "Brand stack + repo split" section |
| `.thinkneverland/PROJECT.md` | celery/uvicorn dev commands; project-structure example; inspection-ID pattern |
| `.thinkneverland/BUILD-PLAYBOOK.md` | added prominent **archival note** at top with old → new translation guide |
| `.thinkneverland/ATLAS-CONTEXT.md` | job-status + verdict tables refreshed |
| `.atlas/docs/project.md` | GitHub repo + brand-language + inspection-ID format refreshed |
| `audit/phase-0/repo-inventory.md` | inventory line refreshed |

## Files edited (commit 3: lockfile)

`pnpm-lock.yaml` regenerated via `pnpm install --lockfile-only`. The
`grounded-plugin` workspace link is replaced with the renamed
`lintpdf-plugin` link. The diff is dominated by pnpm canonicalising
duplicate peer-dependency snapshot keys (e.g., `@radix-ui/*` and
`@prisma/client` peer-tuples) that became collapsible after the rename
cascade — this is normal pnpm-lock behavior and not a logical change.

After regeneration: zero "grounded" hits in `pnpm-lock.yaml`.

## Files kept as-is (with rationale)

| Path | Why kept |
|---|---|
| `grounded-research/` directory + 34 files | Versioned research asset vault (ISO 32000-2, PDF/X-4, GWG, ICC v4 specs). Renaming would break cross-references throughout the docs and provide no functional benefit. The directory name is internal to the repo, not a product surface. |
| `.thinkneverland/` directory | Org identifier (Thinkneverland LLC), not the dead brand. |
| `packages/inference/.../object_detector.py` `post_process_grounded_object_detection()` | Refers to **GroundingDINO**, a third-party ML model. Legitimate proper noun. |
| `.deepsource.toml` (line 28) | Ignore-pattern entry referencing `grounded-research/**`, which keeps that name. |
| `audit/phase-0/qa-resolutions.md` (line 64) | Historical record of the `GRD_*` → `LPDF_*` rename event itself. Legitimate historical reference. |
| `audit/phase-0/check-research-approach.md` + `audit/phase-0/qa-resolutions.md` | Path references to `grounded-research/specs/*` — directory keeps that name. |
| `audit/phase-0/repo-inventory.md` lines 28, 134 | Same — `grounded-research/` directory references. |
| `scripts/audit-opus.py:50` ("grounded against the *rendered*") | Common-English use of "grounded" meaning "based on / verified against". Not the brand. |
| `packages/engine/scripts/audit_test_corpus.py:3` ("grounded accuracy") | Same — common-English use. |
| `.thinkneverland/BUILD-PLAYBOOK.md` historical sections (~50 hits) | Archival planning document; an in-place wholesale scrub would alter the historical record. Mitigated by a prominent archival header at the top of the file with an old → new translation guide. |
| Linear card keys `GRD-001`, `GRD-002`, … | Real Linear issue identifiers; renaming would orphan the Linear history. |
| `LINEAR_TEAM_KEY: GRD` (`.thinkneverland/PROJECT.md`) | Same. |
| `CLAUDE.md` line 71 | Self-reference inside the new Brand-Stack section explaining what this PR does. Legitimate flagged context. |

## Importer counts (before → after)

| Symbol | Before | After |
|---|---|---|
| `@thinkneverland/grounded-plugin` (npm) | 5 importers (plugins.ts, layout.tsx, next.config.mjs, app/package.json, pnpm-lock.yaml) | 0 |
| `@thinkneverland/grounded-web` (npm) | 2 importers (Dockerfile, e2e-local.sh) + 1 self-name (web/package.json) | 0 |
| `@thinkneverland/lintpdf-plugin` (npm, new) | 0 | 5 |
| `@thinkneverland/lintpdf-web` (npm, new) | 0 | 3 |

(Counted via `grep -rln` across tracked files excluding the keep-list above.)

## Acceptance gates

- ✅ `grep -rli "grounded" .` (excluding the keep-list above + `node_modules` / `.venv` / `.next` / `pnpm-lock.yaml`) → only the flagged residuals listed in "Files kept as-is".
- ✅ `pnpm install --lockfile-only` → diff stat as expected (workspace link rename + peer-dep canonicalisation).
- ⏳ `pnpm typecheck && pnpm build` (root) — gate run after all three commits land.
- ⏳ `cd packages/engine && pytest -m "not slow and not corpus"` — gate run after all three commits land.

## Out of scope (Track C)

- Repo extraction (Phase 3).
- Renaming the engine Python package `lintpdf` → `siftpdf` (Phase 3).
- Engine plugin protocol (Track A — separate branch `claude/engine-saas-split-phase1`).
- Viewer `core/` vs `lintpdf/` split (Track B — separate branch `claude/viewer-core-extract-phase1`).
- Railway service / env-var / domain renames — none reference "Grounded" today, so nothing to flag.

## Hosted SaaS continuity

- DB schema: unchanged.
- API surface: unchanged. No route, response, or finding format touched.
- Stripe / billing / auth: unchanged.
- ENABLE_SAAS / OSS-mode posture (PRs #313/#315/#317): unchanged. The marketing
  site continues to render identically with `NEXT_PUBLIC_ENABLE_SAAS=false`.

The only mechanically observable change for end users is the renamed npm
package `name` field, which is internal to the workspace. All consumers
(only `packages/app` consumes `lintpdf-plugin`; `lintpdf-web` is only built
by the Dockerfile + the e2e script) are updated in the same commit.

## Next phases

- **Track A** (next session): engine plugin protocol + decouple analyzers from
  SaaS modules. 63-file SaaS-import migration.
- **Track B** (next session): viewer `core/` vs `lintpdf/` split + plugin
  protocol. 28 components, 11 to be wrapped as plugins.
- Phase 2: registry unification, FastAPI route classification, OpenAPI
  `Field(..., description=...)` backfill.
- Phase 3: repo extraction. SaaS-side rewires to import `siftpdf` (renamed
  from `lintpdf` engine package) and `@thinkneverland/loupe-pdf` as external
  deps. Customer-functional-parity checklist gate before production.
- Phase 4: OSS flip. License audit, repo visibility flipped to public.
