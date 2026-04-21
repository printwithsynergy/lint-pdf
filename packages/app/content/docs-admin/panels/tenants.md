---
title: "Tenants panel"
description: "Browse, inspect, and modify every tenant in the system."
---

# Tenants

**Path:** `/dashboard/admin/tenants` · **Who:** Super admin · **Scope:** Cross-tenant

The canonical list of every tenant the engine knows about. Use this when you need to look up a customer by name, check their plan, mint an API key, or start impersonating them.

## What you see

- Paginated table: name, plan, creation date, whitelabel status, is-active flag.
- Per-row **Inspect** button → detail drawer with contact email, API keys, brand profiles, custom domains, and the impersonate toggle.

## Actions

| Action | API | Notes |
|---|---|---|
| Search by name | client-side filter on loaded page | Server-side search isn't implemented yet — if the tenant list grows past a few hundred we'll need to paginate by query. |
| Create tenant | `POST /api/v1/admin/tenants` | Use sparingly; almost all tenants self-register via `/auth/signup`. |
| Update plan | `POST /api/v1/admin/tenants/{id}/plan` | Flips `plan`, `overage_enabled`, `overage_cap_cents`. Updates take effect immediately; existing jobs are not retro-billed. |
| Mint API key | `POST /api/v1/admin/tenants/{id}/keys` | Returns the raw key exactly once — copy it to the customer or secrets vault before navigating away. |
| Start impersonation | Tenant-user session flag (`Session.impersonatingTenantId`) | See the gotcha below. |

## Gotchas

- **Impersonation is session-scoped.** While impersonating, every request the super-admin makes uses the target tenant's `tenantId` — API keys, job submissions, webhook deliveries all appear to originate from that tenant. The header shows a prominent banner. End impersonation from the same banner or by logging out.
- **API-key minting is write-once.** The engine stores the hash, not the raw key; if the customer loses it, generate a new one.
- **Plan downgrades** don't retro-adjust existing metered packages (AI credits, file packs). Those stay valid for their original 12-month window.

## Related

- [Billing panel](./billing) — override monthly AI credits + file quotas for a specific tenant.
- [Custom domains panel](./custom-domains) — verify + approve whitelabel domain requests.
