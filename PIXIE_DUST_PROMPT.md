# Pixie Dust Framework — Feature Request Prompt

## Context

After building LintPDF (a PDF preflight SaaS) on Pixie Dust, we've identified a clear set of **generic multi-tenant SaaS patterns** that every downstream Pixie Dust app will need. These are currently implemented as custom code in LintPDF but contain zero domain-specific logic — they're pure platform features.

Pixie Dust already provides excellent infrastructure: auth (magic links, sessions), multi-tenancy (User, Tenant, TenantUser, TenantInvite), plugin system (Fairy Ring), tRPC, middleware, Stripe integration, email, and theming. But it stops short of providing the **page-level components and plugin modules** that every SaaS dashboard needs.

The result: every downstream app reimplements the same team management, billing UI, API key CRUD, webhook management, admin pages, and login page from scratch. This is the next natural evolution of the framework.

---

## Tier 1: Page Components (export from pixie-dust-dashboard)

These should be mountable React components that accept branding/config props and work with existing Pixie Dust models.

### 1.1 LoginPage Component

**What we built custom:** A magic link login page with email input, 6-digit code verification, polling-based session detection, plan-aware redirects.

**What Pixie Dust should export:**
```tsx
import { LoginPage } from "@thinkneverland/pixie-dust-dashboard";

// In (auth)/login/page.tsx:
export default function Login() {
  return <LoginPage />;
}
```

**Props/Config:**
- Automatically uses `getBranding()` for logo, colors, heading, subheading
- Accepts optional `onSuccess` redirect URL
- Handles magic link flow internally (requestMagicLink → poll → claim session)
- Shows 6-digit code input as alternative
- Supports `plan` query param for post-auth plan selection
- Dark mode support

**Models used:** User, Session, MagicLink (all already in pixie-dust-database)

### 1.2 TeamPage Component

**What we built custom:** Member listing with role badges, role update dropdowns, remove member, invite form (email + role), pending invites list with revoke.

**What Pixie Dust should export:**
```tsx
import { TeamPage } from "@thinkneverland/pixie-dust-dashboard";

// In dashboard/team/page.tsx:
export default function Team() {
  return <TeamPage />;
}
```

**Props/Config:**
- Configurable role definitions (default: VIEWER, MEMBER, ADMIN, OWNER)
- Optional custom roles via Fairy Ring plugin `addRole()`
- Invite expiration duration (default 7 days)
- Optional `onInviteSent` callback for custom email
- Permission gating: `team:view` for listing, `team:manage` for mutations

**Models used:** TenantUser, TenantInvite, User (all already in pixie-dust-database)

### 1.3 BillingPage Component

**What we built custom:** Plan comparison cards with feature lists, current subscription display, invoice history table, checkout button → Stripe, manage subscription → Stripe portal.

**What Pixie Dust should export:**
```tsx
import { BillingPage } from "@thinkneverland/pixie-dust-dashboard";

// In dashboard/billing/page.tsx:
export default function Billing() {
  return <BillingPage plans={PLAN_DEFINITIONS} />;
}
```

**Props/Config:**
- `plans` array: `{ id, name, price, interval, features: string[], stripePriceId }`
- Uses pixie-dust-stripe-kit internally for checkout/portal/invoices
- Shows current plan, next billing date, cancel status
- Invoice history with PDF download links
- Free tier handling (no subscription = free plan)

**Models used:** StripeCustomer, Subscription, Payment (already in stripe schema)

### 1.4 AccountPage Component

**What we built custom:** Organization name/slug editor, branding settings (logo URL, primary/accent colors), tenant settings form.

**What Pixie Dust should export:**
```tsx
import { AccountPage } from "@thinkneverland/pixie-dust-dashboard";

// In dashboard/account/page.tsx:
export default function Account() {
  return <AccountPage showBranding={entitlements.whitelabel_enabled} />;
}
```

**Props/Config:**
- Organization info section (name, slug, domain)
- Branding section (conditionally shown based on entitlements)
- Uses AppSettings model for branding fields
- Optional custom sections via render props

