---
title: "Workflows"
description: "Pin a profile + brand spec + per-call override defaults under a single name. Replaces legacy CustomEndpoint vanity slugs."
section: "integrations"
order: 30
---

# Workflows

A **Workflow** pins a curated configuration — a profile, an optional brand spec, and per-call ToggleOverride defaults — under a single named handle. Tenants submit jobs with `workflow_id=...` instead of re-specifying every field on every call.

Workflows replace the legacy `/api/v1/endpoints` custom-endpoint surface that shipped before the Phase 0.7 unified-config substrate. The legacy endpoints page on the dashboard is still reachable but carries a deprecation banner pointing at `/dashboard/workflows`.

## Why workflows over endpoints

The legacy endpoints surface tied a slug to a profile + brand spec but couldn't hold per-call ToggleOverrides (the threshold packs that come out of the Phase 0.7 substrate). Workflows are the union of "named slug" + "per-call defaults" so a tenant can ship multiple curated configurations against the same engine without juggling profile + brand spec + override JSON on every submit.

## Endpoints

### List workflows

```
GET /api/v1/workflows
Authorization: Bearer lpdf_live_...
```

```json
{
  "workflows": [
    {
      "id": "w1",
      "name": "Coated stock",
      "profile_id": "lintpdf-default",
      "brand_spec_id": null,
      "created_at": "2026-04-20T12:00:00Z"
    }
  ]
}
```

### Create

```
POST /api/v1/workflows
Content-Type: application/json
Authorization: Bearer lpdf_live_...

{
  "name": "Uncoated stock",
  "profile_id": "lintpdf-default",
  "brand_spec_id": null
}
```

### Update

```
PATCH /api/v1/workflows/{workflow_id}
Content-Type: application/json
Authorization: Bearer lpdf_live_...

{ "name": "Renamed" }
```

### Delete

```
DELETE /api/v1/workflows/{workflow_id}
Authorization: Bearer lpdf_live_...
```

Returns `204 No Content`.

## Where it shows up

- **Dashboard** — `/dashboard/workflows` provides a CRUD UI.
- **Desktop, SDK, plugin, Postman, JSX docs** — all five ship the same surface 1:1.

## Migration from CustomEndpoint

The legacy `CustomEndpoint` rows continue to work in the engine until telemetry shows zero traffic to `/dashboard/endpoints`. After that observation window, the legacy table + UI are hard-removed (a one-time alembic migration ships the column drops). Existing endpoint slugs continue to resolve until that PR lands.

If you have integrations against the legacy `/endpoints` slug, migrate them to a Workflow:

1. List your existing endpoints: `GET /api/v1/endpoints`.
2. For each, create a Workflow with the same profile_id + brand_spec_id.
3. Update your integration to submit with `workflow_id=...` instead of hitting the slug.
4. Delete the old endpoint when traffic moves over.
