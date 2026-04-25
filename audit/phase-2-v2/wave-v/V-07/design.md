# Wave V V-07 — Toggle Resolver Design

**Wave:** V (parallel with Tier-0 per Phase 0 Q1)
**Deliverable:** Toggle registry + tenant→workflow→per-call resolver + Workflow first-class entity
**EM estimate:** 1.0
**Design date:** 2026-04-25
**Dependency:** None — foundation
**Per Phase 1 Q4 approved defaults:** dot-notation IDs, no workflow-from-workflow inheritance, lockable only at tenant scope

## What this delivers

The single resolver consumed by every endpoint, SDK call, and desktop action
that reads a configurable knob. Resolution order: **per-call > workflow >
tenant > registry default**. Locked tenant overrides cannot be replaced by
lower scopes.

After V-07 lands, every new toggleable knob in subsequent waves uses this
resolver — no per-call ad-hoc merging, no per-endpoint config logic.

## New Prisma models

**File:** `packages/app/prisma/schema/workflows.prisma` (NEW)

```prisma
model Workflow {
  id           String   @id @default(cuid())
  tenantId     String                      // FK to Tenant.id
  slug         String                      // user-friendly: "packaging-flexo-folding-carton"
  human_name   String
  description  String?
  is_default   Boolean  @default(false)    // exactly one per tenant
  created_at   DateTime @default(now())
  updated_at   DateTime @updatedAt
  tenant       Tenant   @relation(fields: [tenantId], references: [id], onDelete: Cascade)
  toggle_overrides ToggleOverride[]

  @@unique([tenantId, slug])
  @@index([tenantId])
}
```

**File:** `packages/app/prisma/schema/toggles.prisma` (NEW)

```prisma
enum ToggleType {
  BOOLEAN
  NUMERIC
  ENUM
  STRING
  OBJECT
}

enum ToggleScope {
  TENANT
  WORKFLOW
  CALL
}

enum MergeStrategy {
  REPLACE     // per-call replaces lower scope value entirely
  MERGE       // per-component merge for OBJECT-typed toggles
  UNION       // set-union for array values (e.g. ai_features)
}

model Toggle {
  id              String         @id              // dot-notation: "checks.F-22.severity_override"
  category        String                          // "checks" | "profiles" | "categories" | "tiers" | "viewer_layers" | "epm_module" | "epm_thresholds" | "webhooks"
  human_name      String
  type            ToggleType
  default_value   Json                            // type-validated against `type`
  allowed_range   Json?                           // {min, max} for NUMERIC; [vals] for ENUM
  override_at     ToggleScope[]                   // which scopes can override
  lockable        Boolean        @default(false)  // can a tenant lock this?
  merge_strategy  MergeStrategy  @default(REPLACE)
  description     String?
  added_at        DateTime       @default(now())
  deprecated_at   DateTime?
  overrides       ToggleOverride[]

  @@index([category])
}

model ToggleOverride {
  id          String       @id @default(cuid())
  toggle_id   String                              // FK to Toggle.id
  scope       ToggleScope                         // TENANT | WORKFLOW | CALL
  scope_id    String                              // tenantId, workflowId, or callId
  value       Json
  locked      Boolean      @default(false)        // only meaningful when scope == TENANT
  set_by      String                              // userId or "system" or "api"
  set_at      DateTime     @default(now())
  surface     String                              // "api" | "sdk" | "desktop"

  toggle      Toggle       @relation(fields: [toggle_id], references: [id], onDelete: Cascade)
  workflow    Workflow?    @relation(fields: [scope_id], references: [id], onDelete: Cascade)

  @@unique([toggle_id, scope, scope_id])
  @@index([scope, scope_id])
}
```

## Resolver

**File:** `packages/engine/src/lintpdf/tenants/config_resolver.py` (NEW)

```python
from typing import Any
from sqlalchemy.orm import Session

class ConfigResolver:
    """Tenant → workflow → per-call cascade resolver.

    Resolution order:
        1. per-call override (highest)
        2. workflow override
        3. tenant override
        4. Toggle.default_value (lowest)

    Locked tenant overrides cannot be replaced by lower scopes.
    """

    def __init__(self, session: Session, *, cache_ttl_s: int = 60):
        self._session = session
        self._cache_ttl_s = cache_ttl_s
        self._cache: dict = {}

    def resolve(self, toggle_id: str, *, tenant_id: str,
                workflow_id: str | None = None,
                call_overrides: dict[str, Any] | None = None) -> Any:
        """Return the resolved value for a single toggle."""
        ...

    def resolve_many(self, toggle_ids: list[str], *, tenant_id: str,
                     workflow_id: str | None = None,
                     call_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """Resolve multiple toggles in one query — preferred for hot paths."""
        ...

    def invalidate(self, *, tenant_id: str | None = None,
                   workflow_id: str | None = None,
                   toggle_id: str | None = None) -> None:
        """Cache invalidation hook called from override-write code paths."""
        ...
```

**Cache:** in-process LRU per tenant + workflow combination, 60-second TTL.
Invalidation triggered on every override write (V-07 mutation endpoint
calls `invalidate()` synchronously before responding).

