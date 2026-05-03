# Residual SaaS-shaped modules in the OSS engine

Audit catalog produced after the W6c-7 cluster (Tenant + ApiKey
extraction) and W7 (table-scope tripwire) landed. Captures the
modules that still live under `src/lintpdf/` but are exclusively or
predominantly consumed by `lintpdf_saas`. Each row is a candidate
for a future extraction PR; no code changes here.

## Methodology

- **Consumed by SaaS only**: any module whose only `from lintpdf.X
  import …` callers live in `lintpdf_saas.*` and have no engine-side
  use.
- **Mixed**: module is consumed by both engine and SaaS — needs
  Protocol seam refactor before extraction.
- **Dead**: module is unused by both — candidate for deletion.

The ground rule (post-W6c): the OSS engine package should not host
SaaS-only modules even if those modules don't import any
SaaS-coupled code themselves. Owning a Stripe client in the OSS
engine is a brand-statement leak; users cloning `lint-pdf` standalone
shouldn't see Stripe price IDs.

## Catalog

### 1. `src/lintpdf/billing/` — Stripe integration (extract)

| File | Status | Callers |
|---|---|---|
| `stripe_client.py` | **Extract** | 3 SaaS files (`api/routes/{ai_credits,file_packs,stripe_webhooks}.py`) |
| `metered_packs.py` | **Extract** | 3 SaaS files (`api/routes/{ai_credits,file_packs}.py`, `billing/allocation.py`) |
| `__init__.py` | Trivial — relocate with the package |

Both files are SaaS-only. The engine has no Stripe concept.
Relocation target: `lintpdf_saas/billing/{stripe_client,metered_packs}.py`.

### 2. `src/lintpdf/email/` — Resend-backed email service (extract)

| File | Status | Callers |
|---|---|---|
| `service.py` | **Extract** | 4 SaaS files (`api/routes/trial.py`, `approvals/service.py`); 0 OSS production callers |
| `__init__.py` | Trivial — relocate with the package |

The engine has no email-sending concept either; OSS deploys log
events via stdout. The Resend client + the prebaked HTML templates
(`send_trial_report_email`, `send_approval_request`,
`send_overage_started`, `send_api_key_issued`) are all SaaS surfaces.

Test files (`tests/test_email_service.py`,
`tests/email/test_email_service.py`) need to follow the move OR be
rewritten as OSS test stubs of `EmailService` Protocol.

### 3. `src/lintpdf/tenants/entitlements.py` — billing-tier defaults (split)

The `TenantEntitlements` dataclass is engine-shaped (it's the
abstract feature-flag bag the engine reads via the resolver). The
`PLAN_LIMITS` dict, however, is a SaaS-only mapping from
`TenantPlan` to per-tier feature defaults — the engine has no
business knowing what the "Growth" tier includes.

Split:

- Keep `TenantEntitlements`, the resolver, and `AI_FEATURE_FLAGS`
  in `lintpdf.tenants.entitlements` (engine).
- Move `PLAN_LIMITS` + plan-tier resolution to
  `lintpdf_saas.tenants.entitlements_defaults` (SaaS).
- Wire via a new `EntitlementDefaultsService` Protocol with a
  `defaults_for(plan: str) -> TenantEntitlements` method. OSS
  default returns a permissive everything-enabled bag.

### 4. `src/lintpdf/tenants/models.py` — `TenantPlan` enum (keep, but)

`TenantPlan` is a SaaS billing concept but engine code references it
in non-functional ways (string comparisons inside the entitlement
resolver). The enum can stay in OSS as a string-typed identifier;
its values are opaque to the engine.

`PLAN_LIMITS` here moves with the entitlements split (#3 above).

### 5. `src/lintpdf/audit/metering.py` (already abstracted)

The metering call sites in OSS production code already dispatch
through `MeteringService` Protocol seams (W6c-2 cluster). The OSS
default is a no-op recorder; the SaaS shell installs the
`AIUsageLog`-writing implementation. ✅ No extraction needed.

### 6. `src/lintpdf/services/*.py` (Protocol seams — correct architecture)

These are the engine-side Protocol declarations + no-op defaults.
SaaS shell installs richer implementations at boot. ✅ Stays.

## Recommended extraction order

When the user requests follow-up work, attack in this order
(smallest blast radius first):

1. **`lintpdf.email.service` → `lintpdf_saas.email.service`** — zero
   OSS production callers, only test files need updating. ~1 PR per
   side. Smallest.

2. **`lintpdf.billing.{stripe_client,metered_packs}` →
   `lintpdf_saas.billing.*`** — zero OSS callers, all 6 SaaS-side
   imports flip path. ~1 PR per side. Small.

3. **`lintpdf.tenants.entitlements` `PLAN_LIMITS` split** — adds a
   new `EntitlementDefaultsService` Protocol. Medium — touches the
   resolver + the per-route entitlement loaders. ~3 PRs (Protocol
   foundation, SaaS-side defaults impl, OSS-side cleanup).

After all three: OSS engine has zero modules whose primary
audience is SaaS. Anyone cloning `lint-pdf` standalone gets a
clean preflight engine with no Stripe / billing / email surface
area.

## Out of scope (kept in OSS)

- All `lintpdf.tenants.toggle_*` files — Phase 0.7 unified config
  substrate, used by every plugin's `ctx.config[...]` lookup.
- `lintpdf.decisions.*` — engine pre-flight decision audit trail.
- `lintpdf.webhooks.*` + `WebhookEndpoint` / `WebhookDelivery` ORMs
  — engine event-dispatch infrastructure (every preflight engine
  deploy needs to fire webhooks; not a SaaS concern).
- `lintpdf.{queue,reports,viewer,profiles,annotations,…}` — engine
  core.
