# Phase 0.1 — Repo inventory

**Generated:** 2026-04-24
**Repo:** `lintpdf` (private monorepo, pnpm workspaces + Turborepo)
**Branch at audit time:** `claude/add-preflight-testing-4C2b3` @ `912cf16`
**Last commit:** `912cf16 fix(dieline): compose CTM so transformed artworks register correctly`

---

## Top-level layout

```
lint-pdf/
├── packages/
│   ├── app/             Next.js 15 dashboard (TypeScript, React 19, Prisma, Tailwind 4)
│   ├── engine/          FastAPI 0.115 PDF preflight engine (Python 3.11+, Celery, pikepdf)
│   ├── web/             Public marketing + docs site (Next.js)
│   ├── plugin/          Fairy Ring plugin (`@thinkneverland/lintpdf-plugin`)
│   ├── stripe/          Stripe billing integration (`@lintpdf/stripe`)
│   ├── inference/       AI/vision inference service (Python, isolated venv)
│   ├── desktop/         Tauri 2.2 desktop app (excluded from pnpm workspace)
│   ├── database/        Prisma schema (single `schema.prisma`)
│   ├── hotfolder/       Python file-watcher
│   ├── sdk-python/      Public Python SDK
│   └── edge-caddy/      Edge-cache config
├── audit/               (this Phase-0 working directory)
├── docs/                examples/, audits/raw/ (Opus verdicts), examples/<vendor>-report.json
├── grounded-research/   ISO 32000-2, ISO 15930, GWG, PDFX4 specs (34 files)
└── lintpdf-check-audit-playbook.md   (root playbook)
```

`pnpm-workspace.yaml`:

```yaml
packages:
  - "packages/*"
  - "!packages/desktop"
```

Top-level `package.json`: `name=lintpdf`, `private=true`, `packageManager=pnpm@10.11.0`. Turbo tasks: `build`, `dev`, `lint`, `typecheck`, `test`.

## packages/engine — preflight engine

- **Stack:** FastAPI 0.115, Uvicorn, Celery + Redis, SQLAlchemy 2 + Alembic, pikepdf 9, Pillow 10, pdf2image 1.17, numpy 1.26. Optional `[ai]` extras: PyTorch, transformers, ultralytics, paddleocr, pyiqa.
- **Python:** `>=3.11`, `uv`-managed via `uv.lock`.
- **Source root:** `packages/engine/src/lintpdf/`.

### Subpackages of `lintpdf`

| Subpackage | Purpose |
|---|---|
| `analyzers/` | Deterministic preflight inspectors. **32 `.py` files.** Emit `Finding(...)` with `inspection_id="LPDF_*"`. |
| `ai/` | AI-tier inspectors (model-backed) under `ai/analyzers/`. **60 `.py` files** across subdirs `regulatory_compliance/`, `color_compliance/`, `symbol_detection/`, `text_analysis/`, `image_analysis/`, `barcode/`, `dieline_detection/`, `document_classification/`, `file_comparison/`, `logo_verification/`, `nlp_interfaces/`, `trend_analysis/`, `auto_remediation/`. Emit `inspection_id="AI_*"` (sometimes `LPDF_*` for the AI-barcode family). |
| `profiles/` | Preflight-profile registry + `orchestrator.py` (entrypoint that fans out to analyzers). |
| `api/routes/` | FastAPI routers: `jobs.py`, `reports.py`, `viewer.py`, `endpoints.py`, `batch.py`, `trial.py`, `admin.py`, `profiles.py`, plus AI routes (`ai_config`, `ai_credits`, `ai_generate`, `ai_interpret`, `ai_presets`, `ai_usage`), branding/colour, webhooks, downloads, dev_auth. **30 routers.** |
| `reports/` | Output formatters (HTML, PDF, JSON, XML); `check_names.py` (142 friendly-name registry entries). |
| `queue/` | Celery task definitions; `tasks.py` (already-read in this session). |
| `imports/` | External-format parsers for PitStop XML, Callas JSON/XML, Acrobat XML, lintPDF JSON. |
| `semantic/` | Semantic-document model + content-stream events (`events.py` carries `ctm`, `text_matrix`). |
| `parser/` | Low-level PDF parsing helpers. |
| `conformance/` | PDF/X-* conformance (also calls out to `verapdf/` Java sidecar). |
| `audit/` | Audit metering. |
| `billing/`, `tenants/`, `email/`, `webhooks/`, `approvals/`, `brand_specs/`, `comparison/`, `integrations/`, `regulatory/`, `rules/`, `overrides/`, `warming/`, `spc/`, `color_score.py` | Domain modules. |

