# Phase 0.7 — Workflow + WorkflowConfig design

**Branch:** `claude/phase-0.7-workflow-model`
**Status:** Draft for sign-off
**Decisions referenced:** Q-E1, Q-E2, Q-E3, Q-E4, Q-E5, Q-E6, Q-E7, Q-W1, Q-W2, Q-W3 (see `audit/decisions.md`)
**Read-only invariant:** every table below stores configuration metadata only. lintPDF still inspects, never mutates input PDFs.

## 1. Goals

1. **Replace the 5 legacy config layers** (Profile, BrandSpec, ApprovalChainTemplate, CustomEndpoint, TenantImportMapping) with one unified `Workflow` + `ConfigOverride` model so every per-tenant knob cascades through a single resolver. (Q-E1)
2. **Per-field cascade with locking.** A toggle resolved at request time follows: code-defined system default → tenant override → workflow override → call override. Any scope can mark a field-path as locked, blocking lower scopes from overriding. (Q-E2, principle 12)
3. **Full audit trail.** Every config write is captured with full provenance: actor, surface, request_id, old/new value. Audit rows are durable independent of the override row's mutation history. (Q-E3, §16.5)
4. **Per-job replay.** Every job submission persists a `ResolvedConfigSnapshot` with the merged payload + per-field provenance, so "what config drove this PDF's findings on date X" is always answerable even after the workflow has been edited. (Q-W2)
5. **Single category registry.** EPM thresholds (rich-black recipe, TAC limits, ΔE/ΔC ceilings) and per-tenant LLM cost cap are first-class categories alongside profile/brand/approval/import-mapping/endpoint-defaults/response-format/viewer-capabilities. No siloed config tables. (Q-E6, Q-E7, §16.4)
6. **Desktop-friendly substrate.** Server is canonical; desktop reads the resolved snapshot and writes overrides offline; reconcile-on-reconnect uses a monotonic `server_revision` per workflow. (Q-E4)
7. **No legacy debt.** Wave V V-12 migration script collapses the 5 legacy tables into the new model **and drops them in the same alembic transaction**. No `*_legacy_archived` tables. (Q-W3, Q-E5, §16.7)

## 2. Out of scope

