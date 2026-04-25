# Wave V V-07 / V-08 / V-12 Design Handoff

**Date:** 2026-04-25
**Source:** `audit/phase-0-v2/0.7-config-cascade-audit.md §0.7.2` (all 14 rows approved by Quincy in Phase 0 Q&A Q2)
**Per Q1 decision:** Ships in parallel with Tier-0 primitives.

This is the design handoff for the three Wave V foundation deliverables
that gate every other v2 toggle. Once these three land, every subsequent
wave can introduce toggleable knobs safely.

## V-07 — Toggle resolver (tenant → workflow → per-call)

### Schema

**New Prisma model `Toggle` (registry):**
```prisma
model Toggle {
  id            String   @id              // e.g. "checks.F-22", "epm_thresholds.tac_limit_coated_pct"
  category      String                    // "checks" | "profiles" | "categories" | "tiers" | "viewer_layers" | "epm_module" | "epm_thresholds" | "webhooks"
  human_name    String
  type          ToggleType                // BOOLEAN | NUMERIC | ENUM | STRING | OBJECT
  default_value Json
  allowed_range Json?                     // { min, max } for NUMERIC; [vals] for ENUM
  override_at   ToggleScope[]             // [TENANT, WORKFLOW, CALL]
  lockable      Boolean  @default(false)
  description   String?
  added_at      DateTime @default(now())
  deprecated_at DateTime?
}

enum ToggleType { BOOLEAN NUMERIC ENUM STRING OBJECT }
enum ToggleScope { TENANT WORKFLOW CALL }
```

**New Prisma model `ToggleOverride` (tenant/workflow/call values):**
```prisma
model ToggleOverride {
  id          String   @id @default(cuid())
  toggle_id   String                      // FK to Toggle.id
  scope       ToggleScope                 // TENANT | WORKFLOW | CALL
  scope_id    String                      // tenantId, workflowId, or callId
  value       Json
  locked      Boolean  @default(false)    // only meaningful when scope == TENANT
  set_by      String                      // userId or "system" or "api"
  set_at      DateTime @default(now())
  surface     String                      // "api" | "sdk" | "desktop"
  @@unique([toggle_id, scope, scope_id])
  @@index([scope, scope_id])
}
```

**New Prisma model `Workflow` (the missing first-class entity):**
```prisma
model Workflow {
  id          String   @id @default(cuid())
  tenantId    String                      // FK to Tenant
  slug        String                      // user-friendly: "packaging-flexo-folding-carton"
  human_name  String
  description String?
  is_default  Boolean  @default(false)    // exactly one per tenant
  created_at  DateTime @default(now())
  updated_at  DateTime @updatedAt
  @@unique([tenantId, slug])
  @@index([tenantId])
}
```

**Default workflow auto-created per tenant** with `is_default: true` to
preserve backward compat for callers that don't pass a workflow_id.

### Resolver

Single function in `packages/engine/src/lintpdf/tenants/config_resolver.py`:

```python
def resolve(toggle_id: str, *, tenant_id: str, workflow_id: str | None,
            call_overrides: dict | None) -> Any:
    """
    Resolution: per-call > workflow > tenant > Toggle.default_value.
    If a TENANT override has locked=True, lower scopes cannot override.
    """
```

Identical resolver consumed by:
- HTTP API: every endpoint that reads a configurable knob
- SDK: mirrors API
- Desktop: cached read via `/v1/toggles/resolve` endpoint

### Per-toggle merge strategy

Each Toggle declares `merge_strategy` (in `default_value` JSON or as
separate column): `replace | merge | union`. Examples:
- `checks.F-22.severity_override` → `replace`
- `epm_thresholds.rich_black_recipe` → `merge` (per-component override allowed)
- `ai_features` → `union` (set-union per existing entitlement merge)

### API surface

- `GET /v1/toggles` — list registry (paginated)
- `GET /v1/toggles/{id}` — single toggle metadata
- `GET /v1/toggles/resolve?toggle_id=...&workflow_id=...` — resolved value for current tenant
- `PUT /v1/tenant/toggles/{toggle_id}` — set tenant override
- `PUT /v1/workflows/{workflow_id}/toggles/{toggle_id}` — set workflow override
- Per-call overrides go in request body `overrides` map on existing endpoints

### Risk

Medium. Resolver perf must be cached per (tenant, workflow); cache invalidation on override write. Use existing tRPC + engine SQLAlchemy session.

## V-08 — Config audit log

### Schema

**New Prisma model `ConfigAuditLog`:**
```prisma
model ConfigAuditLog {
  id            String   @id @default(cuid())
  tenantId      String
  workflow_id   String?
  call_id       String?                   // for per-call overrides
  toggle_id     String                    // FK to Toggle.id
  override_path String                    // e.g. "tenant.checks.F-22.severity_override"
  old_value     Json?
  new_value     Json?
  set_by        String                    // userId or "system" or "api"
  set_at        DateTime @default(now())
  surface       String                    // "api" | "sdk" | "desktop"
  request_id    String?                   // for tracing
  @@index([tenantId, set_at])
  @@index([toggle_id, set_at])
}
```

### Middleware