### Engine entry points

- `packages/engine/scripts/entrypoint.sh` — runs `alembic upgrade head` then starts uvicorn (Railway deploys hit this).
- `packages/engine/seed_and_serve.py` — local dev convenience.
- `packages/engine/run_preflight.py` — CLI wrapper.

### Engine scripts (operational)

- `audit_test_corpus.py` — Opus-backed accuracy audit harness.
- `audit_preflight_accuracy.py` — older variant.
- `replay_audit_dataset.py` — re-scores a fresh engine run against committed Opus verdicts (no live Opus call).
- `export_check_catalog.py` — produces `packages/app/lib/rules/check-catalog.json` (the WS-12 catalog).
- `seed_pws_demo.py`, `seed_test_data.py` — fixtures.
- `enrich_pantone_reference.py` — Pantone metadata fetch.
- `full_api_sweep.py` — API smoke harness.

### Database / migrations

- 41 Alembic revisions under `packages/engine/alembic/versions/`.
- Shared Postgres database with the Prisma app — engine owns most tables (`tenants`, `jobs`, `findings`, `endpoints`, `api_keys`, `brand_specs`, `audit_*`); Prisma owns auth + tenancy primitives.
- All data-plane services route through `pgbouncer.railway.internal:6432` (max_connections=200 on Postgres, ~130 logical pool sum, ~30-50 backend connections after PgBouncer multiplexing).

### Tests

