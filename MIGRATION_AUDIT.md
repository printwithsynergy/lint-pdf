# Pixie Dust Migration Audit — LintPDF (Updated from Source)

## Critical Finding

**Pixie Dust has already shipped almost everything LintPDF built custom.** The previous audit was based on inferring exports from lockfile metadata. After inspecting the actual source at `thinkneverland/pixie-dust`, we found that Pixie Dust v1.5+ provides pre-built page components, plugins, UI components, and framework helpers for nearly every generic SaaS feature LintPDF implements from scratch.

---

## Updated Summary Table

| # | Feature | Verdict | Effort | Pixie Dust Has | LintPDF Has Custom |
|---|---------|---------|--------|----------------|-------------------|
| **Tier 1 — Pages** | | | | | |
| 1 | Login page | **MIGRATE** | Low | `LoginPage` from pixie-dust-dashboard v1.7.0 | Custom auth/login/page.tsx |
| 2 | Team management | **MIGRATE** | Low | `TeamPage` from pixie-dust-dashboard v1.7.0 | Custom plugins/team + dashboard/team |
| 3 | Billing / plans | **MIGRATE + EXTEND** | Medium | `BillingPage` from pixie-dust-boilerplate v1.2.0 + `PricingCard/Grid` | Custom dashboard/billing + @lintpdf/stripe |
| 4 | User profile | **MIGRATE** | Low | `ProfilePage` from pixie-dust-dashboard v1.7.0 + `updateProfile()` from auth | Custom dashboard/profile + PATCH /api/auth/me |
| 5 | Workspace settings | **MIGRATE + EXTEND** | Medium | `WorkspaceSettingsPage` from pixie-dust-dashboard v1.7.0 | Custom dashboard/account (proxies to engine) |
| 6 | Admin branding | **MIGRATE** | Low | `BrandingPage` + `BrandingForm` from pixie-dust-dashboard v1.7.0 | Custom admin/branding + site-admin plugin |
| 7 | Admin appearance | **MIGRATE** | Low | `AppearancePage` + `AppearanceForm` from pixie-dust-dashboard v1.7.0 | Custom admin/appearance + site-admin plugin |
| **Tier 2 — Plugins** | | | | | |
| 8 | Super-admin panel | **MIGRATE + EXTEND** | Medium | `AdminDashboardPage`, `TenantsPage`, `UsersPage`, `AuditLogPage` from dashboard | Custom super-admin + site-admin plugins |
| 9 | API key management | **MIGRATE** | Low | `apiKeysPlugin` + `ApiKeysPage` from pixie-dust-api-keys v1.0.0 + Prisma `ApiKey` model | Custom plugins/api-keys (proxies to engine) |
| 10 | Webhook system | **MIGRATE** | Low | `webhooksPlugin` + `WebhooksPage` from pixie-dust-webhooks v1.0.0 + Prisma `Webhook` model | Custom plugins/webhooks (proxies to engine) |
| 11 | Usage metering | **MIGRATE + EXTEND** | Medium | `usagePlugin` + `UsagePage` from pixie-dust-usage v1.0.0 + Prisma `UsageMetric` model | Custom plugins/usage (engine SDK) |
| **Tier 3 — UI** | | | | | |
| 12 | Data tables | **MIGRATE** | Low | `DataTable` from pixie-dust-ui v1.1.0 | Custom HTML tables per page |
| 13 | Badges | **MIGRATE** | Low | `Badge` from pixie-dust-ui v1.1.0 | Inline Tailwind spans |
| 14 | Stat cards | **MIGRATE** | Low | `StatCard` from pixie-dust-ui v1.1.0 | Custom link cards in admin |
| 15 | Empty states | **MIGRATE** | Low | `EmptyState` from pixie-dust-ui v1.1.0 | Inline text paragraphs |
| 16 | Form primitives | SKIP — NOT NEEDED | — | Not exported individually | Inline Tailwind inputs |
| 17 | Loading skeletons | **MIGRATE** | Low | `Skeleton`, `SkeletonText`, `SkeletonCard` from pixie-dust-ui v1.1.0 | Custom components/skeleton.tsx |
| 18 | Toast/notification | **MIGRATE** | Low | `ToastProvider` + `useToast` from pixie-dust-ui v1.1.0 | None (inline success text) |
| 19 | Confirm dialogs | **MIGRATE** | Low | `ConfirmDialog` from pixie-dust-ui v1.1.0 | Browser confirm() |
| 20 | Composite components | SKIP — PREMATURE | — | Not yet | Per-page custom |
| **Tier 4 — Framework** | | | | | |
| 21 | Entitlements | **MIGRATE** | Medium | `defineEntitlements()`, `checkEntitlement()` from pixie-dust-auth v1.5.0 | Hardcoded UNLIMITED_ENTITLEMENTS in super-admin |
| 22 | Impersonation | **MIGRATE** | Low | `startImpersonation()`, `resolveEffectiveUser()` from pixie-dust-auth v1.5.0 | Custom impersonate/route.ts + toolbar |
| 23 | Public link sharing | KEEP STANDALONE | — | Not in Pixie Dust | Custom /view/[token] + viewer |
| 24 | Branding profiles | **MIGRATE + EXTEND** | Medium | `getBrandingProfile()` from pixie-dust-auth v1.5.0 | Custom BrandProfile engine model + routes |
| **Tier 5 — DX** | | | | | |
| 25 | Project init | SKIP | — | Reference app exists but no CLI | N/A |
| 26 | Plugin generation | SKIP | — | Not yet | N/A |
| 27 | Schema sync | **MIGRATE** | Low | `checkSchemaHealth()` from pixie-dust-database v1.4.0 | Custom startup.sh |