**Models used:** Tenant, AppSettings (already in pixie-dust-database)

### 1.5 ProfilePage Component

**What we built custom:** User name, email display, avatar URL editor.

**What Pixie Dust should export:**
```tsx
import { ProfilePage } from "@thinkneverland/pixie-dust-dashboard";
```

**Models used:** User (already in pixie-dust-database)

---

## Tier 2: Plugin Modules (export from new packages or pixie-dust-fairy-ring)

These are Fairy Ring plugins that register routes, permissions, nav items, and pages. They handle the backend logic that page components need.

### 2.1 pixie-dust-admin (NEW PACKAGE)

**What we built custom:** Super admin dashboard with tenant listing, user management, system health, audit log viewer, impersonation toolbar, admin provisioning.

**What Pixie Dust should export:**
```ts
import { adminPlugin } from "@thinkneverland/pixie-dust-admin";

// In plugins.ts:
loader.register(adminPlugin);
```

**Features:**
- **Tenant management page** — list all tenants, search, filter by status (ACTIVE/SUSPENDED/ARCHIVED), update plan/status
- **User management page** — list all users, search, promote/demote super admin
- **Audit log viewer** — paginated, filterable by action/entity/user/tenant, date range
- **System health page** — database connection status, queue stats, storage status
- **Impersonation toolbar** — "Assist Customer" dropdown, yellow banner showing active impersonation, stop button
- **Admin provisioning** — auto-create house tenant with unlimited entitlements on first super admin login

**Permissions:** `site-admin:access` (SUPER_ADMIN only)

**Pages registered:**
- `/dashboard/admin` — hub
- `/dashboard/admin/tenants` — tenant list
- `/dashboard/admin/users` — user list
- `/dashboard/admin/audit-logs` — audit log viewer
- `/dashboard/admin/health` — system health

**Models used:** User, Tenant, TenantUser, AuditLog, Session (all existing)

### 2.2 pixie-dust-api-keys (NEW PACKAGE or part of fairy-ring)

**What we built custom:** API key generation, listing, revocation with masked key display and last-used tracking.

**What Pixie Dust should export:**
```ts
import { apiKeysPlugin } from "@thinkneverland/pixie-dust-api-keys";

loader.register(apiKeysPlugin);
```

**Features:**
- Create API key with label → returns full key once, then only prefix
- List keys with prefix, label, created_at, last_used_at
- Revoke/delete keys
- Key validation middleware for API routes

**New Prisma model (add to pixie-dust-database):**
```prisma
model ApiKey {
  id          String   @id @default(cuid())
  tenantId    String
  label       String
  keyHash     String   @unique
  keyPrefix   String   // First 8 chars for display
  isActive    Boolean  @default(true)
  lastUsedAt  DateTime?
  createdAt   DateTime @default(now())

  @@index([tenantId])
  @@index([keyHash])
}
```

**Permission:** `api-keys:manage` (ADMIN, OWNER)

**Page registered:** `/dashboard/api-keys`

### 2.3 pixie-dust-webhooks (NEW PACKAGE or part of fairy-ring)

**What we built custom:** Webhook endpoint CRUD, HMAC signature verification, test payload delivery, event filtering.

**What Pixie Dust should export:**
```ts
import { webhooksPlugin } from "@thinkneverland/pixie-dust-webhooks";

loader.register(webhooksPlugin({
  eventTypes: ["job.completed", "job.failed", "invoice.paid"],
}));
```

**Features:**
- Create webhook endpoint with URL, secret, event filter
- List/update/delete endpoints
- Send test payload
- HMAC-SHA256 signature verification helper
- Delivery logging with retry

**New Prisma model:**
```prisma
model WebhookEndpoint {
  id        String   @id @default(cuid())
  tenantId  String
  url       String
  secret    String
  events    Json     // string[] of event types
  isActive  Boolean  @default(true)
  createdAt DateTime @default(now())

  @@index([tenantId])
}

model WebhookDelivery {
  id           String   @id @default(cuid())
  endpointId   String
  event        String
  payload      Json
  statusCode   Int?
  responseBody String?
  deliveredAt  DateTime @default(now())

  @@index([endpointId, deliveredAt])
}
```