- 166 `test_*.py` files under `packages/engine/tests/`, mirrored to source layout (`tests/analyzers/`, `tests/ai/`, `tests/api/`, `tests/profiles/`, `tests/reports/`, `tests/queue/`, …). Plus 7 root-level engine tests (`test_config.py`, `test_email_service.py`, `test_middleware.py`, `test_pantone_cache.py`, `test_reports_engine.py`, `test_scaffold.py`, `test_worker.py`, `test_xml_report.py`).
- Pytest markers used: `slow`, `corpus`. Phase-0 baseline command: `cd packages/engine && uv run pytest -m "not slow and not corpus" -q`.
  Test run launched in background (task `beoiyvrjb`); output not captured at the time of writing — record the result before Phase 1 starts. (Previous session reports indicate the suite was green on `main` after PRs #178–#191.)

### Railway deploy topology (engine-side)

`packages/engine/railway*.toml` files:
- `railway.toml` — main API (numReplicas=3 in production).
- `railway.control-plane.toml` — admin / operational plane (numReplicas=2).
- `railway.worker.toml`, `railway.worker-ai.toml`, `railway.worker-priority.toml`, `railway.worker-reports.toml`, `railway.worker-tiles.toml`, `railway.worker-webhooks.toml` — Celery workers split by queue.
- `railway.beat.toml` — Celery beat scheduler.
- `railway.verapdf.toml` — VeraPDF sidecar for PDF/A + PDF/X conformance.

## packages/app — Next.js dashboard

- **Stack:** Next.js 15, React 19, TypeScript 5.9 (strict), tRPC 11, Prisma 7, TailwindCSS 4. Pixie Dust UI components throughout.
- **Name:** `@thinkneverland/lintpdf-app`.
- **Scripts:** `dev`, `build`, `start`, `lint`, `typecheck`, `db:generate`, `db:migrate`, `db:push`, `db:seed`.
- **Routes:** `/dashboard/{account, admin, api-keys, api-reference, approvals, billing, brand-specs, downloads, endpoints, preflight, profile, reports, rulesets, team, usage, waitlist, webhooks, [slug]}`.
- **Critical for Phase 0:** `packages/app/lib/rules/check-catalog.json` (1141 lines, 142 catalogued checks, 47 categories — the WS-12 catalog).
- **Viewer code:** `packages/app/components/viewer/` — `PdfViewer.tsx`, `PageCanvas.tsx`, `LayerCanvas.tsx`, `BoxOverlay.tsx`, `DielineOverlay.tsx` (read this session), `FindingsPanel.tsx`, `DensitometerTool.tsx`, etc.
- **Rules editor:** `packages/app/components/rules/RulesEditor.tsx`, `RulesTab.tsx`, `RuleRow.tsx`, `JsonTab.tsx`, `BulkActionBar.tsx`, plus `hooks/useProfileState.ts`. Tabbed view at `/dashboard/rulesets/[id]` and `/dashboard/admin/rulesets`.
- **Startup:** `packages/app/scripts/startup.sh` runs raw-SQL `ALTER TABLE ADD COLUMN IF NOT EXISTS` + `prisma db push` + seed + `next start` (necessary because `prisma db push` would otherwise want to drop engine tables).

## packages/web — public marketing + docs

- **Markdown docs:** 68 `.md` files under `packages/web/src/content/docs/`. Examples: `viewer-capabilities.md`, `external-imports.md`, `branding-and-anonymous.md`, `share-links.md`, `ai-*.md`.
- **JSX docs:** `packages/web/src/components/docs/pages/` — `ApiReferencePage.tsx` composed of `api/*.tsx` sections; plus `ChecksPage.tsx`, `GlossaryPage.tsx`, `WebhooksPage.tsx`, `ReportFormatsPage.tsx`.
- **Try-it page:** `packages/web/src/app/try-it/page.tsx` (env-gated trial submission).
- **Docs-parity rule:** any new submit-form / viewer / branding field lands in BOTH the markdown docs AND the JSX section components in the same commit.

## packages/database

Single Prisma schema at `packages/database/prisma/schema.prisma`. **STOP rule:** confirm before any changes — schema cascades to FastAPI models via Alembic.

## packages/inference

Python AI/vision inference service in its own venv. Isolated from the main engine deps to avoid forcing PyTorch into every container build. Currently consumed only by AI analyzers when GPU tier features are enabled.

## packages/plugin, packages/stripe, packages/sdk-python, packages/hotfolder, packages/desktop, packages/edge-caddy, packages/infra

Out-of-scope for the check audit. Listed for completeness so a future phase doesn't re-discover them.

## Reference material checked into the repo

- `grounded-research/specs/` — 34 files. Indexes for ISO 32000-2 Ch7 + Ch8, PDF/X-4 spec, ICC v4 (`ICC-PARSING-SUMMARY.md`, `README-ICC1-2022.md`), competitive intelligence index. Citable for check-semantics questions during Phase 1 priority scoring without round-tripping to the web.
- `docs/examples/` — runnable per-vendor sample reports for every external_format parser.
- `docs/audits/raw/` — committed Opus verdicts that the replay harness scores against.

## Engine Python toolchain (Phase-0 commands)

```sh
cd packages/engine
uv run ruff check src tests           # lint
uv run mypy src                        # types
uv run pytest -m "not slow and not corpus"   # ~166 test files
uv run alembic upgrade head            # apply migrations
uv run alembic check                   # verify model ↔ migration parity
```

## App TS toolchain (Phase-0 commands)

```sh
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build
pnpm test
```

## Test-suite snapshot

Pytest invocation (`uv run pytest -m "not slow and not corpus" -q`) was launched in the background as task `beoiyvrjb` while writing this inventory. Capture its pass/fail/skip counts and append them here before exiting Phase 0 — they form the regression baseline every later phase compares against.

## Phase-0 follow-ups recorded for the Q&A gate

- Engine test-suite green/yellow/red status (background task `beoiyvrjb` not yet inspected).
- Whether `packages/engine/scripts/export_check_catalog.py` is wired into CI (the WS-12 catalog has drifted to 142/360 = 39% coverage — see Phase 0.2 summary).
- Whether the `desktop`/`edge-caddy`/`hotfolder`/`infra`/`sdk-python` packages need to be considered as additional check-emit surfaces. (Spot check: none have an `analyzers/` directory; treat as out of scope unless operator says otherwise.)