tRPC middleware on every config-mutating router (tenant, workflow, toggle,
webhook, etc.) that intercepts the mutation, captures old → new, writes
to `ConfigAuditLog` before the actual mutation commits.

```typescript
// packages/app/server/middleware/audit-log.ts
export const auditLogMiddleware = t.middleware(async ({ ctx, path, input, next }) => {
  const oldValue = await ctx.readCurrentValue(input.toggle_id, input.scope);
  const result = await next();
  if (result.ok) {
    await ctx.prisma.configAuditLog.create({
      data: { tenantId: ctx.tenantId, toggle_id: input.toggle_id,
              old_value: oldValue, new_value: input.value,
              set_by: ctx.userId, surface: ctx.surface,
              request_id: ctx.requestId },
    });
  }
  return result;
});
```

### Engine-side parity

Engine's per-call override audit-logged via FastAPI middleware on `POST /v1/jobs` and other endpoints accepting `overrides`. Same schema; engine writes via shared SQLAlchemy session that maps to the same Postgres table (Prisma owns the schema; engine reads via SQLAlchemy ORM mapping).

### Endpoint

- `GET /v1/audit-log?tenant_id=...&toggle_id=...&since=...` — read for compliance
- Retention per tenant data-retention policy

### Risk

Low. Additive; no breaking change. Volume estimate: ~10 mutations/tenant/day → tiny load.

## V-12 — Legacy config migration script

### Goal

Read existing `Tenant.settings` JSON (open-shape, per-tenant); materialize
into typed `Workflow` + `ToggleOverride` rows; preserve current behavior
for every tenant.

### Path

`packages/app/scripts/migrate-legacy-config.ts`

### Algorithm

```
For each tenant in Tenant table:
  1. Create default Workflow (slug="default", human_name="Default", is_default=true)
  2. Read tenant.settings JSON
  3. For each known legacy field:
       - branding.* → tenant Toggle override
       - aiCredits.* → tenant Toggle override
       - viewer.* → tenant Toggle override
       - profile-related fields → workflow Toggle override on the default workflow
  4. Audit-log every override with surface="migration", set_by="system:V-12"
  5. Set tenant.legacy_settings_migrated_at = now()
  6. (Read mirror) keep tenant.settings populated for one release cycle for safety; remove in v2.1
```

### Idempotent + reversible

- **Idempotent:** running twice is a no-op for already-migrated tenants. Check `legacy_settings_migrated_at`; skip if set.
- **Reversible:** every migration writes to `ConfigAuditLog`; reverse-migration script can read the log and restore Tenant.settings JSON shape.
- **Safe:** dry-run mode (`--dry-run`) prints planned mutations without writing.

### Test fixture

Generate 50+ synthetic tenants with varied legacy settings shapes (empty, partial, full), run migration in test DB, verify resolver returns identical config values pre and post migration.

### Risk

**Medium-high.** Touches every tenant. Pre-flight checklist:
1. Dry-run on full prod-like fixture (50+ tenants, varied shapes)
2. Verify config resolver returns identical values for pre/post tenant
3. Snapshot `Tenant.settings` table to S3 before running prod migration
4. Run migration in transaction per tenant (not all-at-once); roll back on any tenant error
5. Ship one Postgres migration that adds `legacy_settings_migrated_at` column with default `null` first
6. Run V-12 script second
7. After 1 release cycle of stability, ship Tenant.settings deprecation in v2.1

### Approval gate per playbook §17.3

Quincy must explicitly sign off on the migration before prod execution.
Phase 0 Q2 approved the **plan**; the operational green-light for prod
run is a separate gate during Wave V execution.

## V-07 + V-08 + V-12 sequencing within Wave V

```
1. Migrations: add ConfigAuditLog table → add Toggle/ToggleOverride/Workflow tables
                                         → add Tenant.legacy_settings_migrated_at column
2. Resolver code: tRPC + engine FastAPI parity
3. Audit-log middleware: tRPC + engine
4. V-12 dry-run on test DB
5. V-12 staging dry-run + verification
6. V-12 production run (per-tenant transactions)
7. Documentation: OpenAPI 3.1 for /v1/toggles + /v1/workflows + /v1/audit-log
```

Estimated EM: V-07 (1.0) + V-08 (0.5) + V-12 (1.0) = **~2.5 EM combined**, plus 1.0 EM for migrations / docs / testing = **~3.5 EM total**.

## Open design decisions

These are non-blocking but worth confirming before V-07 coding starts:

1. **Toggle.id naming convention:** dot-notation (e.g. `checks.F-22.severity_override`) vs flat slug (e.g. `check_F22_severity`). Recommend dot-notation for hierarchical queries.
2. **Workflow inheritance from another workflow:** v2 spec says "single tenant → workflow level"; should we support `parent_workflow_id` for inheritance chains? Recommend **no** — single layer for v2.0; revisit v2.1 if requested.
3. **Lockable for non-tenant overrides:** can a workflow lock an override to prevent per-call override? Spec says only tenant locks. Recommend **only tenant** for v2.0.
4. **ConfigAuditLog retention:** 90 days default? Per-tenant configurable? Recommend 365 days default; tenant override allowed.

These can be batched as a follow-up Q&A before V-07 coding starts (or inferred from playbook §16.2).