**Per-toggle merge strategy:** declared on the `Toggle` row.
- `REPLACE` — per-call value entirely replaces lower scope
- `MERGE` — per-component merge for OBJECT toggles (e.g. `epm_thresholds.rich_black_recipe`)
- `UNION` — set-union for arrays (e.g. `ai_features`)

## API surface

**Engine FastAPI routes** (`packages/engine/src/lintpdf/api/routes/toggles.py`, NEW):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/toggles` | GET | List registry (paginated; filter by category) |
| `/v1/toggles/{id}` | GET | Single toggle metadata |
| `/v1/toggles/resolve` | GET | Resolve a single toggle for current tenant + workflow |
| `/v1/tenant/toggles/{id}` | PUT | Set tenant override |
| `/v1/tenant/toggles/{id}` | DELETE | Remove tenant override (revert to default) |
| `/v1/workflows` | GET / POST | List / create workflows |
| `/v1/workflows/{id}` | GET / PATCH / DELETE | Single workflow CRUD |
| `/v1/workflows/{id}/toggles/{toggle_id}` | PUT / DELETE | Workflow override |

Per-call overrides go in the request body `overrides{}` map on existing job
endpoints; resolved by the same `ConfigResolver` per-request.

**App tRPC mirror** (`packages/app/server/routers/toggle.ts` + `workflow.ts`,
NEW): identical surface, called from dashboard UI. Same DB tables.

**Desktop:** consumes the REST API via existing HTTP client; no Tauri-side
config storage for new toggles. Desktop's existing `AppConfig` (folders,
api_key, base_url) remains unchanged.

## Toggle ID conventions (per Phase 1 Q4 approved)

**Dot-notation:**
- `checks.F-22` (single check enable/disable)
- `checks.F-22.severity_override`
- `checks.F-22.threshold_override.min_pt`
- `profiles.PDF/X-4`
- `categories.fonts`
- `tiers.T5`
- `viewer_layers.tac_heatmap`
- `viewer_layers.findings.errors`
- `epm_module.core`
- `epm_module.advanced`
- `epm_module.ai_explain`
- `epm_thresholds.rich_black_recipe` (OBJECT, MERGE strategy)
- `epm_thresholds.tac_limit_coated_pct`
- `epm_thresholds.llm_cost_cap_monthly_usd`
- `webhooks.preflight.decided`
- `webhooks.epm.scored`

Hierarchical queries supported: `GET /v1/toggles?category=epm_thresholds`
returns all `epm_thresholds.*` toggles.

## Locked toggles (per Phase 1 Q4 approved: tenant-only)

Tenant marks an override `locked: true`. Workflow + per-call values are
ignored for that toggle. Used for compliance-mandated checks (e.g., a pharma
tenant locking BR-05 Braille decode at `enabled: true`).

Locking semantics: only the **TENANT** scope's `locked` field is honored.
A workflow cannot lock a toggle. v2.1 may revisit if real-world demand
surfaces.

## Workflow inheritance (per Phase 1 Q4 approved: NO)

Workflow inherits from tenant only. There is no `parent_workflow_id` for
workflow-from-workflow inheritance in v2.0. Each workflow's overrides are
flat additions on top of tenant defaults.

## Migration path

Existing `Tenant.settings` JSON is **NOT** changed by V-07 alone. V-12
(legacy migration script) reads `Tenant.settings` and materializes it into
typed `ToggleOverride` rows. V-07 ships the resolver + new tables; V-12
ships the data migration. They land separately for rollback safety.

## Test plan

**Engine:**
- `tests/tenants/test_config_resolver.py` — resolver unit tests covering
  cascade, locked, merge strategies, cache invalidation, missing toggle defaults
- `tests/api/test_toggles_api.py` — endpoint integration tests with httpx

**App:**
- `e2e/api/toggles.spec.ts` — Playwright E2E for tenant + workflow CRUD via tRPC
- Vitest units for tRPC routers

**Coverage target:** 90%+ on resolver code path (it's hot path; bugs ship
broken cascade for every job).

## Open design questions for operator (per playbook §2.1)

All 4 prior open questions resolved by Phase 1 Q4 approval. New ones:

1. **Cache TTL:** 60s default. Acceptable, or shorter (10s) for faster
   propagation of admin config edits? Recommend 60s; admins rarely need
   sub-minute propagation.
2. **Workflow `slug` uniqueness:** unique per tenant (e.g. each tenant can
   have one "default" workflow). Confirm.
3. **Toggle deprecation:** `deprecated_at` field exists; what happens to
   existing overrides on deprecated toggles? Recommend: surface a warning
   in `/v1/toggles/{id}` response; auto-clean during V-12 migration of next
   release.
4. **Per-call `overrides{}` field shape:** flat dict `{"checks.F-22": "off"}`
   vs nested `{"checks": {"F-22": "off"}}`. Recommend **flat** for parser
   simplicity; consumers can render hierarchically if desired.

## Read-only / no-stub confirmation

- ✓ No PDF mutation (config layer only)
- ✓ No `TODO`/`FIXME`/`stub`/`mock`/placeholder in production code
- ✓ All tests pass before commit
- ✓ Prisma migrations are additive; no `--accept-data-loss`
- ✓ Engine reads via SQLAlchemy ORM mapping the same tables Prisma owns
- ✓ Desktop is HTTP client; no Tauri-side schema migration needed
