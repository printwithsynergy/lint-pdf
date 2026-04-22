---
title: "Custom endpoints"
description: "Vanity submission URLs scoped to a specific profile + brand."
section: "panels"
order: 12
---

# Custom endpoints

**Path:** `/dashboard/endpoints` · **Who:** Owner / Admin

Create shareable submission URLs like `api.lintpdf.com/e/acme-press-check` that always run a specific profile with preset branding. Hand the URL to customers or hot-folder scripts so they don't need to know about profile IDs.

## What you see

- Table of existing endpoints: slug, target profile, brand profile, response mode, allowed origins (CORS), active flag.
- **Create endpoint** button → form with slug (lowercase alphanumeric + dashes), profile picker, optional brand picker, response-mode selector (`async` / `sync`).

## `response_mode`

- **`async`** *(default)* — submit returns `202 + job_id`; the caller polls `GET /api/v1/jobs/{id}` until the job finishes. Right choice for hot folders, batch integrations, or anything that already has a polling loop.
- **`sync`** — submit **blocks** for up to `LINTPDF_SYNC_MAX_WAIT_S` (default 120 s) and returns `200` + the full `JobResponse` once the job is terminal. Good for Zapier / n8n / Make.com flows that can't orchestrate polling. On timeout the handler falls back to the `202` response so the caller can keep polling.

Per-request override: pass `?wait=<seconds>` on the submit URL to temporarily flip modes (`?wait=0` forces async on a sync endpoint, `?wait=30` forces sync on an async endpoint with a 30 s ceiling).

## Actions

| Action | API | Notes |
|---|---|---|
| Create | `POST /api/v1/endpoints` | Slug must be globally unique across all tenants — picker warns on collisions. |
| Submit to endpoint | `POST /api/v1/endpoints/{slug}/submit` | Accepts multipart with `file`. Profile + brand are already baked in; you can't override at submit time unless the endpoint was configured with `allow_overrides=true`. |
| Rotate the slug | `PATCH /api/v1/endpoints/{id}` | Old slug 410s. Inform anyone still using it. |
| Revoke | `DELETE /api/v1/endpoints/{id}` | Slug becomes reusable after 30 days. |

## Gotchas

- **The endpoint URL is public** — anyone with the slug can submit. If that's not what you want, combine with per-endpoint API-key protection: `POST /endpoints/{slug}/submit` accepts `Authorization: Bearer` too.
- **Submissions count against your file-pack quota** exactly like `/api/v1/jobs` submissions. No separate metering.
- **CORS preflight** (`OPTIONS`) is handled automatically — the `allowed_origins` list is honoured.

## Related

- [Vanity endpoints](../vanity-endpoints) — deeper docs on the submit path
- [Rulesets](./rulesets) — authoring the profile the endpoint points at
