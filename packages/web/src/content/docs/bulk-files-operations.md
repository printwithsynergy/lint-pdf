---
title: Bulk files — operations guide
description: How LintPDF is architected to handle large-file-count workloads, what ops levers exist, and where the remaining headroom lives.
---

# Bulk files — operations guide

LintPDF's ingest/analysis/report pipeline is sized for **hundreds of
PDFs per minute per tenant**, submitted as N independent
`POST /api/v1/jobs` calls (not multipart bundles). This page documents
the operational plane — Railway service layout, Celery queue routing,
knobs exposed via env vars, and the observability endpoints.

## Service map

| Service | Role |
|---|---|
| **API** | FastAPI public ingress. 3 replicas, 8 Uvicorn workers each. Graceful rolling deploys with 60 s overlap. |
| **API-Control-Plane** | Same codebase, `LINTPDF_CONTROL_PLANE_ONLY=1`. Serves `/ready`, `/api/v1/status`, `/api/v1/admin/*`, `/usage`, `/profiles`, `/webhooks`, `/edge`, `/branding`. Isolated so upload bursts on the main API cannot drag admin/health down. Ops dashboards and external uptime probes point here. |
| **Worker** | Main Celery consumer. Subscribes to `default,priority,ai_heavy`. Concurrency: `CELERY_DEFAULT_CONCURRENCY`. |
| **Worker-AI** | Dedicated Celery consumer for `ai_heavy` (any job with `ai_enabled=true`). Concurrency bounded by Modal `max_containers`. `CELERY_AI_CONCURRENCY`. |
| **Worker-Webhooks** | Webhook dispatch queue. `CELERY_WEBHOOK_CONCURRENCY`. |
| **Worker-Reports** *(staged)* | Dedicated `reports` queue consumer. Not yet spun up — promote when step-11 metrics show report-render contention on Worker. |
| **Worker-Tiles** *(staged)* | Dedicated `tiles` queue consumer for viewer-tile warming. Same promotion trigger. |
| **PgBouncer** | Transaction-pool in front of Postgres. Multiplexes API + worker connections onto a small backend pool, keeping us under Postgres `max_connections`. |
| **Postgres** | Single primary. Connection budget is shared via PgBouncer. |
| **Redis** | Celery broker + rate-limit buckets + batch tracking. |
| **ClamAV** | Malware scanner sidecar. Fail-open by default; set `LINTPDF_CLAMAV_REQUIRED=1` on the API to enforce. |
| **veraPDF** | PDF/A validation helper. |

## Queue routing

Decided at API dispatch time in `routes/jobs.py`,
`routes/batch.py`, `routes/endpoints.py`:

```
if ai_enabled:              queue = ai_heavy
elif priority_tier:         queue = priority
else:                       queue = default
```

Main Worker subscribes to `default,priority,ai_heavy` (acts as
fallback). Worker-AI subscribes only to `ai_heavy`. Celery
load-balances across workers subscribed to the same queue.

## Knobs exposed via env vars

| Variable | Service | Default | Purpose |
|---|---|---|---|
| `LINTPDF_WORKERS` | API, API-Control-Plane | 4 | Uvicorn worker processes per replica |
| `LINTPDF_CONCURRENCY_PER_WORKER` | API, API-Control-Plane | 20 | Max in-flight async handlers per Uvicorn worker before 503 |
| `LINTPDF_ASYNCIO_EXECUTOR_WORKERS` | API | 32 | Default-executor pool (R2 uploads via run_in_executor) |
| `LINTPDF_CONTROL_PLANE_ONLY` | API-Control-Plane | 1 | Disables upload/job/report routers |
| `LINTPDF_CLAMAV_URL` | API, Worker | — | ClamAV endpoint (host:port) |
| `LINTPDF_CLAMAV_REQUIRED` | API | 0 | Fail-closed when ClamAV unreachable / unset (enterprise compliance) |
| `CELERY_DEFAULT_CONCURRENCY` | Worker | 2 | Slots on the default/priority/ai_heavy-fallback pool |
| `CELERY_AI_CONCURRENCY` | Worker-AI | 6 | Slots on the dedicated AI pool (track Modal `max_containers`) |
| `CELERY_REPORTS_CONCURRENCY` | Worker-Reports (staged) | 4 | Report-render pool |
| `CELERY_TILES_CONCURRENCY` | Worker-Tiles (staged) | 2 | Viewer tile-warming pool |

## Observability

- `GET /metrics` on every engine service — Prometheus exposition
  format. Metrics:
  - `lintpdf_http_requests_total{method, path_template, status}`
  - `lintpdf_http_request_duration_seconds{method, path_template}`
    (histogram, 5 ms – 30 s buckets)
  - `lintpdf_uploads_in_flight` (gauge — memory-pressure signal)
  - `lintpdf_job_terminal_total{status}`
- `GET /api/v1/status` (auth) — per-queue depth, Celery worker count.
- `GET /ready` — trivial DB + Redis liveness.

Point an external scraper (Grafana Cloud, Prometheus, DataDog agent)
at the API-Control-Plane's `/metrics` for a non-blocked observation
channel.

## Bulk endpoints

### `POST /api/v1/reports:batchMint`

Mints report tokens for up to 500 completed jobs in one round trip.
Per-job failures captured inline; one bad id doesn't drop the rest.
See the API reference "Bulk report-mint" subsection.

## Headroom and escalation

| Signal | Action |
|---|---|
| `lintpdf_uploads_in_flight` > 50 sustained | bump `numReplicas` on the API service |
| `/api/v1/status` queue depth on `default` > 100 | bump `CELERY_DEFAULT_CONCURRENCY` or replicas |
| `/api/v1/status` queue depth on `ai_heavy` > Modal `max_containers` | bump Modal `max_containers` (modal_deploy.py) |
| Postgres `max_connections` near 100 | confirm PgBouncer is in the `DATABASE_URL`; raise `max_connections` on Postgres |
| p99 report-mint latency > 5 s | promote Worker-Reports to a live service; switch report dispatch to the `reports` queue |

## See also

- `docs/scaling/per-tenant-rate-limits.md` — rate-limit surface
- `docs/scaling/multi-region-and-cdn.md` — multi-region runbook (deferred)
- `preflight-stress-results.md` — the incident that drove the program
