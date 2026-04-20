---
title: "Custom Domains"
description: "Serve reports and the viewer from a LintPDF-branded subdomain (zero DNS work) or your own hostname (one CNAME)."
section: "branding"
order: 32
---

# Custom Domains

LintPDF gives every tenant a **branded subdomain** immediately on signup — no DNS configuration required. Scale and Enterprise tiers can additionally point their **own domain** at our edge with a single CNAME record. Both paths terminate TLS at LintPDF's infrastructure and path-route to the same backends; you never install certificates or manage Let's Encrypt yourself.

## Two options, one edge

```
┌──────────────────────────────┐   Instant, zero DNS work (all plans).
│ {slug}-custom.lintpdf.com    │   Covered by our Universal SSL cert.
└──────────────────────────────┘   Customer just uses the URL.
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │  LintPDF edge         │
                              │  (CF Worker + Caddy)  │
                              └───────────────────────┘
                                          ▲
┌──────────────────────────────┐          │    Scale/Enterprise. One CNAME
│ reports.yourdomain.com       │──────────┘    to ``edge.lintpdf.com``.
└──────────────────────────────┘               We issue + rotate the cert.
```

Both options are served by the same edge and routed identically:

- `/r/*` and `/api/v1/*` → reports backend (static HTML/PDF reports, public viewer API)
- `/view/*`, `/_next/*`, `/dashboard/*` → app backend (interactive Next.js viewer)
- default → app backend (landing, auth)

## Option 1: Branded subdomain (default, zero DNS)

Every tenant has an auto-provisioned subdomain under `*-custom.lintpdf.com` derived from their tenant ID. Find yours in the dashboard under **Account → Branding**, or via `GET /api/v1/tenants/{tenant_id}/custom-domain` (returned as `dns_target`).

Example URL shape:

```
https://8cdd7799-custom.lintpdf.com/r/{token}        ← static report
https://8cdd7799-custom.lintpdf.com/view/{token}     ← interactive viewer
```

The cert is managed by LintPDF. Nothing to renew. Nothing to wait for. Use the URL in your emails, embed the viewer, share report links — it works immediately.

## Option 2: Bring your own domain (Scale + Enterprise)

If you want URLs on a hostname you own (e.g. `reports.yourdomain.com`), add **one** CNAME record:

| Hostname | Type | Value | TTL |
|---|---|---|---|
| `reports.yourdomain.com` | CNAME | `edge.lintpdf.com` | 300 |

That's the entire setup. No `_acme-challenge` TXT records, no certificate files to install, no nameserver change. Our edge (Caddy with on-demand TLS) issues a Let's Encrypt certificate for your hostname on the first HTTPS request and caches it for subsequent traffic.

**First request**: 5–30 seconds while the cert issues.
**Every request after**: instant.

## Request a BYO domain

```bash
curl -X PATCH https://api.lintpdf.com/api/v1/tenants/{tenant_id}/custom-domain \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{"domain": "reports.yourdomain.com"}'
```

Response:

```json
{
  "tenant_id": "7c9a4b0e-...",
  "domain": "reports.yourdomain.com",
  "verified": false,
  "requested_at": "2026-04-20T14:30:00Z",
  "plan_allows_whitelabel": true,
  "dns_target": "edge.lintpdf.com"
}
```

Fields:

- `domain` — the hostname you registered.
- `verified` — flips to `true` after the first successful HTTPS request through our edge. Unrelated to DNS propagation; reflects actual end-to-end reachability.
- `dns_target` — **always `edge.lintpdf.com`** for BYO domains. Put this in your CNAME record.
- `plan_allows_whitelabel` — `false` on tiers below Scale; the domain is stored but not served until you upgrade.

## Inspect current state

```bash
curl https://api.lintpdf.com/api/v1/tenants/{tenant_id}/custom-domain \
  -H "Authorization: Bearer lpdf_live_..."
```

## Clear a BYO domain

Pass `null`:

```bash
curl -X PATCH https://api.lintpdf.com/api/v1/tenants/{tenant_id}/custom-domain \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{"domain": null}'
```

This reverts the tenant to their branded subdomain only. The old hostname becomes claimable by other tenants after a 24-hour cooldown.

## App (viewer) domain

The `/app-custom-domain` endpoint mirrors the above but for the interactive viewer. In practice the same CNAME covers both — customers rarely need a separate hostname for the viewer vs. reports. Leaving it empty is fine; the reports domain handles `/view/*` paths too.

## Per-BrandProfile domain

Override the tenant-level custom domain for a specific BrandProfile. Useful when an agency serves multiple clients and each brand's reports should live on its own hostname:

```bash
curl -X PATCH https://api.lintpdf.com/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}/custom-domain \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{"domain": "reports.acme-brand.com"}'
```

## Resolution order

The domain served for a given share link is resolved at **mint time** and baked into the returned URL:

1. **BrandProfile custom domain** — if the mint used a specific BrandProfile with a per-profile domain.
2. **Tenant custom domain** — if set and verified.
3. **Tenant branded subdomain** — `{slug}-custom.lintpdf.com`.
4. **LintPDF default** — `reports.lintpdf.com`.

A share link minted while a custom domain was active keeps using that domain even if the customer later clears it — tokens are domain-immutable.

## Troubleshooting

**`verified=false` after >1 hour**

- Double-check the CNAME points at **exactly `edge.lintpdf.com`** (not `reports.lintpdf.com` from older guides — that's deprecated).
- Confirm DNS has propagated: `dig CNAME reports.yourdomain.com` should return `edge.lintpdf.com.`.
- Ensure no conflicting A/AAAA record on the same hostname.
- Hit the hostname with `curl -v https://reports.yourdomain.com/` and check the TLS handshake. If the cert issuance is still in flight, you'll see an ALPN handshake failure; retry after 30 seconds.

**`422 Unprocessable Entity` — "Invalid hostname"**

- Bare hostname only (no scheme, no path).
- Not on the blocklist (`lintpdf.com` + all subdomains, `localhost`, any `.local`, any IP literal).
- DNS-valid per RFC 1035 — no underscores, no leading/trailing hyphens.

**`409 Conflict` — "Domain already claimed"**

Another tenant is using the hostname. Contact `support@lintpdf.com` with both tenant IDs if this is a migration or ownership transfer.

## Security notes

- The edge validates every new hostname against our tenant / brand-profile registry before requesting a cert. An attacker can't point `evil.example.com` at our IP to trick us into issuing a cert for them.
- Cookies set by reports / the viewer are scoped to the customer's hostname — no cross-tenant leakage.
- Host-header rewriting at the edge means Railway's backend sees `reports.lintpdf.com` or `app.lintpdf.com`, not the customer's hostname. Backend logs are consistent regardless of which custom domain the request arrived on; `X-Forwarded-Host` carries the original hostname for tenant-level analytics.

## Related

- [Branded, LintPDF-Default, and Anonymous Outputs](/docs/branding-and-anonymous)
- [Share Links](/docs/share-links)
