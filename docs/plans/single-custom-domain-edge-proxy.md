# Plan: collapse white-label custom domains into one + edge proxy

**Status:** future work — not for this commit.
**Prerequisites:** commit `65fb825` (tenant-aware `viewer_url` in mint
response) is shipped. Engine already emits the right host per tenant;
this plan is about consolidating the DNS / setup story.

## Context

The user's actual frustration with the "wrong URL" bug was the
**white-label story**, not just the script bug. Today a tenant who
wants every URL to live under their brand has to:

1. Set `tenant.brand_custom_domain = "reports.acme.com"` (CNAME →
   `reports.lintpdf.com`).
2. Wait for `tenant.brand_custom_domain_verified` flag to flip via
   `probe_pending_custom_domains` Celery beat task.
3. Set `tenant.app_custom_domain = "app.acme.com"` (CNAME →
   `app.lintpdf.com`).
4. Wait for `tenant.app_custom_domain_verified` to flip.

That's TWO domains + TWO DNS records + TWO TLS certs + TWO
verification windows. Mint responses then return URLs split across
both: `https://reports.acme.com/r/{token}` for the static report,
`https://app.acme.com/view/{token}` for the interactive viewer.

What the user wants:

- ONE `tenant.custom_domain` (e.g. `acme.lintpdf.com`).
- ONE CNAME, one cert, one verification window.
- That domain serves BOTH paths transparently:
  - `acme.lintpdf.com/r/{token}` → routes to the engine
    (FastAPI / API service)
  - `acme.lintpdf.com/view/{token}` → routes to the App service
    (Next.js)
  - `acme.lintpdf.com/_next/*` → routes to the App service
    (the Next.js bundle assets)
- Mint response returns URLs from the single tenant domain when set;
  falls back to `app.lintpdf.com/view/{token}` +
  `reports.lintpdf.com/r/{token}` for default tenants.

## Architecture options

### Option C-1 — Cloudflare Worker (recommended for this stack)

Cloudflare Workers can attach to a tenant's custom hostname (Workers
for Platforms, or just per-zone Worker routes), inspect the path, and
forward to the right Railway service:

```
acme.lintpdf.com/r/*       → fetch("https://reports.lintpdf.com/r/...")
acme.lintpdf.com/view/*    → fetch("https://app.lintpdf.com/view/...")
acme.lintpdf.com/_next/*   → fetch("https://app.lintpdf.com/_next/...")
acme.lintpdf.com/*         → fetch("https://app.lintpdf.com/...")  (catch-all)
```

**Pros:**
- One DNS record per tenant (CNAME to `lintpdf.cloudflare-edge.com`).
- One cert (Cloudflare-issued).
- Sub-millisecond routing decision; no Railway hop overhead.
- Already on Cloudflare for the marketing site presumably.

**Cons:**
- Cloudflare Workers for Platforms requires a paid plan ($5/mo + $0.50/M
  requests). For LintPDF's volume that's pennies.
- Adds a second deployment surface (Worker bundle + wrangler config).

### Option C-2 — Caddy/Traefik sidecar on Railway

Add a Railway service running Caddy that does the same path-based
routing. CNAME tenant domains to the Caddy service.

**Pros:**
- Stays on Railway, no new vendor.
- Open-source, no per-request cost.

**Cons:**
- Caddy doesn't auto-issue certs for arbitrary on-the-fly hostnames
  unless you wire it to ACME with on-demand TLS — workable but more
  ops surface than Workers.
- Adds a hop (Railway → Caddy → Railway internal DNS → engine/app).

### Option C-3 — Engine-internal reverse proxy

Add a FastAPI route to the engine that proxies `/view/*` to the App
service.

**Pros:**
- No new infrastructure.

**Cons:**
- Engine has to stream Next.js assets too (`/_next/*`) — every page
  load fans out to N httpx calls.
- Coupling: engine becomes responsible for serving the Next.js app
  even though the App service exists for that.
- Not actually "one domain" — `reports.acme.com` would have to host
  Next.js assets that originally come from `app.lintpdf.com`. Either
  we proxy them all (slow) or set Next.js `assetPrefix` to
  `app.lintpdf.com` (defeats unification).

**Reject C-3.** Path-based routing belongs at an edge proxy, not in
application code.

## Recommended path: Option C-1

Cloudflare Worker with these capabilities:

1. **Auto-attach** when a new `tenant.custom_domain` is verified by
   `probe_pending_custom_domains`. The probe task already lives at
   `packages/engine/src/lintpdf/queue/tasks.py` — extend it to call
   the Cloudflare API to register the hostname on the Worker.
2. **Routing rules** in the Worker:
   ```js
   if (url.pathname.startsWith('/r/'))         → reports.lintpdf.com
   if (url.pathname.startsWith('/api/v1/'))    → reports.lintpdf.com
   if (url.pathname.startsWith('/_next/'))     → app.lintpdf.com
   if (url.pathname.startsWith('/dashboard/')) → app.lintpdf.com
   else                                        → app.lintpdf.com (Next.js handles /view, /, etc.)
   ```
3. **Origin host header rewrite** so Railway sees the correct
   `Host: reports.lintpdf.com` / `Host: app.lintpdf.com` when
   forwarding.

## Engine + DB changes required

### Schema

- Deprecate `tenant.brand_custom_domain` (keep column, mark
  `# DEPRECATED: use custom_domain instead` in the model).
- Deprecate `tenant.app_custom_domain` (same treatment).
- Add `tenant.custom_domain` (already exists in the model at line
  847 of `models.py` per the earlier grep — verify and reuse rather
  than introducing yet another column).
- Add `tenant.custom_domain_verified` + `tenant.custom_domain_requested_at`
  if missing.
- Migration is purely additive + backward-compat. Existing tenants
  keep using the legacy fields until they re-onboard with the
  unified field.

### Resolver

Update `resolve_report_base_url` and `resolve_viewer_base_url` in
`packages/engine/src/lintpdf/reports/service.py`:

```python
def _tenant_base(tenant) -> str | None:
    # Prefer the new unified field; fall back to legacy split fields
    # so already-white-labeled tenants keep working through the
    # transition window.
    if tenant.custom_domain and tenant.custom_domain_verified:
        return f"https://{tenant.custom_domain}"
    return None

def resolve_report_base_url(tenant, profile, entitlements, settings):
    if entitlements.whitelabel_enabled:
        unified = _tenant_base(tenant)
        if unified:
            return unified
        # Legacy fallback (existing logic).
        ...
    return settings.report_base_url
```

Same change for `resolve_viewer_base_url`. Both helpers now return
the SAME host when a unified `custom_domain` is set.

### Admin UI

`/admin/tenants/{id}/custom-domain` PATCH already exists. Add a
`/admin/tenants/{id}/custom-domain` route that takes a single
`{domain: "acme.lintpdf.com"}` payload, kicks off the probe, and
calls the Cloudflare API to register the hostname on the Worker.

Mark the legacy `/admin/tenants/{id}/brand-custom-domain` and
`/admin/tenants/{id}/app-custom-domain` as deprecated in OpenAPI.

### Dashboard

Replace the two domain-config screens with one. The UI shows:

- Field: `Your custom domain` (e.g. `acme.lintpdf.com`)
- Status: `Pending DNS` / `Verified` / `Failed`
- DNS instructions: "Add a CNAME `acme.lintpdf.com` →
  `lintpdf-edge.cloudflare.com`"

## Verification

- Set up a CF zone for `lintpdf.com` (probably already exists).
- Deploy a Worker on a test subdomain (e.g.
  `staging-edge.lintpdf.com`).
- Manually CNAME `staging-acme.lintpdf.com` → the Worker.
- Curl `staging-acme.lintpdf.com/view/{token}` and
  `staging-acme.lintpdf.com/r/{token}` — both should return 200 with
  the right backing service responding.
- Update one test tenant in the DB to set
  `custom_domain=staging-acme.lintpdf.com, verified=true`.
- Mint a report and confirm the response carries
  `viewer_url=https://staging-acme.lintpdf.com/view/{token}` and
  `url=https://staging-acme.lintpdf.com/r/{token}`.

## Out of scope for this plan

- Per-page edge caching rules (defer to a later perf pass).
- Worker logging / observability — basic Cloudflare analytics is
  fine for v1.
- Multi-region origin selection — Railway is single-region today.
- Email custom domains (different feature, different DNS records).

## Effort estimate

- Engine schema + resolver + admin route: ~half a day
- Cloudflare Worker code + wrangler deploy: ~half a day
- Probe-task integration with Cloudflare API: ~half a day
- Dashboard UI consolidation: ~1 day
- Migration runbook + customer email re-onboarding ~legacy field
  deprecation: ~half a day

Total: ~3 dev-days plus customer outreach.
