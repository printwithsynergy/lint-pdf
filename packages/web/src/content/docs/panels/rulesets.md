---
title: "Rulesets"
description: "Pick a built-in profile or clone + customise your own."
section: "panels"
order: 13
---

# Rulesets

**Path:** `/dashboard/rulesets` · **Who:** Owner / Admin

A *ruleset* is a bundle of individual checks with thresholds + severities. A *profile* is a ruleset + metadata (conformance target, workflow). This panel is where you pick or author profiles for your tenant.

## What you see

- **System profiles** section — read-only built-ins: `lintpdf-default`, `press-ready`, `pdfx-4`, `packaging-standard`. Click any → inspection view shows which checks, thresholds, and severities it contains.
- **Your profiles** section — profiles this tenant owns. Clone, edit, archive.
- **Create profile** button → start from scratch or clone a system profile.

## Actions

| Action | API | Notes |
|---|---|---|
| Clone a system profile | `POST /api/v1/profiles` with `clone_from` | Fastest way to customise — pick the nearest system profile, tweak thresholds. |
| Edit check thresholds | `PATCH /api/v1/profiles/{id}` | Visual editor groups checks by category. |
| Archive | `PATCH /api/v1/profiles/{id}` with `archived=true` | Archived profiles stay referenceable by jobs already using them; new submissions with the ID return 404. |
| Export | `GET /api/v1/profiles/{id}?format=json` | Download the full profile definition as JSON for git-friendly version control. |

## Gotchas

- **Custom profiles are identified by UUID**, not name. Collisions aren't possible, but your team needs a labelling discipline (`press-check-v3`, `customer-nordic-std`) so you know which is which.
- **Severity changes are immediate** — a profile edit takes effect on the next submission using that profile. There's no "draft" mode.
- **Archived profiles can't be unarchived** via the UI. Clone it to a new profile if you need to un-archive.

## Related

- [Preflight modes](../preflight-modes) — detect vs. interpret
- [Checks reference](../checks) — every individual check you can tune
