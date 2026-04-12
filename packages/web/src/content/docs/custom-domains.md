---
title: "Custom Domains"
description: "Serve reports and the viewer from your own hostname (reports.yourdomain.com / app.yourdomain.com)."
section: "branding"
order: 32
---

# Custom Domains

Scale and Enterprise tiers can serve hosted reports and the interactive viewer from hostnames they own — `reports.yourdomain.com` instead of `reports.lintpdf.com`, and `app.yourdomain.com` instead of `app.lintpdf.com`. Custom domains are separate from branding: a tenant can be fully anonymous (no tenant or LintPDF chrome) *and* serve from a custom hostname, which is the typical broker-to-distributor configuration.

LintPDF tracks two independent custom domains per tenant:

- **Report domain** — used for share-link PDF/HTML URLs (`reports.yourdomain.com/r/{token}`).
- **App (viewer) domain** — used for the interactive dashboard and viewer (`app.yourdomain.com/share/{token}`).

Plus optional **per-BrandProfile** report domains, so a tenant with multiple brand identities can serve each brand's reports from its own hostname.

## DNS setup

All three domain types point at the same `CNAME` target:

```
CNAME target: reports.lintpdf.com
```

### Example DNS records

| Hostname | Type | Value | TTL |
|---|---|---|---|
| `reports.yourdomain.com` | CNAME | `reports.lintpdf.com` | 300 |
| `app.yourdomain.com` | CNAME | `reports.lintpdf.com` | 300 |
| `reports.acme-brand.com` | CNAME | `reports.lintpdf.com` | 300 |

The same edge infrastructure serves every custom hostname — LintPDF routes by `Host` header, issues an ACME-backed TLS certificate for each domain, and handles renewal. You don't need to provision certificates yourself.

### Blocklisted hostnames

The following are rejected at the API (HTTP `422`):

- `lintpdf.com` and all subdomains of `lintpdf.com` (reserved).
- `localhost`, `*.local`, `*.internal`.
- Railway platform hostnames.
- Any IP address.
- Any domain already claimed by another tenant (HTTP `409`).

## Request a domain

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
  "requested_at": "2026-04-12T14:30:00Z",
  "plan_allows_whitelabel": true,
  "dns_target": "reports.lintpdf.com"
}
```

Fields:

- `verified` — flips to `true` once our edge detects the CNAME resolves correctly. Polling interval is ~1 minute; typical end-to-end propagation is 5–30 minutes.
- `requested_at` — set on every PATCH that changes the domain.
- `plan_allows_whitelabel` — `false` on tiers below Scale; the domain is stored but not served until you upgrade.
- `dns_target` — always `reports.lintpdf.com`.

## Inspect current domain

```bash
curl https://api.lintpdf.com/api/v1/tenants/{tenant_id}/custom-domain \
  -H "Authorization: Bearer lpdf_live_..."
```

## Clear the domain

Pass `null`:

```bash
curl -X PATCH https://api.lintpdf.com/api/v1/tenants/{tenant_id}/custom-domain \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{"domain": null}'
```

This reverts the tenant to `reports.lintpdf.com` and releases the domain for other tenants to claim (after a 24-hour grace period).

## App (viewer/dashboard) domain

Same shape, different endpoint:

```bash
curl -X PATCH https://api.lintpdf.com/api/v1/tenants/{tenant_id}/app-custom-domain \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{"domain": "app.yourdomain.com"}'
```

```bash
curl https://api.lintpdf.com/api/v1/tenants/{tenant_id}/app-custom-domain \
  -H "Authorization: Bearer lpdf_live_..."
```

## Per-BrandProfile domain

Override the tenant-level report domain for a specific BrandProfile. Useful when a tenant operates multiple brands and each brand's reports should live at its own hostname:

```bash
curl -X PATCH https://api.lintpdf.com/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}/custom-domain \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{"domain": "reports.acme-brand.com"}'
```

A share link minted while the `acme-brand` BrandProfile was active will return URLs at `reports.acme-brand.com`; links minted with a different profile continue to use the tenant's default domain.

## Resolution order

The domain served for a given share link is resolved at **mint time** and baked into the returned URL:

1. **BrandProfile custom domain** — if the mint used a specific BrandProfile with a per-profile domain.
2. **Tenant report domain** — if set and verified.
3. **LintPDF default** — `reports.lintpdf.com`.

If a domain was verified at mint but is later invalidated (CNAME removed, plan downgraded), existing tokens continue to work — LintPDF keeps the DNS and TLS in place for 30 days after a downgrade/removal to avoid broken links.

## Troubleshooting

**`verified=false` after >1 hour**

- Double-check the CNAME points at `reports.lintpdf.com` (not `reports.lintpdf.com.` with a trailing dot — most providers accept either but some strip it).
- Confirm your DNS provider has fully propagated: `dig CNAME reports.yourdomain.com` should return `reports.lintpdf.com.` as the answer.
- Ensure no conflicting A/AAAA record on the same hostname.

**`409 Conflict` — "Domain already claimed"**

Another tenant is using the hostname. Contact support (`support@lintpdf.com`) with both tenants' IDs if this is a migration or ownership transfer.

**`422 Unprocessable Entity` — "Invalid hostname"**

- Bare hostname only (no scheme, no path).
- Not on the blocklist.
- DNS-valid (RFC 1035 — no underscores, no leading/trailing hyphens).

## Related

- [Branded, LintPDF-Default, and Anonymous Outputs](/docs/branding-and-anonymous)
- [Share Links](/docs/share-links)
