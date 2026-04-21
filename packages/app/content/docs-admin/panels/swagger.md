---
title: "Swagger (admin)"
description: "Full OpenAPI spec with every admin route; try-it-out enabled."
---

# Swagger (admin)

**Path:** `/dashboard/admin/swagger` · **Who:** Super admin · **Scope:** Global

Interactive Swagger UI loading `/openapi.json` (the full spec including every admin route). Use this when you need to poke at an admin endpoint interactively without fighting `curl` quoting.

## What you see

- Swagger UI 5.x, loaded from CDN, pointed at `https://api.lintpdf.com/openapi.json`.
- Authorize button → two API-key fields: `APIKeyHeader` (for tenant-scoped endpoints, `Authorization: Bearer`) and `X-Admin-Key` (for admin endpoints).
- Deep-linking enabled — you can bookmark a specific operation.

## Actions

All operations in the spec work from this UI: fill in the form → click Execute → see the raw request + response + curl equivalent.

## Gotchas

- **Don't authorise with a live customer's API key.** This is a shared admin surface; a mistake here could issue real requests on their behalf. Use a dedicated test-tenant key for try-it-out against tenant routes.
- Swagger UI caches the loaded spec per browser session. If a new engine deploy adds routes, hard-reload the page (`Shift+R` → Swagger UI then re-fetches).
- The tenant-only slice lives at `/dashboard/api-reference` — reachable by customers too. This admin version is strictly for ops.

## Related

- [Admin APIs + Swagger](../admin-api) for the read-me.
