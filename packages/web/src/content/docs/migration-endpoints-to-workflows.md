---
title: "Migration: Endpoints → Workflows"
description: "How to migrate from legacy CustomEndpoint vanity slugs to the Phase 0.7 Workflow substrate before the legacy surface is hard-removed."
section: "integrations"
order: 35
---

# Migration: Endpoints → Workflows

The legacy **CustomEndpoint** surface (`/api/v1/endpoints` + `/dashboard/endpoints`) is being replaced by **Workflows** (`/api/v1/workflows` + `/dashboard/workflows`). Workflows are the unified-config substrate that ships with Phase 0.7 — they pin a profile + brand spec **plus** per-call ToggleOverride defaults under a single named handle, where Endpoints could only pin profile + brand spec.

## Timeline

1. **Now** — Workflows ship alongside legacy Endpoints. Both surfaces are functional. The dashboard's Endpoints page carries a deprecation banner.
2. **Observation window (≥30 days)** — Telemetry tracks any traffic to `/dashboard/endpoints` and `/api/v1/endpoints`. If traffic stays zero for the window, the legacy surface is eligible for hard-removal.
3. **Hard-removal PR** — Once telemetry confirms zero traffic:
   - Alembic migration `052_drop_legacy_endpoints.py` drops the `custom_endpoints` table and the `Job.brand_spec_id` / `CustomEndpoint.default_brand_spec_id` columns.
   - ORM `CustomEndpoint` class is deleted from `lintpdf.api.models`.
   - Dashboard `/dashboard/endpoints` page is deleted; the framework router stamps a 308 redirect to `/dashboard/workflows` so old bookmarks still land somewhere useful.
   - Postman folders named "endpoints" are removed from both collections.
   - SDK `Endpoint` class + methods are deleted (if any survived earlier passes).

   **Until telemetry shows zero traffic, the destructive parts are deferred** — per the project Working Agreements, we never hard-delete a surface that's still in use.

## How to migrate

If you have integrations against the legacy `/api/v1/endpoints` slug surface, point them at Workflows instead:

### 1. List your existing endpoints

```bash
curl -H "Authorization: Bearer $LINTPDF_API_KEY" \
  https://api.lintpdf.com/api/v1/endpoints
```

Note the `slug`, `profile_id`, `default_brand_spec_id` for each.

### 2. Create a Workflow per endpoint

```bash
curl -X POST -H "Authorization: Bearer $LINTPDF_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"name":"Coated stock","profile_id":"lintpdf-default","brand_spec_id":null}' \
     https://api.lintpdf.com/api/v1/workflows
```

Capture the returned `id` — that's the new handle.

### 3. Update your integration

The legacy submit path was:

```bash
POST /api/v1/endpoints/{slug}/submit
```

The new submit path attaches a workflow at job-submit time:

```bash
POST /api/v1/jobs
Content-Type: multipart/form-data
Authorization: Bearer ...

file=@brochure.pdf
workflow_id=<new-uuid>
```

### 4. Delete the old endpoint

Once your integration is on Workflows and you've confirmed it's processing jobs end-to-end:

```bash
curl -X DELETE -H "Authorization: Bearer $LINTPDF_API_KEY" \
  https://api.lintpdf.com/api/v1/endpoints/<old-id>
```

This frees up the slug for a new Workflow + drops the row from the deprecated table before the hard-removal pass clears it for you.

## Why migrate now (not later)

- **Per-call overrides** — Workflows can pin ToggleOverride defaults (rich-black recipe, TAC limits, ΔE budget) that legacy Endpoints can't carry. Once you migrate, you can curate threshold packs per workflow without changing the engine profile.
- **Audit alignment** — Decisions logged from a workflow-submitted job carry the workflow id in `decision_metadata`. The legacy endpoint slug is opaque in audit reports.
- **Cleaner dashboard** — `/dashboard/workflows` shows the new surface; the legacy page is being removed in the hard-removal PR.

## What about share links and approval chains?

Both surfaces continue to work unchanged. Share-link minting is keyed off the job, not the endpoint/workflow. Approval chains attach to jobs by id and are unaffected by the migration.
