---
title: "Admin dashboard overview"
description: "What the admin index page is for and how to navigate."
---

# Admin dashboard overview

**Path:** `/dashboard/admin` · **Who:** Super admin only · **Scope:** Cross-tenant

The landing page for every super-admin task. Entry-point cards link out to each feature area below. Nothing here is reachable by regular tenant users — the `/dashboard/admin/` layout redirects non-super-admins to `/dashboard` before rendering.

## What you see

A responsive grid of feature cards, each a link to one admin panel:

- All tenants → [Tenants panel](./tenants)
- All jobs → [Jobs panel](./jobs)
- Preflight audit → [Audit panel](./audit)
- Trial submissions → [Trials panel](./trials)
- System health → [Health panel](./health)
- Webhook dead letters → [Webhooks panel](./webhooks)

## Actions

None directly — this page only contains navigation. Actions live in each linked panel.

## Gotchas

- Super-admin status is checked on every request via the layout's session + `User.isSuperAdmin` lookup, so revoking the flag takes effect on the next page load.
- Impersonation: super admins can impersonate a tenant via the Tenants panel; when active, the header in the rest of the dashboard shows the impersonated tenant name with a banner to exit.

## Related

- [Admin APIs + Swagger](../admin-api)
