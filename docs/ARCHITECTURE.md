---
title: "Architecture"
description: "Component layout, request flow through the API and Celery worker, the three-scope toggle cascade, snapshot recording, and the AI-tier model that gates which analyzers run."
group: "Getting started"
order: 3
---

# Architecture

This doc walks the LintPDF engine from a request entering the API
layer through analyzer dispatch, AI tier routing, snapshot
recording, and report generation. Read alongside
[`README.md`](../README.md) for the high-level overview.

## Process topology

A typical OSS deployment runs three processes against a shared
Postgres + Redis:

```
┌──────────────┐   ┌──────────────┐
│  Postgres    │   │   Redis      │
└──────┬───────┘   └──────┬───────┘
       │                  │
       └────────┬─────────┘
                │
        ┌───────┴────────────────┐
        │                        │
┌───────┴───────┐      ┌─────────┴──────┐      ┌──────────────┐
│  uvicorn API  │ ───► │  celery worker │ ───► │ celery beat  │
│  (FastAPI)    │      │  (analyzers)   │      │  (timers)    │
└───────────────┘      └────────────────┘      └──────────────┘
```

Optional sidecars: a veraPDF service for full PDF/A and PDF/X
validation, an AI inference service for the GPU/external-AI tier,
ClamAV for upload virus scanning, and S3-compatible object storage
for PDFs and rendered reports. Without any of those the engine
still runs — analyzers self-skip cleanly.

The deployment guide ([`docs/DEPLOYMENT.md`](DEPLOYMENT.md)) covers
the env vars and the production hard-fail security gates
(`LINTPDF_SECRET_KEY` + `LINTPDF_CORS_ALLOW_ORIGINS=*`).

## Request lifecycle

### 1. Submission

`POST /api/v1/jobs` accepts a multipart form: the PDF, an optional
`profile_id` (which ruleset to apply), an optional `workflow_id`
(the curated configuration handle), an optional `ai_preset` slug,
and per-call `overrides` JSON.

The route handler:

