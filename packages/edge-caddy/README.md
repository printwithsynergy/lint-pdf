# LintPDF edge (Caddy on Fly.io)

Self-hosted TLS-terminating reverse proxy for **customer-owned domains** (BYO-domain). Customers CNAME their hostname at `edge.lintpdf.com`; Caddy mints a Let's Encrypt cert on the first HTTPS request and path-routes to the Railway backends.

Cloudflare's **SSL for SaaS** feature would handle the same case inside CF but requires the Business plan ($250/mo). Self-hosting Caddy with `on_demand_tls` gets us the same capability at $0 until Fly.io usage exceeds their free tier.

## Architecture

```
Customer
   │
   │  CNAME reports.acme.com → edge.lintpdf.com
   ▼
Fly.io (this Caddy app)  ← terminates TLS, per-hostname LE cert
   │                         issued on first request
   │  path-routed reverse proxy (Host rewritten)
   ▼
Railway (reports.lintpdf.com / app.lintpdf.com)
```

### Path routing

| Path prefix | Upstream | Rewritten Host |
|---|---|---|
| `/r/*`, `/api/v1/*` | `reports.lintpdf.com` | `reports.lintpdf.com` |
| `/view/*`, `/_next/*`, `/dashboard/*`, `/favicon.ico`, `/robots.txt` | `app.lintpdf.com` | `app.lintpdf.com` |
| everything else | `app.lintpdf.com` | `app.lintpdf.com` |

### Cert issuance abuse guard

On-demand TLS would let any internet rando point `evil.example` at our edge and force us to burn LE rate-limit budget. To prevent that, Caddy calls an `ask` endpoint on the engine (`api.lintpdf.com/api/v1/internal/on-demand-tls-check?domain=X`) before each cert issuance. The engine returns 200 if `X` is a known tenant / brand-profile custom domain; 4xx otherwise. Caddy refuses to issue in that case.

A shared secret (`LINTPDF_EDGE_SHARED_SECRET`) sent as a header prevents random traffic from probing the ask endpoint directly.

## Deploy

From repo root:

```sh
cd packages/edge-caddy

# One-time app creation (idempotent; no-op if app exists)
fly apps create lintpdf-edge --org personal

# Rotate / set the shared secret (Caddy side)
fly secrets set LINTPDF_EDGE_SHARED_SECRET=$(openssl rand -hex 32) --app lintpdf-edge

# Persistent volume for Caddy's cert store
fly volumes create caddy_data --app lintpdf-edge --region ord --size 1 --yes

# Deploy
fly deploy --app lintpdf-edge
```

(Equivalent Fly Machines API calls work without the CLI — see the one-shot deploy script in `scripts/fly-deploy-edge.sh` which uses only `curl`.)

## Customer flow (once live)

1. Customer submits `reports.theirdomain.com` via LintPDF dashboard / API.
2. Engine persists the hostname + returns `dns_target: "edge.lintpdf.com"`.
3. Customer adds a CNAME: `reports.theirdomain.com → edge.lintpdf.com`.
4. First request to `https://reports.theirdomain.com/...` hits Caddy.
5. Caddy's `on_demand_tls` fires → asks engine's `/on-demand-tls-check?domain=reports.theirdomain.com` → engine returns 200 (hostname is registered).
6. Caddy requests an LE cert via TLS-ALPN-01 on port 443 → issued in ~5-30 seconds.
7. Cert cached in `/data` (the mounted Fly volume); subsequent requests use cached cert.
8. Caddy path-routes to Railway; customer sees their report / viewer on their own branded URL.

## Operational notes

- **LE rate limits**: 50 duplicate certs per registered-domain per week; 300 new-orders per account per 3h. Caddy handles renewal automatically (30 days before expiry).
- **Volume backup**: cert store lives in `/data` on the Fly volume. Losing that volume forces re-issuance but doesn't break anything structural.
- **Logs**: `fly logs --app lintpdf-edge`. Each request logs the hostname + path + upstream + status as JSON.
- **Scaling**: `fly scale count 2` to run two VMs for HA. Fly's built-in load balancer spreads traffic. Cert store is shared via the mounted volume so no double-issuance.

## Rollback

Delete the Fly app (`fly apps destroy lintpdf-edge`). Customer CNAMEs pointing at `edge.lintpdf.com` will fail DNS resolution / 502 until the app is restored.
