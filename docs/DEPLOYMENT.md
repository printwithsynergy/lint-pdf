# Deployment

This guide covers self-hosting the LintPDF OSS engine — running it
standalone, without the hosted SaaS shell at `lintpdf.com`. For the
high-level overview see [`README.md`](../README.md); for the
architectural picture see [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).

## What the OSS engine ships

When booted with `LINTPDF_SAAS_MODE=false`, the following routes
are mounted:

| Route | Purpose |
|---|---|
| `GET /health`, `GET /ready` | Liveness + readiness (DB / Redis check) |
| `GET /api/v1/ai/health` | AI subsystem readiness probe |
| `POST /api/v1/jobs` | Submit a PDF for preflight |
| `GET /api/v1/jobs/{id}` | Poll job status + retrieve findings |
| `GET /api/v1/jobs/{id}/state` | One-call snapshot (job + reports + annotations + verdicts) |
| `GET /api/v1/jobs` | List jobs |
| `DELETE /api/v1/jobs/{id}` | Delete job + its artifacts |
| `POST /api/v1/jobs/{id}/rerun_audit` | Re-run AI audit on existing findings |
| `POST /api/v1/jobs/{id}/findings/{fid}/explain` | Per-finding AI explanation |
| `GET /api/v1/jobs/{id}/epm` | EPM (Engineering Production Match) verdict |
| `GET /api/v1/jobs/{id}/decisions` | Audit log of human-in-the-loop verdict overrides |
| `GET/POST /api/v1/viewer/jobs/{id}/...` | Viewer config + capability fetches |
| `POST /api/v1/viewer/jobs/{id}/annotations[/...]` | Annotation CRUD |
| `POST /api/v1/reports/jobs/{id}` | Mint HTML / PDF / JSON / annotated reports |
| `POST /api/v1/batch` | Batch submit (multiple PDFs in one call) |
| `GET /api/v1/profiles[/...]` | Built-in preflight profile resolution |
| `GET /api/v1/icc-profiles[/...]` | Substrate ICC profile lookup |

What is **NOT** in OSS mode: tenant CRUD, API-key issuance, Stripe
billing, the trial intake flow, brand profile management, custom
domain probing, approval workflows, file-pack purchases, AI credit
grants, the admin console, and the white-label-aware report mint.
Those live behind the SaaS shell, which proprietarily consumes the
OSS engine as a Python dep.

## Required environment variables

| Var | Required? | Purpose |
|---|---|---|
| `LINTPDF_SAAS_MODE=false` | yes (for OSS deploy) | Skips SaaS-only routers at boot. Default `true` mounts everything (the hosted SaaS layout). |
| `LINTPDF_SECRET_KEY` | **yes in production** | Signs viewer JWTs and share-link tokens. Production refuses to boot with the default `'change-me-in-production'` value. Generate with `openssl rand -hex 32`. |
| `LINTPDF_ENVIRONMENT` | optional | One of `production` (default), `staging`, `development`. Dev mode bypasses the secret-key + CORS hard-fails so local hacking works. |
| `LINTPDF_CORS_ALLOW_ORIGINS` | optional | Comma-separated origin allowlist for browser callers. Defaults to `https://lintpdf.com,https://app.lintpdf.com` — set to your origin(s). Production refuses `'*'`. |
| `LINTPDF_DATABASE_URL` | yes | PostgreSQL connection string. Engine tables run via Alembic on first boot. |
| `LINTPDF_REDIS_URL` | yes | Redis used for rate limiting + tile-warming locks. |
| `LINTPDF_GPU_INFERENCE_URL` | optional | Point at the AI inference service if running with AI features. Without it, AI analyzers self-skip. |
| `S3_*` / `LINTPDF_S3_*` | yes if using object storage | R2 / S3 credentials for PDF + report storage. |
| `LINTPDF_CLAMAV_URL` | optional | If set, every upload is scanned. Best-effort fail-open by default (set `LINTPDF_CLAMAV_REQUIRED=1` to fail-closed). |

## Boot a server (pip)

```bash
# Install from PyPI
pip install lintpdf

# Or pin to a specific git ref:
#   pip install "lintpdf @ git+https://github.com/printwithsynergy/lint-pdf.git@main"

# Minimum viable env
export LINTPDF_SAAS_MODE=false
export LINTPDF_SECRET_KEY=$(openssl rand -hex 32)
export LINTPDF_DATABASE_URL=postgresql://user:pass@localhost/lintpdf
export LINTPDF_REDIS_URL=redis://localhost:6379/0
export LINTPDF_CORS_ALLOW_ORIGINS=https://your-app.example.com

# Run
uvicorn lintpdf.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

Verify:

```bash
curl http://localhost:8000/ready
# {"status":"ok","database":"connected","redis":"connected"}
```

## Boot the full stack (docker-compose)

The repo ships a `docker-compose.yml` that wires the engine +
Postgres + Redis + ClamAV + a Celery worker + beat:

```bash
git clone https://github.com/printwithsynergy/lint-pdf.git
cd lint-pdf
docker compose up -d

# Once /ready returns 200:
curl http://localhost:8000/ready
```

Volume-mount your own `LINTPDF_*` env file via `--env-file`; the
default compose file uses dev-friendly placeholders.

## Production topology

A production deployment runs the engine as multiple processes
behind a load balancer:

```
                    ┌────────────────────┐
                    │   ALB / nginx      │
                    └──────────┬─────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────┴──────┐      ┌───────┴────────┐      ┌──────┴──────┐
