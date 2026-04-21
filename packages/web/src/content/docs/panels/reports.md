---
title: "Reports"
description: "Every job this tenant has run, with filters and bulk actions."
section: "panels"
order: 5
---

# Reports

**Path:** `/dashboard/reports` · **Who:** Any signed-in tenant user

The searchable list of every preflight job this tenant has run. Open a report, re-run a file, export metadata, or archive old jobs.

## What you see

- Filters: status, profile, date range, submitter, AI-enabled flag.
- Table: file name, status, profile, created-at, duration, findings count, report-token link.
- Per-row: **Open report** (new tab), **Re-run** (resubmits), **Archive** (soft-hide from default view).

## Actions

| Action | API | Notes |
|---|---|---|
| Search / filter | URL query params | Bookmark a filter by copying the URL. |
| Open report | Links to `reports.<tenant-domain>/r/<token>` | Share-link expiry applies — expired links land on a 410 page. |
| Re-run | `POST /api/v1/jobs` with the same file key | Re-consumes a file from the monthly quota. |
| Export CSV | Client-side of current filter | Up to 1000 rows per export. |
| Archive | `PATCH /api/v1/jobs/{id}` with `archived=true` | Hides from the default list; you can still open via direct URL or by showing archived. |

## Gotchas

- **Archive is soft.** The data stays; only the list-view visibility changes. Use "Show archived" to un-hide.
- **Retention is tenant-wide.** Your plan's `report_retention_days` controls when the underlying tokens + stored artefacts expire. Archiving doesn't extend retention.
- **Bulk operations are missing by design.** For cross-tenant ops, use the admin panel; for single-tenant bulk work, use the API.

## Related

- [Preflight](./preflight) — run a new job
- [Report formats](../report-formats) — what the PDF / HTML / JSON report contains