- **ApprovalChain / ApprovalStep runtime tables** stay as-is. Only `ApprovalChainTemplate` folds into `ConfigOverride(category='approval_template')`. The chain instance + step decision tables are runtime workflow execution state, not config.
- **CustomProfile JSON evolution.** The internal shape of the rule pack (checks/thresholds/AI/color/report) is unchanged; we only move where it lives. Pydantic schemas are reused.
- **System profile seeding.** SystemProfile rows (admin-curated bundled profiles) become `ConfigOverride(scope='system_default', category='profile_rules')` rows but their selection / visibility logic is unchanged in this PR; admin UI stays.
- **Job runtime fields.** `Job.profile_id`, `Job.brand_spec_id`, `Job.endpoint_id` columns stay (they're identifiers, not config) — but their *values* now reference Workflow IDs / snapshot IDs instead of CustomEndpoint / BrandSpec / CustomProfile IDs.
- **Authentication / API key model.** Untouched.
- **Pricing tier gating.** Stays in entitlements layer; not folded into ConfigOverride.
- **Phase 5 docs sweep.** Defer to release boundary per Q-G1; this PR ships its own ApiReferencePage + markdown docs additions but no full audit.

## 3. Schema

All tables live in the **engine** schema (SQLAlchemy + Alembic). Prisma sees these tables only as foreign references on `Job` (already-existing rows like `Job.workflow_id`); the app talks to engine over HTTP for all CRUD.

### 3.1 `workflows`

The named container that replaces `custom_endpoints` 1:1.

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` PK | |
| `tenant_id` | `UUID` FK → `tenants.id` | NOT NULL, cascade |
| `slug` | `TEXT` | unique per tenant |
| `name` | `TEXT` | display name |
| `description` | `TEXT` | nullable |
| `is_default` | `BOOLEAN` | partial-unique: only one true per tenant |
| `is_active` | `BOOLEAN` | soft-delete via false |
| `response_mode` | `TEXT` | CHECK `('async','sync')` — carried over from CustomEndpoint |
| `server_revision` | `BIGINT` | monotonic counter; bumped on every config write that targets this workflow. Used by desktop reconcile (Q-E4). |
| `created_at` | `TIMESTAMPTZ` | |
| `updated_at` | `TIMESTAMPTZ` | |
| `created_by_user_id` | `UUID` | nullable; null when seeded from migration |

Indexes:
- `(tenant_id, slug)` UNIQUE
- `(tenant_id, is_default)` PARTIAL UNIQUE WHERE `is_default = true AND is_active = true`
- `(tenant_id, is_active)` for list queries

### 3.2 `config_overrides`

The cascade primitive. One row per `(scope, tenant_id, workflow_id?, call_id?, category, field_path)` tuple.

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` PK | |
| `scope` | `TEXT` | CHECK `('tenant','workflow','call')` — system defaults are code-defined, not stored |
| `tenant_id` | `UUID` FK → `tenants.id` | NOT NULL |
| `workflow_id` | `UUID` FK → `workflows.id` | NULL when scope='tenant'; NOT NULL when scope='workflow' or 'call' |
| `call_id` | `UUID` FK → `jobs.id` | NULL except scope='call' |
| `category` | `TEXT` | CHECK enum (see §3.4) |
| `field_path` | `TEXT` | dotted path within category payload; `''` (empty) = whole category |
| `value_json` | `JSONB` | the override value; for `field_path=''` this is the full category shape |
| `is_locked` | `BOOLEAN` | only meaningful at tenant or workflow scope |
| `created_at` | `TIMESTAMPTZ` | |
| `updated_at` | `TIMESTAMPTZ` | |
| `last_set_by_user_id` | `UUID` | nullable |
| `last_set_by_api_key_id` | `UUID` | nullable |

Constraints:
- CHECK: `(scope='tenant' AND workflow_id IS NULL AND call_id IS NULL) OR (scope='workflow' AND workflow_id IS NOT NULL AND call_id IS NULL) OR (scope='call' AND workflow_id IS NOT NULL AND call_id IS NOT NULL)`
- UNIQUE `(scope, tenant_id, workflow_id, call_id, category, field_path)` — only one override per scope+path

Indexes:
- `(tenant_id, scope, category)` for resolver fast-path
- `(workflow_id, category)` for "all overrides on this workflow"
- `(call_id)` for "all overrides on this job"

### 3.3 `resolved_config_snapshots`

One row per Job, written at submit time (Q-W2 every-job snapshot).

| Column | Type | Notes |
|---|---|---|
| `job_id` | `UUID` PK FK → `jobs.id` | one-to-one |
| `workflow_id` | `UUID` FK → `workflows.id` | nullable (direct submission with no workflow ref) |
| `tenant_id` | `UUID` FK → `tenants.id` | NOT NULL — denormalized for filtering |
| `resolved_payload` | `JSONB` | full merged config that drove the job |
| `provenance` | `JSONB` | `{field_path: 'system'\|'tenant'\|'workflow'\|'call'}` per field |
| `system_default_version` | `TEXT` | code version of system defaults at snapshot time |
| `created_at` | `TIMESTAMPTZ` | |

Indexes:
- `(tenant_id, created_at DESC)` for tenant audit dashboards
- `(workflow_id, created_at DESC)` for workflow history

### 3.4 Categories

Stored as `category` text with CHECK enum. Each has a Pydantic model in `lintpdf.config.categories`:

| Category | Pydantic model | Replaces / contains |
|---|---|---|
| `profile_rules` | `ProfileRulesPayload` | CustomProfile.preflight_profile_json + SystemProfile.preflight_profile_json |
| `brand` | `BrandPayload` | BrandSpec (colors[], rich_black_spec, customer_name) |
| `approval_template` | `ApprovalTemplatePayload` | ApprovalChainTemplate (steps[], default flag) |
| `import_mapping` | `ImportMappingPayload` | TenantImportMapping (config, sample_payload, format, name) |
| `endpoint_defaults` | `EndpointDefaultsPayload` | CustomEndpoint.profile_id + default_brand_spec_id |
| `epm_thresholds` | `EpmThresholdsPayload` | rich-black recipe defaults (Q-E6), TAC limits, ΔE/ΔC ceilings |
| `ai_cost_cap` | `AiCostCapPayload` | per-tenant LLM cost cap (Q-E7); off-by-default + opt-in |
| `response_format` | `ResponseFormatPayload` | sync vs async, webhook hooks, immediate-render flags |
| `viewer_capabilities` | `ViewerCapabilitiesPayload` | enable_*, data_capabilities, toolbar/branding knobs |

### 3.5 `config_audit`

Append-only audit log (Q-E3). Every config write generates one row.

| Column | Type | Notes |
|---|---|---|
| `id` | `BIGSERIAL` PK | |
| `tenant_id` | `UUID` | NOT NULL |
| `workflow_id` | `UUID` | nullable |
| `call_id` | `UUID` | nullable |
| `category` | `TEXT` | |
| `field_path` | `TEXT` | |
| `old_value_json` | `JSONB` | null on create |
| `new_value_json` | `JSONB` | null on delete |
| `operation` | `TEXT` | CHECK `('set','unset','lock','unlock')` |
| `actor_user_id` | `UUID` | nullable |
| `actor_api_key_id` | `UUID` | nullable |
| `surface` | `TEXT` | CHECK `('dashboard','plugin','sdk','api','desktop','system','migration')` |
| `request_id` | `TEXT` | correlation id |
| `created_at` | `TIMESTAMPTZ` | NOT NULL DEFAULT now() |

Indexes:
- `(tenant_id, created_at DESC)`
- `(workflow_id, created_at DESC)`
- `(category, created_at DESC)`

### 3.6 What stays untouched

- `jobs` table: keeps `endpoint_id` column **renamed to `workflow_id`** (FK redirected from `custom_endpoints.id` to `workflows.id`); `brand_spec_id` and `profile_id` columns are dropped (replaced by snapshot lookup).
- `approval_chains` + `approval_steps`: runtime tables, untouched. Only the FK `template_id` is updated to point at a `config_overrides.id` (with category='approval_template') — or simpler, dropped, since the snapshot covers replay.
- `system_profiles`: dropped; rows fold into `config_overrides(scope='tenant', category='profile_rules')` for each tenant in the visibility list.
- `system_profiles` admin-side metadata (visibility_mode, min_plan, source) → stored on a sibling `config_override_metadata` row keyed by override id, OR (simpler) folded into the `value_json` payload. Decision: fold into payload; simpler.

## 4. Resolver cascade

### 4.1 Read path

```python
def resolve_config(
    tenant_id: UUID,
    workflow_id: UUID | None,
    call_overrides: dict | None,
    *,
    db: Session,
) -> ResolvedConfig:
    """
    Returns a fully merged ResolvedConfig with per-field provenance.
    Pure function modulo db reads; no writes.
    """
    # 1. Start from code-defined system defaults (Pydantic models with defaults)
    merged = SystemDefaults.copy()
    provenance = {path: 'system' for path in merged.flat_paths()}

    # 2. Tenant scope: load all config_overrides where scope='tenant' AND tenant_id=...
    tenant_overrides = db.query(ConfigOverride).filter_by(
        scope='tenant', tenant_id=tenant_id
    ).all()
    for o in tenant_overrides:
        merged.set_path(o.category, o.field_path, o.value_json)
        provenance[f"{o.category}.{o.field_path}"] = 'tenant'
        if o.is_locked:
            merged.lock_path(o.category, o.field_path)

    # 3. Workflow scope (if workflow_id provided)
    if workflow_id is not None:
        wf_overrides = db.query(ConfigOverride).filter_by(
            scope='workflow', workflow_id=workflow_id
        ).all()
        for o in wf_overrides:
            if merged.is_locked(o.category, o.field_path):
                # Tenant-locked; workflow override silently dropped
                # (or raise — see §10 risks)
                continue
            merged.set_path(o.category, o.field_path, o.value_json)
            provenance[f"{o.category}.{o.field_path}"] = 'workflow'
            if o.is_locked:
                merged.lock_path(o.category, o.field_path)

    # 4. Call scope (request body, not DB)
    if call_overrides:
        for category, payload in call_overrides.items():
            for field_path, value in flatten(payload):
                if merged.is_locked(category, field_path):
                    raise LockedFieldError(category, field_path)
                merged.set_path(category, field_path, value)
                provenance[f"{category}.{field_path}"] = 'call'

    return ResolvedConfig(payload=merged, provenance=provenance)
```

Three knobs to pin down:

- **Locked-field violation by workflow scope is silently dropped** vs. raised. Default: **silently drop with a logged warning** (workflows can't be expected to know what tenant has locked). Per-call locked-field violation is **always raised** (the request submitter actively asked for the override).
- **Caching**: tenant + workflow overrides are tenant-scoped read-mostly; cache via Redis (key = `(tenant_id, workflow_id, system_default_version)`, TTL 60s, invalidated on any audit write). Skipped in v1; add when read latency hurts.
- **System default version**: bumped manually in code on every system-default change; persisted on snapshot for replay.

### 4.2 Write path

Every API mutation that modifies config must:

1. Open transaction
2. Read the existing `ConfigOverride` row (for old_value capture)
3. UPSERT the new value
4. Insert `ConfigAudit` row with `(old_value, new_value, actor, surface, request_id)` from `Request.state` (FastAPI dep)
5. Bump `workflows.server_revision` if scope='workflow'
6. Commit

Audit insertion is in the same transaction as the override write — never decoupled. If the audit insert fails, the override is rolled back.

### 4.3 Snapshot path (per-job)

At job submit, after `resolve_config`:

```python
snapshot = ResolvedConfigSnapshot(
    job_id=job.id,
    workflow_id=workflow_id,
    tenant_id=tenant_id,
    resolved_payload=resolved.payload.dict(),
    provenance=resolved.provenance,
    system_default_version=SystemDefaults.VERSION,
)
db.add(snapshot); db.commit()
```

Read replays for audit-dashboards / "as-of" queries use the snapshot, not the live override state.

## 5. Migration script (Q-E5, Q-W3) — drop in same transaction

**Critical constraint (Quincy 2026-04-26): if we drop the legacy tables in this migration, every UI / API / plugin / SDK / E2E reference must be updated in the same PR.** No follow-up. The migration and the consumer rewrites land together, gate each other in CI, and a single Railway deploy flips the world.

### 5.1 Alembic migration ordering

`packages/engine/alembic/versions/050_workflow_unified_config.py`:

```
def upgrade():
    # PHASE A — create new structures (idempotent; no data risk)
    op.create_table('workflows', ...)
    op.create_table('config_overrides', ...)
    op.create_table('resolved_config_snapshots', ...)
    op.create_table('config_audit', ...)

    # PHASE B — pre-flight validation (raise on any unexpected legacy state)
    _assert_legacy_invariants()
    # e.g., every CustomEndpoint.profile_id resolves to a real CustomProfile or system profile;
    # every BrandSpec.tenant_id matches a real tenant; etc.
    # If any assertion fails, the migration aborts and Postgres rolls back.

    # PHASE C — copy data into new tables
    _migrate_custom_endpoints_to_workflows()
    _migrate_custom_profiles_to_overrides()      # scope='tenant', category='profile_rules'
    _migrate_system_profiles_to_overrides()      # scope='tenant', category='profile_rules' (per visible tenant)
    _migrate_brand_specs_to_overrides()          # scope='tenant' for is_default, scope='workflow' for endpoint-pinned
    _migrate_approval_templates_to_overrides()   # scope='tenant' for is_default
    _migrate_tenant_import_mappings_to_overrides()  # scope='tenant'

    # PHASE D — post-migration validation (counts must match; resolver must reproduce legacy behavior)
    _assert_row_counts_match()
    _assert_resolver_replay_matches_legacy(sample_size=200)

    # PHASE E — backfill resolved snapshots for in-flight + recent jobs (90d window)
    _backfill_recent_snapshots(window_days=90)

    # PHASE F — redirect FK on jobs (rename endpoint_id -> workflow_id, drop brand_spec_id, drop profile_id)
    op.alter_column('jobs', 'endpoint_id', new_column_name='workflow_id')
    op.drop_column('jobs', 'brand_spec_id')
    op.drop_column('jobs', 'profile_id')

    # PHASE G — drop legacy tables (atomic with everything above)
    op.drop_table('approval_chain_templates')
    op.drop_table('tenant_import_mappings')
    op.drop_table('brand_specs')
    op.drop_table('custom_endpoints')
    op.drop_table('custom_profiles')
    op.drop_table('system_profiles')

def downgrade():
    raise RuntimeError(
        "050_workflow_unified_config: irreversible. Restore from Railway "
        "volume snapshot taken pre-deploy."
    )
```

Postgres wraps `upgrade()` in a single transaction by default. Any abort in Phases B/C/D rolls back everything — including the table drops in G — leaving the database identical to its pre-migration state.

### 5.2 Pre-deploy operator checklist (one-time)

The migration is irreversible by design (per Q-W3). To make that safe:

1. **Railway volume snapshot** of the Postgres data directory immediately before deploy. Recorded in `audit/deploy-log.md` with snapshot id + timestamp.
2. **Maintenance window** declared on status page (estimated 2–4 minutes).
3. **App + Engine + Worker scaled to zero** during the migration window so no in-flight requests hit a half-migrated schema.
4. **Run on staging first.** The PR's `railway preview` deploy must succeed end-to-end against a copy of production data before merge. (See §9.)

### 5.3 Migration row mapping (detailed)

#### `custom_endpoints` → `workflows`

```sql
INSERT INTO workflows (id, tenant_id, slug, name, description, is_default, is_active, response_mode, server_revision, created_at, updated_at)
SELECT id, tenant_id, slug,
       COALESCE(slug, 'workflow') AS name,
       description,
       FALSE AS is_default,
       is_active,
       response_mode,
       1 AS server_revision,
       created_at,
       NOW() AS updated_at
FROM custom_endpoints;
```

Then for each tenant: pick one workflow to mark `is_default = TRUE` (the most-recently-used by job count).

#### `custom_endpoints.profile_id` + `default_brand_spec_id` → `config_overrides(category='endpoint_defaults')`

Two rows per workflow:
- `(scope='workflow', category='endpoint_defaults', field_path='profile_id', value_json='"<id>"')`
- `(scope='workflow', category='endpoint_defaults', field_path='default_brand_spec_id', value_json='"<uuid>"')` — IF non-null

#### `custom_profiles` → `config_overrides(scope='tenant', category='profile_rules', field_path='')`

One row per CustomProfile, value_json = full preflight_profile_json. Profile_id (the string identifier like "pdf_x1a") becomes the workflow's `endpoint_defaults.profile_id`. Multiple custom profiles per tenant → multiple `config_overrides` rows distinguished by `field_path = profile_id`.

Wait — that breaks the cascade model since profile_rules is normally a single rule pack. Re-design: **CustomProfile rows fold into `config_overrides(scope='tenant', category='profile_rules', field_path=<profile_id>)`** and the resolver picks the right pack based on the workflow's `endpoint_defaults.profile_id`. Same handling for system_profiles.

This means `category='profile_rules'` is special — it's a *registry* keyed by `field_path`, not a single value. Updated category description in §3.4: **profile_rules** stores `{<profile_id>: PreflightProfile}`.

#### `system_profiles` → `config_overrides(scope='tenant', category='profile_rules', field_path=<profile_id>)`

For each system profile + each visible tenant (per visibility_mode + min_plan + visible_tenant_ids), insert one row per (tenant, profile). Visibility metadata (admin id, source, bundled_version) folded into value_json under reserved key `_meta`.

#### `brand_specs` → `config_overrides(category='brand', field_path=<spec_id_str>)`

Each BrandSpec becomes one row. `is_default=true` → `scope='tenant'`. Endpoint-pinned (i.e., referenced by some `custom_endpoints.default_brand_spec_id`) → `scope='workflow'` rows for each pinning workflow.

#### `approval_chain_templates` → `config_overrides(scope='tenant', category='approval_template', field_path=<template_id>)`

One row per template. `is_default=true` template stored at `field_path=''` (the default; resolver picks this when no per-call template_id provided).

#### `tenant_import_mappings` → `config_overrides(scope='tenant', category='import_mapping', field_path=<mapping_name>)`

One row per mapping; mapping.name is the field_path key.

### 5.4 Snapshot backfill (Phase E)

For every job in the last 90 days:

```python
for job in db.query(Job).filter(Job.created_at > now() - timedelta(days=90)):
    resolved = resolve_config(
        tenant_id=job.tenant_id,
        workflow_id=job.workflow_id,
        call_overrides=None,
        db=db,
    )
    db.add(ResolvedConfigSnapshot(
        job_id=job.id,
        workflow_id=job.workflow_id,
        tenant_id=job.tenant_id,
        resolved_payload=resolved.payload.dict(),
        provenance=resolved.provenance,
        system_default_version=SystemDefaults.VERSION,
    ))
```

This is best-effort: backfill snapshots reflect the CURRENT resolved config, not the config at the time the job ran (we have no pre-migration audit log). Older jobs (>90d) have no snapshot; their UI shows "Config snapshot not available — pre-migration job".

## 6. Consumer surface inventory — every reference that must be updated in this PR

Per Quincy 2026-04-26: dropping the legacy tables is only safe if every consumer is rewritten in the same PR. This is the inventory.

### 6.1 Engine (Python)

| File | Current behavior | New behavior |
|---|---|---|
| `packages/engine/src/lintpdf/api/models.py` (CustomProfile, SystemProfile, BrandSpec, CustomEndpoint, ApprovalChainTemplate, TenantImportMapping models, lines 499–1257) | SQLAlchemy declarations | **Delete** these declarations. Add `Workflow`, `ConfigOverride`, `ResolvedConfigSnapshot`, `ConfigAudit`. |
| `packages/engine/src/lintpdf/api/routes/profiles.py` | CRUD for CustomProfile + SystemProfile via 4 endpoints | Rewrite to read/write `config_overrides(category='profile_rules')`. Same external URL paths preserved (`GET/POST/DELETE /api/v1/profiles`). |
| `packages/engine/src/lintpdf/api/routes/brand_specs.py` | CRUD for BrandSpec | Rewrite to `config_overrides(category='brand')`. URLs preserved. |
| `packages/engine/src/lintpdf/api/routes/approvals.py` | Templates + chains + step decisions | Templates → `config_overrides(category='approval_template')`. Chains/steps untouched. URLs preserved. |
| `packages/engine/src/lintpdf/api/routes/endpoints.py` | CRUD for CustomEndpoint + submit-via-endpoint | Rewrite to `workflows` table; `endpoint_defaults` overrides. URLs preserved. |
| `packages/engine/src/lintpdf/api/routes/import_mappings.py` | CRUD for TenantImportMapping | Rewrite to `config_overrides(category='import_mapping')`. URLs preserved. |
| `packages/engine/src/lintpdf/queue/tasks.py:600+` (preflight_job) | Loads profile JSON, resolves brand spec | Calls `resolve_config()` once at job start; reads `resolved_config_snapshots.resolved_payload`. |
| `packages/engine/src/lintpdf/queue/tasks.py:2176+` (parse_external_preflight_report) | Loads TenantImportMapping by id | Reads `config_overrides(category='import_mapping')`. |
| `packages/engine/src/lintpdf/profiles/resolver.py` | Visibility / lookup helpers for system + custom profiles | Rewrite as thin wrappers over the new resolver. |
| `packages/engine/src/lintpdf/brand_specs/resolver.py` | `resolve_brand_spec_for_job()` cascade | Rewrite as thin wrapper or delete; cascade is handled by central resolver. |
| `packages/engine/src/lintpdf/imports/custom.py` (CustomMappingParser) | Reads mapping.config dict | Untouched; receives the same dict shape from the new override row. |
| `packages/engine/src/lintpdf/api/schemas.py` (Pydantic request/response) | EndpointCreate, BrandSpecCreate, etc. | Add new ResolvedConfig + Workflow schemas; keep response shapes for existing endpoints stable. |
| Pydantic models in `lintpdf.config.categories` (NEW module) | — | Define `ProfileRulesPayload`, `BrandPayload`, `ApprovalTemplatePayload`, `ImportMappingPayload`, `EndpointDefaultsPayload`, `EpmThresholdsPayload`, `AiCostCapPayload`, `ResponseFormatPayload`, `ViewerCapabilitiesPayload`. |
| `packages/engine/tests/api/test_profiles.py` + `test_profiles_routes.py` + `test_brand_specs.py` + `test_branding_defaults.py` + `test_endpoints_response_mode.py` + `test_import_mappings.py` | Cover legacy CRUD | **Update assertions** to match new internals; external API shape unchanged where possible. |

### 6.2 App (TypeScript / Next.js)

| File | Current | New |
|---|---|---|
| `packages/app/app/dashboard/brand-specs/page.tsx` + `layout.tsx` | List/CRUD UI calling proxied engine routes | UI unchanged externally; the routes it calls now resolve from `config_overrides` server-side. Update tRPC type imports if shapes change. |
| `packages/app/app/dashboard/endpoints/page.tsx` + `layout.tsx` | Endpoint list / management | Rename to `dashboard/workflows/...` AND add a redirect from `/dashboard/endpoints` for old bookmarks. Update copy from "endpoint" to "workflow". |
| `packages/app/app/dashboard/approvals/page.tsx` | Templates + active chains | Templates UI unchanged in shape; backend swap is invisible. |
| `packages/app/app/dashboard/import-mappings/page.tsx` (if it exists) | CRUD UI | Same. |
| `packages/app/app/dashboard/preflight/page.tsx` | Profile selection in submit form | Replace profile dropdown with workflow picker; profile selection moves under workflow scope. |
| `packages/app/app/api/lintpdf/[...path]/route.ts` (proxy) | Forwards to engine | Untouched if engine URLs are preserved. |
| `packages/app/app/approve/[token]/page.tsx` | Approver decision page | Untouched (consumes approval_chains/steps which are unchanged). |
| `packages/app/e2e/api/profiles.spec.ts`, `branding.spec.ts`, `endpoints.spec.ts`, `approvals.spec.ts`, `import-mappings.spec.ts` | E2E coverage | **Update setup fixtures** to insert into new tables; assertions on response shape kept where possible. |
| Type imports from `@thinkneverland/lintpdf-types` if present | Shared schemas | Regenerate from engine OpenAPI. |

### 6.3 Plugin (Fairy Ring)

| File | Current | New |
|---|---|---|
| `packages/plugin/src/routes/profiles.ts` | GET /profiles | Forward to engine; same URL. Update integration test fixtures. |
| `packages/plugin/src/plugins/endpoints/index.ts` | Endpoint management routes | Rename to `workflows`; add deprecated `endpoints` route shim that redirects callers (one-release deprecation window). |
| `packages/plugin/src/routes/approvals.ts` | Approval routes | Untouched. |
| `packages/plugin/src/__tests__/routes.test.ts` | Profile fixture tests | Update fixtures. |

### 6.4 SDK (Python — packages/sdk-python/)

The SDK is a thin HTTP client. Affected:

- Any `Client.create_endpoint(...)` / `Client.update_endpoint(...)` methods → renamed to `create_workflow` / `update_workflow`. Old methods kept as deprecated shims that emit `DeprecationWarning` for one minor version.
- Type stubs regenerated from engine OpenAPI.
- README + examples updated.

### 6.5 Marketing site (`packages/web/`)

Per Q-G1 (defer Phase 5 to release boundary), this PR ships the bare minimum:

- `packages/web/src/content/docs/workflows.md` — new doc page (replaces / merges `endpoints.md`)
- `packages/web/src/lib/doc-sections.ts` — register new slug
- `packages/web/src/components/docs/pages/ApiReferencePage.tsx` (and section components under `api/`) — updated to describe Workflow + ConfigOverride API. Add deprecation banner on the old "Endpoints" section pointing to the new "Workflows".
- `docs/examples/` — new sample for `POST /workflows`.

Full doc audit is the release-boundary Phase 5 sweep.

## 7. Breaking-change posture

We're keeping public API URLs and JSON response shapes stable wherever possible. But the migration breaks two surfaces in irreducible ways:

1. **Renamed dashboard route**: `/dashboard/endpoints` → `/dashboard/workflows`. Old URL serves a redirect (not a 404) so user bookmarks still work.
2. **SDK method rename**: `Client.create_endpoint` → `Client.create_workflow` etc. Deprecated shims for one minor version.

Internal API routes (engine `/api/v1/*`) stay at the same URLs. Response field names that referenced "endpoint" (e.g., `endpoint_id` on Job responses) are renamed to `workflow_id`; callers that destructure those names break. **This is the most risky breaking change** and needs:

- Release-notes callout
- Deprecation banner in dashboard for one full week before merge
- Engine response includes BOTH old + new keys for one release (e.g., emit `workflow_id` as the canonical and `endpoint_id` as a deprecated alias) — coordinated with the SDK.

## 8. Test plan

### 8.1 Unit (engine pytest)

- `tests/config/test_resolver.py` — system → tenant → workflow → call cascade; locked-field semantics at every scope; locked at tenant blocks workflow override (silent); locked at workflow blocks call override (raises).
- `tests/config/test_categories.py` — Pydantic model parsing for every category; round-trip JSON.
- `tests/config/test_audit.py` — every CRUD path emits exactly one `config_audit` row; rollback drops the audit too.
- `tests/config/test_snapshot.py` — snapshot is written on job submit; replay-from-snapshot reproduces resolved payload byte-for-byte.

### 8.2 Migration

- `tests/migrations/test_050_workflow_unified_config.py` — alembic upgrade against a synthetic dataset covering every legacy table; assert row counts + sample resolves match.
- `tests/migrations/test_050_invariants.py` — pre-flight assertions catch corrupted legacy state (orphan FKs, missing tenants).
- Run alembic upgrade against a snapshot of production data in a Railway preview environment; manual sign-off before main merge.

### 8.3 Integration (engine + Postgres)

- `tests/integration/test_workflow_crud.py` — full Workflow + override lifecycle.
- `tests/integration/test_locked_toggle.py` — pharma BR-05 scenario: tenant locks `epm_thresholds.tac_limit_coated`, workflow tries to override → silently ignored; per-call tries → 422.

### 8.4 E2E (Playwright via packages/app)

- `e2e/api/workflows.spec.ts` — replaces `endpoints.spec.ts` (kept as smoke shim that hits the redirect).
- `e2e/api/profiles.spec.ts`, `branding.spec.ts`, `import-mappings.spec.ts` — updated.
- New: `e2e/api/locked-toggles.spec.ts` — UI lock/unlock workflow.

### 8.5 Plugin (Vitest)

- `packages/plugin/src/__tests__/workflows.test.ts` — new test for the renamed plugin routes.
- `packages/plugin/src/__tests__/routes.test.ts` — updated profile fixtures.

## 9. Rollout

### 9.1 PR sequencing

This is one mega-PR. The branches and reviews cascade as:

1. Open the draft PR with the design doc + alembic migration only (no consumer changes yet) for **schema review**.
2. After schema review, push consumer changes in logical commits: engine first, app second, plugin/SDK third, docs fourth, e2e last.
3. Run the **full CI** matrix (engine pytest, app typecheck/build/E2E, plugin Vitest, web build).
4. Merge requires green CI + approval from a human reviewer.

### 9.2 Deploy-day runbook

- Maintenance window declared 24h ahead.
- Pre-deploy: Railway volume snapshot of Postgres data dir; logged with id + timestamp.
- App + Engine + Worker scaled to zero.
- `railway up` triggers alembic upgrade.
- Smoke tests run (single submit-and-resolve flow) against the upgraded engine.
- Scale services back up.
- Monitor `config_audit` row rate for 1h; abnormally high indicates a hot-loop bug.

### 9.3 Rollback

The migration's `downgrade()` raises `RuntimeError`. Rollback path is **Railway volume snapshot restore** of the Postgres data dir. Documented in `audit/deploy-log.md`. RTO ≈ 10–20 minutes. Acceptable for an off-hours maintenance window.

## 10. Open risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Migration data loss from edge-case row | Medium | High | Pre-flight invariants in Phase B; row-count match in Phase D; sample-resolve replay; Railway volume snapshot. |
| Consumer rewrite misses a caller | High | Medium | The §6 inventory; CI typecheck on engine + app; integration tests; deprecated shims for SDK + plugin. |
| Per-field cascade resolver is too slow on hot path | Low | Medium | First-pass: no cache; benchmark before merge. If P50 > 5ms add Redis cache (60s TTL invalidated on audit write). |
| Locked-field semantics confuse users | Medium | Low | Dashboard UI shows lock-icon + "locked by: tenant admin" tooltip; per-call API returns 422 with locked_path in error body so SDK can hint. |
| Snapshot table growth | Medium | Low | ~5KB × N jobs/day; estimated <1GB/year for current scale. Add partitioning (monthly) when table > 50M rows. |
| Old-key/new-key dual emission of `endpoint_id` + `workflow_id` confuses caller code | Low | Medium | Single release window only; deprecation warning header; release notes. |
| Pre-migration audit history is empty | High | Low | Documented limitation: snapshot backfill captures CURRENT config, not config-as-of-job-time, for jobs older than the migration. |
| Alembic transaction times out on large tenant | Low | High | Run `EXPLAIN` on the migration queries; if any tenant has > 100k legacy rows, batch the inserts within Phase C. |

---

## 11. Decision sign-off

This design needs explicit Quincy approval on:

- §3 schema: column types, indexes, CHECK constraints
- §4 resolver: silent-drop vs raise semantics for tenant-locked + workflow override
- §5 migration: same-transaction drop is correct (Q-W3 confirmed) — restate assent
- §6 consumer inventory: complete? anything missing?
- §7 breaking-change posture: dashboard route rename + SDK rename ok?

Once approved, work proceeds in commit order: alembic migration → SQLAlchemy models + resolver → engine routes → app dashboard → plugin → SDK → docs → E2E. Draft PR opens after the alembic migration commit so reviewers can shape the schema before consumers are rewritten on top of it.
