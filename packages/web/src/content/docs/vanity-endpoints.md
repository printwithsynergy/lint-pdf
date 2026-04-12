---
title: "Vanity Submission Endpoints"
description: "Bind a short URL slug to a preflight profile so integrations can submit without specifying profile_id every time."
section: "viewer-workflow"
order: 40
---

# Vanity Submission Endpoints

Vanity endpoints let you create short, memorable submission URLs bound to a specific preflight profile. An integration that always submits against the same profile (hot folder, MIS webhook, Zapier flow) can POST to `/api/v1/endpoints/{slug}/submit` instead of `/api/v1/jobs` and skip the `profile_id` form field — cleaner curls, cleaner audit logs, and a single place to swap the target profile without touching every caller.

**Entitlement**: Growth plan or above.

## Create

```bash
curl -X POST https://api.lintpdf.com/api/v1/endpoints \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "trade-show-packaging",
    "profile_id": "pdf-x-4p",
    "description": "Trade-show booth PDFs go through PDF/X-4"
  }'
```

Response:

```json
{
  "id": "a12b3c4d-...",
  "slug": "trade-show-packaging",
  "profile_id": "pdf-x-4p",
  "description": "Trade-show booth PDFs go through PDF/X-4",
  "is_active": true,
  "created_at": "2026-04-12T14:30:00Z"
}
```

### Slug rules

- Lowercase ASCII letters, digits, and hyphens.
- 3–63 characters.
- Must start and end with a letter or digit.
- Unique per tenant (cross-tenant collisions are allowed; slugs are namespaced by the tenant that owns the endpoint).

Invalid slugs return `422`. Slug collisions within a tenant return `409`.

## List

```bash
curl https://api.lintpdf.com/api/v1/endpoints \
  -H "Authorization: Bearer lpdf_live_..."
```

## Update

Partial update — every field is optional:

```bash
curl -X PATCH https://api.lintpdf.com/api/v1/endpoints/{endpoint_id} \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{"profile_id": "gwg-sheetfed"}'
```

Updatable fields: `slug`, `profile_id`, `description`, `is_active`. Inactive endpoints reject submissions with `404` (same behavior as unknown slugs — avoids leaking endpoint-existence information).

## Delete

```bash
curl -X DELETE https://api.lintpdf.com/api/v1/endpoints/{endpoint_id} \
  -H "Authorization: Bearer lpdf_live_..."
```

## Submit against a vanity endpoint

```bash
curl -X POST https://api.lintpdf.com/api/v1/endpoints/trade-show-packaging/submit \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@booth-01.pdf
```

The endpoint's bound `profile_id` is implicit. All other `/api/v1/jobs` form fields still work:

```bash
curl -X POST https://api.lintpdf.com/api/v1/endpoints/trade-show-packaging/submit \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@booth-01.pdf \
  -F external_report=@pitstop.xml \
  -F preflight_source=external \
  -F external_format=pitstop_xml \
  -F brand=anonymous
```

## When to prefer over `/api/v1/jobs`

- **Automation clients** — hot folders, MIS integrations, Zapier/Make/n8n flows that always run the same profile.
- **Multi-tenant integrations** — the slug is part of the URL, so your integration config is just a URL + API key.
- **Audit clarity** — the endpoint's `slug` appears on every resulting job, making it easy to filter submissions by integration.

Prefer plain `/api/v1/jobs` when:

- The profile changes per submission (you'd constantly re-PATCH the endpoint or create dozens of endpoints).
- You're a one-off / ad-hoc caller.

## Permissions

- **Create / update / delete** — `preflight:submit`.
- **Submit** — any API key that can submit jobs (`preflight:submit`).

## Related

- [API Reference](/docs/api-reference)
- [Preflight Modes](/docs/preflight-modes)
- [Integrations Overview](/docs/integrations-overview)
