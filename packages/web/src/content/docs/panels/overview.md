---
title: "Dashboard overview"
description: "What every screen in the LintPDF dashboard does."
section: "panels"
order: 1
---

# Dashboard overview

**Path:** `/dashboard` · **Who:** Any signed-in tenant user

The landing page after you log in. Shows recent jobs, the current billing period's usage, and quick-action cards into the most-used panels.

## What you see

- **Recent jobs** — last 10 preflights, newest first, with status badge and a one-click open-report link.
- **Usage summary** — jobs run this period, AI credits consumed, file-pack balance remaining.
- **Quick actions** — cards linking to the five panels most users visit daily: Preflight a file, API keys, Webhooks, Billing, Usage.

## Actions

| Action | What it does |
|---|---|
| Open job | Links out to the job's hosted report (new tab). Expires with the tenant's share-link policy. |
| Run a preflight | Shortcut to [`/dashboard/preflight`](./preflight) for a browser-upload preflight. |
| View all jobs | Opens the Reports panel filtered to every job, not just your own. |

## Gotchas

- Usage numbers are cached for ~30s. If you just ran a big batch, they'll lag briefly.
- "Recent jobs" shows jobs across the *whole tenant*, not just your own. If you want just yours, filter in Reports.

## Related

- [Reports](./reports) — searchable list of every job
- [Preflight](./preflight) — upload + run a single file
