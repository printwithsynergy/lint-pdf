# Pixie Dust Migration Audit — LintPDF

## Summary

| # | Feature | Verdict | Effort | Notes |
|---|---------|---------|--------|-------|
| 1 | Login / magic-link | MIGRATE + EXTEND | Medium | Auth logic uses pixie-dust-auth. UI custom. Keep plan-redirect. |
| 2 | Team management | MIGRATE | Low | 100% generic. Prisma TenantUser/TenantInvite. |
| 3 | Billing / subscription | MIGRATE + EXTEND | Medium | Uses stripe-kit. Keep engine plan sync as extension. |
| 4 | User profile | MIGRATE | Low | Minimal page. No domain logic. |
| 5 | Workspace / org settings | KEEP STANDALONE | — | Proxies to engine for tenant config. |
| 6 | Admin branding/appearance | MIGRATE | Low | Pure AppSettings CRUD. Already wired. |
| 7 | Account-level settings | KEEP STANDALONE | — | Engine-specific config (AI, color, entitlements). |
| 8 | Super-admin panel | MIGRATE + EXTEND | High | Generic tenant/user list + engine-specific health/jobs. |
| 9 | API key management | KEEP STANDALONE | — | Keys in engine DB. All routes proxy. |
| 10 | Webhook system | KEEP STANDALONE | — | Webhooks in engine DB. Routes proxy. |
| 11 | Usage metering | KEEP STANDALONE | — | Engine SDK. Domain-specific metrics. |
| 12 | Data tables | SKIP — PREMATURE | — | pixie-dust-ui doesn't export DataTable yet. |
| 13 | Status/role badges | SKIP — PREMATURE | — | pixie-dust-ui doesn't export Badge yet. |
| 14 | Stat cards | SKIP — PREMATURE | — | No generic stat card needed. |
| 15 | Empty states | SKIP — PREMATURE | — | Simple text. No component needed. |
| 16 | Form primitives | SKIP — PREMATURE | — | All inline Tailwind. pixie-dust-ui has no form exports. |
| 17 | Loading skeletons | MIGRATE | Low | components/skeleton.tsx is 100% generic. |
| 18 | Toast/notification | SKIP — NOT NEEDED | — | No toast system. Inline text works. |
| 19 | Confirmation dialogs | SKIP — PREMATURE | — | Browser confirm(). Functional. |
| 20 | Composite components | SKIP — PREMATURE | — | Per-page. Not enough reuse yet. |
| 21 | Entitlements/gating | SKIP — PREMATURE | — | Engine-managed. Pixie Dust has no entitlements system. |
| 22 | Impersonation | MIGRATE + EXTEND | Medium | Generic session impersonation + audit logging. |
| 23 | Public link sharing | KEEP STANDALONE | — | Coupled to PDF viewer + engine tokens. |
| 24 | Branding profiles | MIGRATE + EXTEND | Medium | Platform AppSettings generic. Tenant BrandProfile engine-specific. |
| 25 | Project init | SKIP — PREMATURE | — | No scaffolding in either project. |
| 26 | Plugin generation | SKIP — PREMATURE | — | Manual creation works. |
| 27 | Schema sync | KEEP STANDALONE | — | startup.sh handles dual-DB. Unique to LintPDF. |

## Status

All MIGRATE items are **blocked on Pixie Dust shipping the corresponding features** (TeamPage, ProfilePage, BillingPage, pixie-dust-admin, etc.). The LintPDF codebase is already prepared:

- Admin branding/appearance routes wired into site-admin plugin via Prisma AppSettings
- Login page refactored to use dynamic branding from AppSettings via `/api/auth/branding`
- Profile PATCH handler added to `/api/auth/me`
- Auth logic fully delegated to pixie-dust-auth functions

When Pixie Dust publishes these components, migration is a swap-import operation for most items.

## What Should NOT Migrate

- PDF viewer (tiles, separations, TAC heatmaps, annotations)
- Preflight jobs, rulesets, reports
- Engine proxy routes (API keys, webhooks, usage, account settings)
- AI/color configuration
- Engine-side models and Alembic migrations
- startup.sh schema sync (dual-DB specific)
