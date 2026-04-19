# LintPDF edge Worker

Cloudflare Worker that terminates TLS for branded tenant subdomains under `*.custom.lintpdf.com` and path-routes to the Railway-hosted Reports + App backends.

## Why

Railway's per-domain TLS issuance (TLS-ALPN-01 via Let's Encrypt) requires customer CNAMEs to point **directly** at Railway's per-domain-generated target (e.g. `9m9a8ps4.up.railway.app`). That leaks Railway's infrastructure into every customer's DNS record, and Railway's validator doesn't chase CNAME chains, so any middle-layer alias breaks cert issuance.

This Worker replaces that model for tenant subdomains:

- Cloudflare terminates TLS using the wildcard cert on `*.custom.lintpdf.com` (auto-provisioned on the zone).
- The Worker path-routes each request to the correct Railway backend (`reports.lintpdf.com` for `/r/*` + `/api/v1/*`, `app.lintpdf.com` for `/view/*` + `/_next/*` + `/dashboard/*`).
- Railway sees a request with `Host: reports.lintpdf.com` (or `app.lintpdf.com`), which it already knows about. No per-tenant Railway registration.
- Customer gets ONE branded URL: `https://{slug}.custom.lintpdf.com/r/{token}` for static reports AND `/view/{token}` for the interactive viewer.

## Path-routing table

| Pattern | Upstream | Rationale |
|---|---|---|
| `/r/*` | `reports.lintpdf.com` | Signed static report tokens |
| `/api/v1/*` | `reports.lintpdf.com` | Public viewer API + OpenAPI + webhook inbound |
| `/view/*` | `app.lintpdf.com` | Interactive Next.js viewer |
| `/_next/*` | `app.lintpdf.com` | Next.js asset bundle |
| `/dashboard/*` | `app.lintpdf.com` | Admin + tenant dashboards (served under customer subdomain if they enable it) |
| `/favicon.ico`, `/robots.txt` | `app.lintpdf.com` | Served by the App service |
| everything else | `app.lintpdf.com` | Landing / catch-all |

Host header is rewritten to the upstream service's hostname so Railway's edge routes the proxied request to the right service. `X-Forwarded-Host` preserves the customer-facing hostname for engine-side telemetry / per-tenant logic.

## Local dev

Requires `wrangler` (install with `pnpm add -g wrangler` or `npm i -g wrangler`).

```sh
cd packages/edge-worker
wrangler dev              # local edge emulator at http://localhost:8787
wrangler tail             # tail live logs from the deployed Worker
```

## Deploy

From the repo root:

```sh
cd packages/edge-worker
wrangler deploy
```

Requires a Cloudflare API token with `Workers Scripts: Edit` + `Workers Routes: Edit` on the `lintpdf.com` zone. Our existing scoped token (`CLOUDFLARE_API_TOKEN` in the Railway engine env) has `Zone:DNS:Edit` only — deploying the Worker needs a **separate** token. See `docs/cloudflare-setup.md` for the steps.

## Cutover

Once deployed:

1. Create a wildcard DNS record: `*.custom.lintpdf.com` → proxied (orange-cloud) A record pointing at any IP (CF's edge intercepts via route attachment). Easiest is a proxied CNAME to `lintpdf.com`.
2. Verify: `curl https://test.custom.lintpdf.com/__edge/health` returns 200 with the Worker's health JSON.
3. Verify path routing: `curl https://test.custom.lintpdf.com/` returns the App service landing page (with headers showing `x-forwarded-host: test.custom.lintpdf.com` + `host: app.lintpdf.com` in engine logs).

## Rollback

Comment out the `routes` block in `wrangler.toml` and re-deploy. Customer subdomains will start 522'ing (origin unreachable) since the route is gone. Customers can always migrate BACK to direct Railway CNAMEs as the fallback.

## Observability

- `wrangler tail` for live logs (stdout from the Worker).
- Cloudflare dashboard → Workers → `lintpdf-edge` → Analytics for request volume + error rate.
- Engine-side: the Reports and App services see `X-Forwarded-Host` on every request and can log per-hostname traffic.
