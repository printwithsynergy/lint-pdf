# Per-tenant rate limits (bulk-files step 12)

## Status

**Already implemented.** The existing codebase has per-tenant
rate-limiting at two layers:

### Daily rate limit

`check_rate_limit(tenant)` in `packages/engine/src/lintpdf/api/middleware.py:165`
enforces `tenant.rate_limit_daily` against a rolling 24-hour window
tracked in Redis. Tenants exceeding their quota get HTTP 429 with the
standard retry/usage headers.

### Burst rate limit

`check_burst_rate_limit(tenant)` at `middleware.py:258` enforces
`tenant.rate_limit_burst` against a short rolling window (seconds).
Every upload endpoint (`/api/v1/jobs`, `/api/v1/batch/submit`,
`/api/v1/endpoints/{id}/submit`, `/api/v1/trial/submit`) calls both
guards.

### Priority throttling

Paid-tier tenants (`entitlements.priority_processing=true`) route to
the `priority` Celery queue at submit time; free tier goes to
`default`. Bulk-files step 3 (PR #118) introduced a third queue
`ai_heavy` that both tiers share but is bounded by Modal's container
cap. Head-of-line-blocking across tenants is mitigated because:

- Upload concurrency is per-tenant (`check_burst_rate_limit` is a
  Redis-bucket-per-tenant).
- Celery worker pool is tenant-agnostic but ai_heavy is isolated
  (step 3) so a noisy AI tenant can't drown deterministic work from
  other tenants.

## When to escalate

| Signal | Action |
|---|---|
| p99 latency differs dramatically per tier | split the `default` Celery queue further: `deterministic-paid`, `deterministic-free`. |
| A single tenant generates >10× the usage of the 90th percentile | move that tenant to a dedicated Worker replica (Railway numReplicas scale on a tenant-scoped queue). |
| Cross-tenant share-link abuse | add IP-bucket rate limiting on `/view/{token}`. |

## See also

- `packages/engine/src/lintpdf/api/middleware.py` — rate-limit implementation
- `packages/engine/src/lintpdf/tenants/entitlements.py` — tier definitions
- `CLAUDE.md` "Connection budget" — shared-DB tenancy considerations
