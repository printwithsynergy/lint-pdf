---
title: "Admin APIs + Swagger"
description: "Overview of the admin REST surface and where to find the interactive reference."
---

# Admin APIs

The engine exposes two OpenAPI surfaces:

- **Tenant** (`/openapi.tenant.json`) — everything a customer can call with their `lpdf_live_...` key. Rendered on the public marketing site at `lintpdf.com/swagger` and as the interactive reference inside the authenticated app at `/dashboard/api-reference`.
- **Full / admin** (`/openapi.json`) — every route, including the admin surface gated by `X-Admin-Key`. Available only inside the authenticated dashboard at **[`/dashboard/admin/swagger`](/dashboard/admin/swagger)**.

## Authentication

Admin routes authenticate via the `X-Admin-Key` header:

```sh
curl -H "X-Admin-Key: $LINTPDF_ADMIN_API_KEY" \
  https://api.lintpdf.com/api/v1/admin/tenants?page=1
```

The key lives in Railway as `LINTPDF_ADMIN_API_KEY` on the API service. It's shared — there's no per-user admin key today. Rotate via the Railway dashboard if it leaks; the engine reads it fresh on each request.

## Tag groups

| Tag | Routes | What they do |
|---|---|---|
| `admin` | `/api/v1/admin/*` | Tenant CRUD, API-key minting, plan overrides, custom-domain controls |
| `admin-billing` | `/api/v1/admin/tenants/{id}/*` (billing subpaths) | File-pack + AI-credit overrides, grant/revoke metered packages |
| `admin-webhooks` | `/api/v1/admin/webhooks/*` | Cross-tenant dead-letter list + replay |
| `admin-trials` | `/api/v1/admin/trials/*` | Trial submission queue, preflight trigger, send-report |
| `admin-audit` | `/api/v1/admin/audit/*` | Preflight history + finding-level drill-down |
| `admin-health` | `/api/v1/admin/warming`, `/api/v1/admin/custom-domains` | Ops probes |

Use the Swagger UI for the authoritative, try-it-out reference — this page exists as a pointer, not a mirror.

## Related runbooks

- [Replay a dead webhook delivery](../runbooks/webhook-dlq-replay)
- [Run the preflight script end-to-end](../runbooks/run-preflight-script)
- [Seed the Print-With-Synergy demo tenant](../runbooks/pws-onboarding)
