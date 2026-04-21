# Multi-region deployment + CDN (bulk-files steps 13 & 14)

## Context

**Step 13 (multi-region) is explicitly deferred.** Standing up a second
region on Railway costs an estimated **$60-100/mo ongoing** (duplicate
API + Workers + Postgres + Redis + sidecars — effectively doubles the
infra bill). No current customer requires data residency, so this is
pure cost with no revenue backing it. The design below stays as a
runbook so when a paying enterprise does require it, flipping the
switch is a 1-day exercise, not a 1-week design round.

**Step 14 (CDN) is a verification-only item.** `cdn.lintpdf.com` + R2
public-read already exist via `LINTPDF_TILE_CDN_BASE_URL`. Nothing to
spin up.

## Step 13 — Multi-region deployment (EU + US) — DEFERRED

**When to do it:** a prospect or existing customer commits to a contract
that requires data residency (GDPR, German customers insisting on
EU-only processing, etc.) or a regional-latency SLA.

**Plan:**

1. Duplicate the existing Railway services in a new Railway project
   scoped to the target region:
   - `API`, `Worker`, `Worker-AI`, `Worker-Webhooks`, `API-Control-Plane`
     (optional), `Postgres`, `Redis`, `ClamAV`, `veraPDF`, `PgBouncer`.
2. Each regional project gets its own R2 bucket (data residency).
3. Set `LINTPDF_REGION` env var per project: `us-east`, `eu-west`.
4. Route public traffic by Host → region:
   - Keep the shared marketing site (`lintpdf.com`).
   - Tenant subdomain or custom domain resolves to the regional API
     via Railway custom-domain routing (same pattern as today's
     white-label DNS).
5. Per-tenant `preferred_region` column on `Tenant`; engine redirects
   submission endpoints when the request hits the wrong region.
6. Modal is already regionally routable — pick the nearest datacenter
   via `modal.App(region="eu-west-1")` or similar in the per-region
   Modal deploy.

**Non-goals:** cross-region replication for Postgres. Customer data
stays in-region; if a tenant wants both, they get two accounts.

## Step 14 — CDN for viewer + report tiles

**Status:** Cloudflare R2 already hosts the tiles and `cdn.lintpdf.com`
already exists (`LINTPDF_TILE_CDN_BASE_URL` env var). Verify:

- Ensure the R2 bucket has public-read on the `tiles/` prefix.
- `cdn.lintpdf.com` CNAME resolves at Cloudflare → the public R2
  endpoint.
- `LINTPDF_TILE_CDN_BASE_URL=https://cdn.lintpdf.com` is set on the
  API + Worker services (both emit tile URLs in responses).

**Nothing more to ship here until viewer load times from Europe / APAC
become a complaint.** Cloudflare's global edge network + R2 origin
already gets us <200ms-first-byte from most regions.

## Escalation triggers

- **Latency > 500ms** for the viewer in a region → verify `cdn.lintpdf.com`
  resolves correctly; add regional CF cache rules.
- **A prospect blocks on data residency** → start step 13.
- **Report render time > 5s in a region** → consider regional
  Worker-Reports replicas.

## See also

- `packages/engine/railway.*.toml` — per-service deploy configs
- `packages/engine/src/lintpdf/api/config.py` — env-var schema
- `CLAUDE.md` "Connection budget" — shared-DB considerations if
  deciding to point both regions at one Postgres (don't).
