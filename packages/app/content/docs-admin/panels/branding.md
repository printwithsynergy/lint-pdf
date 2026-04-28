---
title: "Branding panel (admin)"
description: "Cross-tenant brand profile viewer + default-picker."
---

# Branding (admin)

**Path:** `/dashboard/admin/branding` · **Who:** Super admin · **Scope:** Cross-tenant

Inspect every tenant's brand profiles and see which one is flagged as their default. Use this when a customer says "my reports are branded wrong" and you need to confirm which profile is active.

## What you see

- Tenant picker.
- Table of brand profiles for the selected tenant: profile name, type (custom / lintpdf / none), primary color swatch, logo URL, default flag.
- Per-row **Inspect** → drawer with the full resolved report URL under that profile.

## Actions

| Action | API | Notes |
|---|---|---|
| Open profile | `GET /api/v1/tenants/{id}/brand-profiles/{profile_id}` | Uses the cached read path with 5-min TTL. |
| Set default | `PATCH /api/v1/tenants/{id}/default-brand-profile` | Immediate — no cache invalidation needed because the `tenants.default_brand_profile_id` column isn't cached. |
| Inspect logo | Links to `logo_url` | 302-redirects to R2-backed storage. |

## Gotchas

- Editing brand profile *content* happens in the customer's own dashboard at `/dashboard/profile`. This panel is read-mostly for admins — only the default-picker is here.
- The Redis brand-profile cache is invalidated explicitly on every `PATCH`, so you don't need to bump anything manually.

## Related

- [Custom domains panel](./custom-domains) — domain verification for whitelabel profiles.