1. Validates the upload (size, MIME, ClamAV scan if configured).
2. Resolves the **toggle cascade** to compute the effective
   configuration for this job (see [Toggle cascade](#toggle-cascade)
   below). The result lands in `resolved_config_snapshots` so the
   audit log can replay exactly which config drove the findings.
3. Persists the job row + the uploaded PDF (object storage or
   local filesystem).
4. Enqueues the job onto the Celery queue.

The HTTP handler returns immediately with `202 Accepted` and the
`job_id`. The caller polls `GET /api/v1/jobs/{id}` (or subscribes
to webhooks) until terminal.

### 2. Worker dispatch

The Celery worker picks up the job and runs the orchestrator
(`lintpdf.ai.orchestrator.dispatch`). The orchestrator:

1. Loads every registered analyzer (built-ins + entry-point
   plugins) and filters by the resolved profile's enabled / disabled
   glob lists.
2. Constructs an `AnalyzerContext` per analyzer carrying:
   - `pdf_bytes` — the source PDF.
   - `config["ai_config"]` — the resolved AI knobs (no direct
     access to tenant or billing tables).
   - `services.{database, renderer, gpu_client, cost_cap, metering,
     verapdf_client, llm_client, …}` — Protocol-typed handles for
     SaaS-coupled functionality.
   - `capabilities.{page_images, ocr_text, …}` — shared work
     providers (so two analyzers reading the same rendered page
     image fulfil the request once, not twice).
3. Dispatches in **tier order**:
   - `Tier.CPU` — runs in the orchestrator process.
   - `Tier.GPU` — needs `gpu_client` and usually `page_images`.
   - `Tier.EXTERNAL_AI` — calls an LLM/API; gated through
     `cost_cap` + `metering`.
4. Collects findings, applies the profile's
   `severity_overrides` + `max_severity` cap.
5. Computes the verdict (`pass` / `pass_with_warnings` / `fail`).
6. Writes the `JobFinding` rows + emits webhook events
   (`job.completed` or `job.failed`).

If an analyzer raises, the orchestrator captures the exception and
emits a single `LPDF_ANALYZER_ERROR` finding instead of failing the
whole job — one bad inspector never silences the others.

### 3. Report mint

`POST /api/v1/reports/jobs/{id}` mints reports on demand. Four
formats:

- `html` — single-file self-contained, suitable for share links.
- `pdf` — printable PDF (rendered via WeasyPrint).
- `json` — structured payload, the same shape as `GET /jobs/{id}`.
- `annotated` — the original PDF with finding annotations stamped
  onto each page.

Reports go through the `WorkerReports` Celery queue so the API
process never blocks on rendering.

### 4. Viewer + share links

`GET /api/v1/viewer/jobs/{id}` returns a viewer config
(separations, layers, tile DPI, branding) + signed tile URLs that
the embedded viewer
([@printwithsynergy/loupe-pdf](https://github.com/printwithsynergy/loupe-pdf))
fetches as the user scrolls. Annotations are CRUD'd via
`POST /api/v1/viewer/jobs/{id}/annotations`.

Share links are minted by the SaaS shell on top of the OSS engine —
the OSS package itself does not carry tenant-domain probing or
brand-profile management.

## Toggle cascade

Configuration is resolved through a three-scope cascade introduced
in Phase 0.7:

```
TENANT  ─── (tenant defaults; ai_cost_cap and other lockable knobs live here)
   │
   └── WORKFLOW  ─── (pinned per-workflow defaults)
         │
         └── CALL  ─── (per-job overrides passed in JobCreate.overrides)
```

Each toggle in the registry declares an `override_at` array listing
which scopes may override it. `ai_cost_cap`, for example, is
`override_at=[TENANT]` only — workflows and calls cannot raise it.
Most preflight knobs (`profile_rules`, `brand`,
`viewer_capabilities`, `response_format`) are
`override_at=[TENANT, WORKFLOW, CALL]`.

A toggle marked `lockable=true` and set with `locked=true` at
TENANT scope rejects WORKFLOW/CALL overrides outright.

The resolution result lands in `resolved_config_snapshots` per
job; the snapshot's `provenance` map records which scope supplied
each toggle's value. Audit views replay from the snapshot, not
from live override state, so historical job context survives
workflow edits.

The customer-facing reference for the cascade lives at the SaaS
docs ([Workflows](https://lintpdf.com/docs/workflows) +
[Rulesets](https://lintpdf.com/docs/rulesets)).

## Service-injection layer

Every cross-boundary call from the engine goes through a Protocol
declared under `lintpdf.services.*`. SaaS hosts override at app
construction:

```python
app = create_app()
app.dependency_overrides[get_email_service] = lambda: SendgridEmailService()
```

The default implementations are:

- `EmailService` → `NoOpEmailService` (logs at debug, returns
  `success=False`).
- `EntitlementsService` → forwards to
  `lintpdf.tenants.entitlements.resolve_entitlements`.
- `BillingService` → forwards to
  `lintpdf.billing.file_quota.check_and_consume_file_quota`.

OSS deployers swap these for their own implementations or no-ops —
see [`docs/EXTENDING.md`](EXTENDING.md).

## Analyzer plugin model

Every analyzer satisfies a single Protocol:

```python
class Analyzer(Protocol):
    manifest: PluginManifest                                 # plugin metadata
    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]: ...
```

Built-in analyzers live under `src/lintpdf/analyzers/` and
`src/lintpdf/ai/analyzers/`. Third-party plugins ship as Python
packages declaring an entry point under
`[project.entry-points."lintpdf.plugins"]` — the engine discovers
them at startup.

Hard rule (CI tripwire): code under `src/lintpdf/analyzers/**` and
`src/lintpdf/ai/analyzers/**` cannot import from
`lintpdf.tenants.*`, `lintpdf.billing.*`, `lintpdf.audit.metering`,
`lintpdf.audit.cost`, `lintpdf.api.database`, `lintpdf.api.storage`,
`lintpdf.ai.{cost_cap,credits,gpu_client}`, or
`lintpdf.conformance.verapdf_client`. Use `ctx.services.*` instead.
This rule is what keeps third-party analyzers portable across OSS
and SaaS hosts. See [`docs/plugin-api.md`](plugin-api.md) for the
authoritative protocol reference.

## Database surface

The engine ships these tables (Alembic-managed):

- `jobs`, `job_findings`, `report_tokens`, `annotations`,
  `decisions`, `epm_snapshots`, `resolved_config_snapshots`,
  `workflows`, `toggles`, `toggle_overrides`,
  `webhook_endpoints`, `webhook_deliveries`.

The SaaS shell adds: `tenants`, `api_keys`, `subscriptions`,
`brand_profiles`, `app_custom_domains`, `tenant_ai_config`,
`tenant_ai_credit_packages`. Phase 5 work is decoupling the SaaS
tables out of the engine alembic stream — track the W6 / W7 line
items in the project board.

## Conformance + AI sidecars

veraPDF runs as a separate HTTP service
([thinkneverland/railway-verapdf](https://github.com/thinkneverland/railway-verapdf))
that the engine consults via `ctx.services.verapdf_client`. Without
the sidecar, `lintpdf.conformance` emits a single advisory marker
and skips deep PDF/A + PDF/X-4 checks.

AI analyzers consult an inference service via
`ctx.services.gpu_client` (vision models, OCR) and
`ctx.services.llm_client` (Claude). Without either configured, AI
checks self-skip at runtime — the engine still produces a valid
preflight report, just without the AI-driven categories.

## Read more

- [`docs/DEPLOYMENT.md`](DEPLOYMENT.md) — running the engine.
- [`docs/EXTENDING.md`](EXTENDING.md) — service overrides + plugins.
- [`docs/plugin-api.md`](plugin-api.md) — full plugin Protocol reference.
- [`docs/audit-phase1.md`](audit-phase1.md) — Phase 1 plugin-protocol
  refactor engineering record.