**Permission:** `webhooks:manage` (ADMIN, OWNER)

**Page registered:** `/dashboard/webhooks`

### 2.4 pixie-dust-usage (NEW PACKAGE)

**What we built custom:** Usage metering dashboard showing current period consumption, limits, overage costs.

**What Pixie Dust should export:**
```ts
import { usagePlugin } from "@thinkneverland/pixie-dust-usage";

loader.register(usagePlugin({
  metrics: [
    { key: "api_calls", label: "API Calls", unit: "calls" },
    { key: "storage_gb", label: "Storage", unit: "GB" },
  ],
  getUsage: async (tenantId) => fetchFromEngine(tenantId),
}));
```

**Features:**
- Usage bar chart (used / limit)
- Overage indicator with cost
- Period reset countdown
- Configurable metrics (not hardcoded to "jobs")

**Permission:** `usage:view` (all roles)

**Page registered:** `/dashboard/usage`

---

## Tier 3: UI Component Library (export from pixie-dust-ui)

pixie-dust-ui exists but LintPDF doesn't use it — every page is inline Tailwind. The component library should be compelling enough that downstream apps actually import it.

### 3.1 Core Components Needed

```tsx
// Data display
import { DataTable, Badge, StatCard, EmptyState } from "@thinkneverland/pixie-dust-ui";

// Forms
import { Form, FormField, Input, Select, Textarea, Switch, ColorPicker } from "@thinkneverland/pixie-dust-ui";

// Feedback
import { Toast, Alert, ConfirmDialog, Skeleton } from "@thinkneverland/pixie-dust-ui";

// Layout
import { PageHeader, PageContent, Card, Tabs, SplitPane } from "@thinkneverland/pixie-dust-ui";
```

### 3.2 Composite Components

```tsx
// Ready-made patterns
import {
  MemberListItem,     // Avatar + name + role badge + actions
  InviteForm,         // Email + role selector + send button
  PlanCard,           // Plan name + price + features + CTA
  InvoiceTable,       // Date + amount + status + PDF link
  ApiKeyRow,          // Prefix + label + last used + revoke
  WebhookEndpointRow, // URL + events + status + test button
  UsageBar,           // Progress bar with limit + overage
  AuditLogEntry,      // Timestamp + user + action + entity
} from "@thinkneverland/pixie-dust-ui";
```

### 3.3 Loading Skeletons

```tsx
import {
  SkeletonTable,
  SkeletonCard,
  SkeletonForm,
  SkeletonDashboard,
  SkeletonPageHeader,
} from "@thinkneverland/pixie-dust-ui";
```

---

## Tier 4: Framework Enhancements (pixie-dust-core / pixie-dust-auth)

### 4.1 Entitlements System

**What we built custom:** Hardcoded entitlements per plan (rate limits, file size, webhook count, whitelabel, AI features).

**What Pixie Dust should provide:**
```ts
import { defineEntitlements, resolveEntitlements } from "@thinkneverland/pixie-dust-core";

const entitlements = defineEntitlements({
  free: { api_calls: 100, storage_gb: 1, webhooks: 0, whitelabel: false },
  starter: { api_calls: 1000, storage_gb: 10, webhooks: 5, whitelabel: false },
  growth: { api_calls: 10000, storage_gb: 100, webhooks: 20, whitelabel: true },
  enterprise: { api_calls: Infinity, storage_gb: Infinity, webhooks: 100, whitelabel: true },
});

// In any route:
const limits = resolveEntitlements(tenant);
if (limits.api_calls <= currentUsage) throw new Error("Rate limit exceeded");
```

### 4.2 Impersonation Support (Built-in to pixie-dust-auth)

**What we built custom:** Session-based impersonation with `impersonatingTenantId` on Session model, audit logging, toolbar UI.

