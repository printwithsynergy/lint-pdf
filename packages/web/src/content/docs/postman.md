---
title: "Postman Collection"
description: "Download the auto-generated Postman collection for every LintPDF endpoint."
section: "api"
order: 38
---

# Postman collection

Both collections are auto-generated from the engine's OpenAPI spec and
published under [`docs/postman/`](https://github.com/thinkneverland/lint-pdf/tree/main/docs/postman)
in the public repo. Re-generate anytime with:

```sh
python tools/generate_postman.py \
  --full-url https://api.lintpdf.com/openapi.json \
  --tenant-url https://api.lintpdf.com/openapi.tenant.json
```

## Which file do I want?

| Collection | Download | Use when |
|---|---|---|
| **Tenant** (recommended) | [`lintpdf-tenant.postman_collection.json`](https://raw.githubusercontent.com/thinkneverland/lint-pdf/main/docs/postman/lintpdf-tenant.postman_collection.json) | You're a customer with an `lpdf_live_...` API key. Excludes admin + trial-submit routes. |
| **All** (admin / ops) | [`lintpdf-all.postman_collection.json`](https://raw.githubusercontent.com/thinkneverland/lint-pdf/main/docs/postman/lintpdf-all.postman_collection.json) | Ops or integration work that needs the admin surface too. Requires `X-Admin-Key`. |

## Quick start

1. Download the collection JSON (right-click → Save link as… or use the
   curl snippets below).
2. In Postman, **Import** the file.
3. Click the collection name → **Variables** tab.
4. Set `API_KEY` to your `lpdf_live_...` key. (For the All collection,
   also set `ADMIN_KEY` for admin endpoints.)
5. Send any request — `BASE_URL` already points at `https://api.lintpdf.com`.

```sh
# Tenant
curl -O https://raw.githubusercontent.com/thinkneverland/lint-pdf/main/docs/postman/lintpdf-tenant.postman_collection.json

# All (admin)
curl -O https://raw.githubusercontent.com/thinkneverland/lint-pdf/main/docs/postman/lintpdf-all.postman_collection.json
```

## Live Swagger alternative

Prefer browser try-it-out over Postman? The same spec powers the
**[interactive API reference](/swagger)** — Authorize with your API key
once and hit Send without leaving the page.

## What's inside

Each endpoint in the collection carries:

- A working URL pre-wired to the `BASE_URL` variable.
- The right auth header (`Authorization: Bearer {{API_KEY}}` for tenant
  routes; `X-Admin-Key: {{ADMIN_KEY}}` for admin routes).
- An example JSON body generated from the endpoint's schema (including
  the five new per-endpoint webhook retry + retention fields, the
  universal `/state` digest, and every webhook event shape).
- Query + path parameter placeholders with descriptions from the spec.

Endpoints are grouped by their OpenAPI tag so folders map one-to-one to
sections in the Swagger UI.
