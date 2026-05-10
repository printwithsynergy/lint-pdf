---
title: "HTTP API"
description: "Reference for the engine's HTTP surface — 91 routes across job submission, results, reports, viewer payloads, AI explain, decisions audit, profile catalogue, and batch jobs. The OpenAPI spec is the single source of truth."
group: "Reference"
order: 8
---

# HTTP API

The engine exposes a FastAPI application with 91 routes across 12
modules under [`src/lintpdf/api/routes/`](../src/lintpdf/api/routes/).
Every public route has a Pydantic response model and an explicit
`responses=` mapping for non-200 statuses, so the OpenAPI spec at
`/openapi.json` is the canonical client contract.

For the hosted product the spec lives at
[api.lintpdf.com/openapi.json](https://api.lintpdf.com/openapi.json);
self-hosters get the same spec at `http://<your-host>/openapi.json`
once the engine is booted.

## Route map

| Module                                                                                            | Prefix                  | Purpose                                                      |
|---------------------------------------------------------------------------------------------------|-------------------------|--------------------------------------------------------------|
| [`health.py`](../src/lintpdf/api/routes/health.py)                                                | _(none)_                | `GET /health`, `GET /ready` — liveness + readiness           |
| [`ai_health.py`](../src/lintpdf/api/routes/ai_health.py)                                          | `/api/v1/ai`            | Unauthenticated AI-inference outage probe                    |
| [`jobs.py`](../src/lintpdf/api/routes/jobs.py)                                                    | `/api/v1/jobs`          | Submit, list, fetch, delete jobs; rerun audit                |
| [`ai_explain.py`](../src/lintpdf/api/routes/ai_explain.py)                                        | `/api/v1/jobs`          | AI-Explain endpoint for findings                             |
| [`decisions.py`](../src/lintpdf/api/routes/decisions.py)                                          | `/api/v1/jobs`          | Verdict-decisions audit (V-05)                               |
| [`epm_summary.py`](../src/lintpdf/api/routes/epm_summary.py)                                      | `/api/v1/jobs`          | HP Indigo EPM candidacy summary                              |
| [`profiles.py`](../src/lintpdf/api/routes/profiles.py)                                            | `/api/v1/profiles`      | List / get / register preflight profiles                     |
| [`reports.py`](../src/lintpdf/api/routes/reports.py)                                              | _(none — paths embed it)_ | HTML / PDF / JSON / annotated-PDF report generation          |
| [`viewer.py`](../src/lintpdf/api/routes/viewer.py)                                                | `/api/v1/viewer`        | Tile rendering, separations, TAC heatmap, font list, layers  |
| [`annotations.py`](../src/lintpdf/api/routes/annotations.py)                                      | `/api/v1/viewer`        | Per-finding annotation overlays                              |
| [`icc_profiles.py`](../src/lintpdf/api/routes/icc_profiles.py)                                    | `/api/v1/icc-profiles`  | Substrate ICC profile catalogue (EPM-A1)                     |
| [`batch.py`](../src/lintpdf/api/routes/batch.py)                                                  | `/api/v1/batch`         | Bulk job submission + status                                 |

The mounting order, plus which routers depend on the AI tier being
configured, lives in
[`src/lintpdf/api/app.py`](../src/lintpdf/api/app.py) at the
`include_router` block — useful when reading why an endpoint may
404 on a deploy without AI services configured.

## Submit a job (the golden path)

```bash
# 1. Submit
curl -X POST http://localhost:8000/api/v1/jobs \
  -F "file=@artwork.pdf" \
  -F "profile_id=lintpdf-default"
# { "job_id": "job_abc...", "status": "queued" }

# 2. Poll
curl http://localhost:8000/api/v1/jobs/job_abc...
# { "id": "job_abc...", "status": "completed", "verdict": "pass_with_warnings", ... }

# 3. One-call snapshot (job + reports + annotations + verdicts)
curl http://localhost:8000/api/v1/jobs/job_abc.../state | jq .
```

`/state` is the wide-payload endpoint used by the viewer — it folds
the job, its findings, available report renderings, viewer-capability
flags, and the verdict snapshot into one call so the UI doesn't have
to choreograph N round-trips.

## Auth

Out of the box the OSS engine boots with **no auth**. To wire in your
own — single-user, OIDC, basic auth, or a custom tenant resolver — see
[Deployment / auth in OSS mode](./DEPLOYMENT.md#auth-in-oss-mode).
The hosted SaaS layers multi-tenant API-key auth on top via the
service-override seams documented in
[Extending the engine](./EXTENDING.md).

## Discipline (for contributors)

Every Pydantic field on a public route MUST have
`description="..."`, every route handler MUST have a docstring summary
and explicit `responses=` mapping. Both rules are enforced by
[`scripts/check_openapi_descriptions.py`](../scripts/check_openapi_descriptions.py)
in CI. Background: [Contributing](./CONTRIBUTING.md).
