---
title: "Admin docs home"
description: "What lives here and how it's organised."
---

# Admin documentation

This area is only reachable by super-admin accounts (the `/dashboard/admin/*` layout enforces the gate). Nothing here is linked from the marketing site or the public docs.

## What's inside

- **[Admin panels](./panels)** — a page per `/dashboard/admin/*` route explaining what it does, who can use it, and which API it calls. Start here when you're trying to answer "what does this screen actually do?"
- **[Admin APIs + Swagger](./admin-api)** — one-page summary of the admin API surface and a link to the full Swagger UI at `/dashboard/admin/swagger` for interactive drill-down.
- **[Ops runbooks](./runbooks)** — procedural docs for tasks that span multiple panels or scripts (webhook replay, demo-tenant seeding, preflight verification).

## Conventions

Every panel doc follows the same skeleton: **Path · Who · Scope** header row, a short "what you see" section listing the main UI elements, an "Actions" list naming each button / form and which API it hits, and a "Gotchas" section for non-obvious behaviour.

Panel docs are deliberately short. If something needs a multi-step procedure, it becomes a runbook and the panel doc links out to it.

## Adding a new admin panel

1. Create the Next.js route under `packages/app/app/dashboard/admin/<slug>/page.tsx`.
2. Add a matching `packages/app/content/docs-admin/panels/<slug>.md` from the template above.
3. Register the slug in `packages/app/lib/admin-doc-sections.ts` so it shows up in the sidebar.

The docs route under `/dashboard/admin/docs/*` picks it up automatically — no code changes needed beyond the registry line.