**What Pixie Dust should provide:**
```ts
import { startImpersonation, stopImpersonation, getImpersonationState } from "@thinkneverland/pixie-dust-auth";
import { ImpersonationToolbar } from "@thinkneverland/pixie-dust-dashboard";
```

- `Session.impersonatingTenantId` already exists — just needs helper functions
- Toolbar component that shows "Assisting: {tenant name}" banner
- Automatic audit logging

### 4.3 Public Link Sharing with Email Gate

**What we built custom:** Token-based public URLs, email collection form, view tracking.

**What Pixie Dust should provide:**
```ts
import { publicLinkPlugin } from "@thinkneverland/pixie-dust-core";

// Register public link support for any resource type
loader.register(publicLinkPlugin({
  resourceType: "report",
  emailGate: { configurable: true, default: "tenant" },
  tracking: true,
}));
```

**New Prisma model:**
```prisma
model PublicLink {
  id          String   @id @default(cuid())
  tenantId    String
  resourceType String  // "report", "document", etc.
  resourceId  String
  token       String   @unique
  expiresAt   DateTime?
  requireEmail Boolean @default(false)
  createdAt   DateTime @default(now())

  @@index([token])
  @@index([tenantId])
}

model LinkView {
  id          String   @id @default(cuid())
  linkId      String
  viewerEmail String?
  viewerName  String?
  ipAddress   String?
  viewedAt    DateTime @default(now())

  @@index([linkId])
}
```

### 4.4 Branding Profiles System

**What we built custom:** BrandProfile model with custom/default/none types, CRUD API, resolution hierarchy.

**What Pixie Dust should provide:**
- Extend AppSettings with profile support
- Three modes: Custom branding, Platform default, Blind (no branding)
- Resolution: per-call > per-resource > tenant default > platform default
- `getBranding(context)` already exists — just needs profile awareness

---

## Tier 5: Developer Experience

### 5.1 CLI Scaffolding

```bash
npx pixie-dust init my-saas
# Creates:
# - Next.js 15 app with Pixie Dust pre-configured
# - Login page (using LoginPage component)
# - Dashboard with team, billing, account, api-keys, webhooks pages
# - Plugin bootstrap with stripe-kit
# - Prisma schema with all models
# - startup.sh with safe migration pattern
# - Dockerfile with pixie-dust-aware build
# - railway.toml
```

### 5.2 Plugin Generator

```bash
npx pixie-dust generate plugin my-feature
# Creates:
# - src/plugins/my-feature/index.ts (Fairy Ring plugin skeleton)
# - src/routes/my-feature.ts (route definitions)
# - app/dashboard/my-feature/page.tsx (page skeleton)
```

### 5.3 Schema Sync Helper

```bash
npx pixie-dust schema-sync
# - Detects new columns needed by current pixie-dust version
# - Generates ALTER TABLE statements
# - Updates startup.sh automatically
# - Runs prisma db push safely
```

---

## Priority Order

1. **LoginPage** — every app needs this, currently rebuilt from scratch each time
2. **TeamPage** — standard multi-tenant feature, zero domain logic
3. **BillingPage** — stripe-kit exists but has no UI, every app rebuilds billing pages
4. **Admin plugin** — tenant/user management, impersonation, audit logs
5. **API Keys plugin** — standard SaaS pattern, currently proxied to engine unnecessarily
6. **Webhooks plugin** — standard event delivery, every integration-heavy SaaS needs this
7. **UI component library** — make pixie-dust-ui compelling enough to actually use
8. **Entitlements system** — plan-based feature gating is universal
9. **Usage metering** — consumption dashboards are needed by every metered SaaS
10. **Public link sharing** — token-based sharing with email gate is common

---

## What Should NOT Be in Pixie Dust

These are correctly domain-specific and should remain in downstream apps:

- PDF viewer, separations, annotations, TAC heatmaps
- Preflight job submission/listing/detail pages
- Rulesets/profile management
- Engine-specific report generation
- AI feature configuration
- Color/gamut configuration
- Domain-specific usage metrics (jobs, pages, file sizes)
- Custom preflight check definitions