│ uvicorn API  │  ×N  │ celery worker  │  ×M  │ celery beat │  ×1
│ (FastAPI)    │      │ (analyzers)    │      │ (timers)    │
└──────┬───────┘      └───────┬────────┘      └─────┬───────┘
       │                      │                     │
       └──────────────────────┴─────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────┴─────┐  ┌──────┴─────┐  ┌─────┴───────┐
        │  Postgres │  │   Redis    │  │  S3 / R2    │
        └───────────┘  └────────────┘  └─────────────┘
```

Sizing notes:

- Each uvicorn worker holds an SQLAlchemy pool (default 5 + 10
  overflow). With Postgres `max_connections=100`, leave headroom
  for migrations + Celery + admin sessions; route through PgBouncer
  if you scale past ~3 API replicas.
- Celery worker concurrency defaults to 8 prefork workers per
  process. Each worker can saturate one CPU during analyzer
  dispatch, so size pods with one CPU per concurrency slot.
- Analyzer memory budget is dominated by page rasterization: a
  20 MB PDF with a 12 MB page can briefly use 800 MB before
  garbage collection. Provision 2 GB RAM per worker conservatively.

## Optional sidecars

| Sidecar | Image | Purpose |
|---|---|---|
| **veraPDF** | [`thinkneverland/railway-verapdf`](https://github.com/thinkneverland/railway-verapdf) | Full PDF/A and PDF/X-4 conformance validation. Without it, `lintpdf.conformance` emits a single advisory marker. |
| **AI inference** | (deploy your own; talks to `LINTPDF_GPU_INFERENCE_URL`) | Vision models, OCR, dieline detection. Without it, AI checks self-skip. |
| **ClamAV** | `clamav/clamav` (or built-in compose service) | Upload virus scanning. Best-effort fail-open by default. |
| **R2 / S3** | (any S3-compatible) | PDF + rendered-report storage. Without it, jobs persist to a local filesystem path (suitable for single-node OSS deploys, not HA). |

## Auth in OSS mode

The OSS engine ships its tenant-auth Protocol declarations in
`lintpdf.api.auth` but does **not** ship a working multi-tenant
implementation. By default `get_current_tenant` requires an API key
that maps to a row in the `tenants` table — and the OSS package
doesn't ship that table.

Two paths for OSS-mode auth:

**Single-user mode** — override `get_current_tenant` to return a
fixed sentinel tenant. Add this to your boot script:

```python
from fastapi import FastAPI
from lintpdf.api.app import create_app
from lintpdf.api.auth import get_current_tenant

class _SingleUser:
    id = "00000000-0000-0000-0000-000000000001"
    name = "Self-hosted"
    is_active = True
    plan = "enterprise"
    # …other Tenant fields your routes touch

app = create_app()
app.dependency_overrides[get_current_tenant] = lambda: _SingleUser()
```

**Custom auth (LDAP, OIDC, BasicAuth)** — implement your own
`get_current_tenant` factory and override it the same way. The
function must return an object with `id`, `name`, `plan`,
`is_active`, and `contact_email` — see the engine's `Tenant` model
for the full shape.

**No auth at all** — not recommended, but you can return the
`_SingleUser` stub above unconditionally and skip API key checks.

## Security gates (production)

`LINTPDF_ENVIRONMENT=production` (the default) enables two hard
fails that turn unsafe defaults into refuse-to-boot:

1. **`LINTPDF_SECRET_KEY`** — `get_settings()` raises
   `RuntimeError` if the value is left at the default
   `'change-me-in-production'`. Bypass via `PYTEST_CURRENT_TEST`
   set, `pytest` in `sys.modules`, or
   `LINTPDF_ENVIRONMENT=development`.
2. **`LINTPDF_CORS_ALLOW_ORIGINS`** — `create_app()` raises if
   `'*'` is present in production. Same bypass cascade.

Without these gates an OSS deployer running on a production-shaped
server with no env config would have a working server signing
forgeable JWTs with a known key + an open CORS policy. Now the
deploy refuses to boot with a clear remediation message.

## Backups + retention

- **Postgres** — back up the engine database with whatever your
  cloud's managed-Postgres ships (Railway snapshots, RDS automated
  backups). The schema lives entirely in `alembic/`; restoring
  from a backup re-runs migrations to current head on next boot.
- **PDFs + reports** — if you use S3, lifecycle rules per bucket.
  If you use the local filesystem fallback, plan for periodic
  archival (the engine never auto-deletes; see the cleanup recipe
  in `scripts/`).
- **Toggle audit log** — `toggle_audit_log` rows accumulate forever
  by default. Truncate older than your retention window via a
  Celery beat task.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `503 Service Unavailable` on `/ready` | Database or Redis unreachable | Check `LINTPDF_DATABASE_URL` + `LINTPDF_REDIS_URL` connectivity. |
| `RuntimeError: refusing to boot with default LINTPDF_SECRET_KEY` | Secret-key gate firing in production | Set `LINTPDF_SECRET_KEY` to a real value (`openssl rand -hex 32`). |
| `RuntimeError: production refuses CORS '*'` | Wildcard CORS gate firing | Pin `LINTPDF_CORS_ALLOW_ORIGINS` to a real origin list. |
| Job stuck in `processing` | Worker pool saturated, or veraPDF/AI sidecar offline | Check worker logs + sidecar reachability. |
| Webhook never fires | Endpoint URL not configured, or 5+ consecutive failures auto-disabled it | Inspect `webhook_deliveries` table; `is_active=true` to re-enable. |

## Read more

- [`README.md`](../README.md) — overview + quick start.
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — request flow, toggle
  cascade, AI tiering.
- [`docs/EXTENDING.md`](EXTENDING.md) — service overrides + plugin
  authoring.
