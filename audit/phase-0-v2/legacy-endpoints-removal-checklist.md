# Legacy CustomEndpoint hard-removal — pre-flight checklist

> **Status:** **Deferred** until telemetry confirms zero traffic to
> `/dashboard/endpoints` and `/api/v1/endpoints` for ≥30 days.
>
> Author: v2 playbook PR 22 (2026-04-27).

The Phase 0.7 unified-config substrate ships **Workflows** as the
replacement for legacy CustomEndpoint vanity slugs. PR 13 added the
deprecation banner; PR 17 + PR 22 docs document the migration. The
final destructive cleanup must wait for telemetry to confirm no live
integrations remain, per the project Working Agreements ("no
destructive deletion without observation window").

## Pre-flight gate

Before opening the hard-removal PR, confirm **all** of:

- [ ] **Engine telemetry**: zero Successful 2xx responses on
      `GET/POST/PUT/DELETE /api/v1/endpoints*` for 30 consecutive days.
      Query: `lintpdf_http_requests_total{path=~"/api/v1/endpoints.*"}`
      via Prometheus.
- [ ] **App telemetry**: zero pageviews on `/dashboard/endpoints` for
      30 consecutive days. Either Pixie Dust analytics or the
      Plausible / GA hook the dashboard uses.
- [ ] **Tenant outreach**: every tenant whose `custom_endpoints` table
      row count > 0 has been notified via in-product banner + email
      with a 14-day final notice.
- [ ] **Decision recorded** in this checklist (date + reviewer).

## Destructive PR scope

When the gate clears, open the hard-removal PR with these changes
*in this order*:

1. **Alembic migration** —
   `packages/engine/alembic/versions/052_drop_legacy_endpoints.py`:
   - `op.drop_constraint(...)` for any FK referencing `custom_endpoints`
     or `Job.brand_spec_id` (if it survived earlier passes).
   - `op.drop_table("custom_endpoints")`.
   - Reverse-migration restores empty tables (data is unrecoverable;
     document in the migration's docstring explicitly).
2. **ORM cleanup** —
   `packages/engine/src/lintpdf/api/models.py`:
   - Delete the `CustomEndpoint` ORM class.
   - Delete the `endpoints` router include + the
     `lintpdf.api.routes.endpoints` module.
3. **Dashboard cleanup** —
   - Delete `packages/app/app/dashboard/endpoints/` entirely.
   - Add a 308 redirect at the framework router level so old bookmarks
     land on `/dashboard/workflows`.
4. **Plugin + SDK cleanup** —
   - Remove `endpointRoutes` from
     `packages/plugin/src/index.ts:addRoutes()` and delete the
     `endpoints.ts` route module.
   - Delete any `Endpoint` class + methods from
     `packages/sdk-python/lintpdf/__init__.py` (if any survived
     earlier passes).
5. **Postman cleanup** — remove the `endpoints` folder from both
   `lintpdf-all.postman_collection.json` and
   `lintpdf-tenant.postman_collection.json`.
6. **Desktop cleanup** —
   `packages/desktop/src-tauri/src/db.rs`: remove the
   one-time CustomEndpoint → Workflow migration shim added by PR 14.
   Local-state schema is now Workflow-only.

## Observability hooks

To verify the telemetry gate before merging:

```bash
# Engine HTTP — last 30 days
curl -s "$PROMETHEUS_URL/api/v1/query?query=increase(lintpdf_http_requests_total%7Bpath%3D~%22%2Fapi%2Fv1%2Fendpoints.*%22%7D%5B30d%5D)"

# App pageviews — depends on which provider; Pixie Dust analytics:
psql "$LINTPDF_DATABASE_URL" -c \
  "SELECT count(*) FROM analytics_pageview \
   WHERE path LIKE '/dashboard/endpoints%' \
   AND occurred_at > now() - interval '30 days';"
```

## Rollback

If the destructive PR ships and a tenant *does* report a regression:

1. **Don't undo the alembic migration** — reversing a column drop
   loses zero data (the columns were already empty), but the lost
   work is the migration ordering. Roll forward instead.
2. Open a follow-up PR that re-introduces a stub
   `/api/v1/endpoints` route returning `404 Gone` with a `Link:`
   header pointing at `/api/v1/workflows`.
3. Notify the affected tenant via Slack + email + in-product banner.

## Reviewer checklist for the destructive PR

- [ ] Pre-flight gate above is fully checked.
- [ ] Alembic `revision` runs cleanly on a copy of staging.
- [ ] Alembic `downgrade -1` runs cleanly (and documents the data loss).
- [ ] Pre-push hook + CI green.
- [ ] No remaining grep matches for `CustomEndpoint`, `custom_endpoints`,
      or `endpoint_slug` outside of this checklist + the migration file.
