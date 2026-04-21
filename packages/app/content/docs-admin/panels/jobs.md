---
title: "Jobs panel"
description: "Cross-tenant preflight job list with drill-down."
---

# Jobs

**Path:** `/dashboard/admin/jobs` · **Who:** Super admin · **Scope:** Cross-tenant

Every preflight job the engine has ever run, across every tenant. Use this when a customer asks "where did my job go?" and you need to see what actually happened.

## What you see

- Paginated table sorted newest-first: tenant, status (pending / processing / complete / failed), profile, filename, created-at.
- Click any row → detail drawer with: full job JSON, logs tab, report links tab, verdict tab.

## Actions

| Action | API | Notes |
|---|---|---|
| Filter by status / tenant | URL query params | `?status=failed&tenant_id=<uuid>` |
| Open report | Links out to `reports.<tenant-domain>/r/<token>` | Opens in a new tab. Share-link expiry still applies. |
| Re-run job | Not implemented — re-submit via API | Use the preflight script or POST to `/api/v1/jobs` manually. |

## Gotchas

- Failed jobs often have useful hints in `error_message`. If it's empty, check the Worker deploy logs for the job id — the Celery stack trace is there.
- Jobs older than the tenant's retention window (default: forever) get cleaned up by `cleanup-expired-reports` beat task. Missing jobs in the list usually means retention kicked in.

## Related

- [Audit panel](./audit) — drill down further into individual findings.