---

## What Changed from Previous Audit

The previous audit marked most items as "SKIP — PREMATURE" because we assumed Pixie Dust didn't have them. **It does.** Key discoveries:

1. **pixie-dust-dashboard v1.7.0** exports 11 pre-built page components: `LoginPage`, `TeamPage`, `ProfilePage`, `AccountPage`, `BrandingPage`, `AppearancePage`, `TenantsPage`, `UsersPage`, `AuditLogPage`, `AdminDashboardPage`, `WorkspaceSettingsPage`

2. **pixie-dust-ui v1.1.0** exports 7 components: `Badge`, `DataTable`, `EmptyState`, `StatCard`, `Skeleton/SkeletonText/SkeletonCard`, `ToastProvider/useToast`, `ConfirmDialog`

3. **pixie-dust-auth v1.5.0** adds: `updateProfile()`, `startImpersonation()`, `resolveEffectiveUser()`, `defineEntitlements()`, `checkEntitlement()`, `getBrandingProfile()`

4. **pixie-dust-database v1.4.0** adds Prisma schemas for: `ApiKey`, `Webhook`, `WebhookEvent`, `WebhookDelivery`, `UsageMetric`, `UsageAlert`

5. **Three new plugins** exist: `pixie-dust-api-keys`, `pixie-dust-webhooks`, `pixie-dust-usage` — each with page component + Fairy Ring plugin

6. **pixie-dust-boilerplate v1.2.0** has `BillingPage`, `PricingCard`, `PricingGrid`, `SubscriptionBadge`, `BillingOverview`

---

## Migration Priority

### Immediate (swap imports, delete custom code):

1. **LoginPage** — Replace `auth/login/page.tsx` (318 lines) with `<LoginPage />` from dashboard
2. **TeamPage** — Replace `dashboard/team/page.tsx` + `plugins/team/` with `<TeamPage />` + `teamPlugin` concept
3. **ProfilePage** — Replace `dashboard/profile/page.tsx` with `<ProfilePage />` + use `updateProfile()` from auth
4. **BrandingPage + AppearancePage** — Replace `admin/branding` + `admin/appearance` with dashboard components
5. **ApiKeysPage** — Replace `dashboard/api-keys` + `plugins/api-keys/` with `apiKeysPlugin` from pixie-dust-api-keys
6. **WebhooksPage** — Replace `dashboard/webhooks` + `plugins/webhooks/` with `webhooksPlugin` from pixie-dust-webhooks
7. **UI components** — Import `Badge`, `DataTable`, `EmptyState`, `StatCard`, `Skeleton`, `ToastProvider`, `ConfirmDialog` from pixie-dust-ui
8. **Impersonation** — Use `startImpersonation()` + `resolveEffectiveUser()` from auth instead of custom route

### Medium-term (needs engine integration hooks):

9. **BillingPage** — Use boilerplate's `BillingPage` but keep `syncPlanToEngine()` as Fairy Ring hook
10. **UsagePage** — Use usage plugin but provide engine-specific metric fetcher
11. **Entitlements** — Use `defineEntitlements()` from auth but map to engine entitlements
12. **WorkspaceSettingsPage** — Use dashboard component but add engine proxy extensions
13. **AdminDashboardPage + TenantsPage + UsersPage + AuditLogPage** — Use dashboard components but keep engine health/jobs as extensions

### Keep standalone:

14. **Public link viewer** (`/view/[token]`) — PDF viewer specific
15. **Engine proxy routes** (jobs, profiles, viewer, color-config, ai-config) — Domain specific
16. **startup.sh** — Dual-DB migration specific (though `checkSchemaHealth()` can supplement it)

---

## API Key & Webhook Migration Note

API keys and webhooks currently live in the **engine database** (SQLAlchemy). Pixie Dust now provides Prisma models (`ApiKey`, `Webhook`, `WebhookDelivery`) in pixie-dust-database. Two options:

**Option A:** Migrate key/webhook storage from engine to Prisma. Requires engine auth middleware changes.
**Option B:** Use Pixie Dust plugins for UI but keep engine as storage backend via proxy. Simpler but less integrated.

Recommend **Option B** initially — use the page components but proxy to engine for data.

---

## Estimated Impact

If all MIGRATE items are implemented:
- **~2,500 lines of custom code deleted** (login, team, profile, billing, admin pages, api-keys, webhooks, UI components)
- **11 custom page files replaced** with single-line imports
- **6 custom plugin files simplified** or removed
- **1 custom component file deleted** (skeleton.tsx)
- **Better consistency** with Pixie Dust theming and branding system
