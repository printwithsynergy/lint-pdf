---
title: "API reference (in-app)"
description: "Interactive Swagger UI inside the dashboard — same tenant-only slice as the marketing site."
section: "panels"
order: 10
---

# API reference (in-app)

**Path:** `/dashboard/api-reference` · **Who:** Any signed-in tenant user

Swagger UI pointed at `/openapi.tenant.json` — every route your API key can call, with try-it-out enabled. Same payload as the marketing-site [`/swagger`](/swagger) but inside the authenticated dashboard so your key + cookies are already handy.

## What you see

- Full tenant API surface grouped by OpenAPI tag: `jobs`, `reports`, `webhooks`, `branding`, `imports`, `ai-*`, `profiles`, etc.
- Authorize button at the top to paste your API key (stored in browser memory only — not persisted).
- Per-route: request / response schemas, example payloads, "Try it out" to fire a live request.

## Actions

- **Authorize** — paste `lpdf_live_...`; gets sent as `Authorization: Bearer ...` on every try-it request.
- **Execute** — fires the request, shows status + response.
- **Copy curl** — every form generates the curl equivalent.

## Gotchas

- **This is the tenant slice.** Admin endpoints aren't here. Super-admins use `/dashboard/admin/swagger` for the full spec.
- **Try-it-out runs live against production.** Don't hit destructive endpoints (webhook delete, etc.) unless you mean it.
- **Authorize state resets on refresh.** The key isn't persisted — paste it every session.

## Related

- [Postman collection](../postman) — same spec, but downloadable
- [Authentication](../authentication) — auth header format + rotation
