---
title: "Audit panel"
description: "Finding-level preflight history across every tenant."
---

# Audit

**Path:** `/dashboard/admin/audit` · **Who:** Super admin · **Scope:** Cross-tenant

Drill-down view for every preflight finding in the system. Use this when a customer says "my report says X but the PDF looks fine" and you need to trace the finding back to the check that emitted it.

## What you see

- Paginated table of jobs (same shape as [Jobs panel](./jobs)) with an expandable row.
- Expand → findings table: inspection_id, severity, page, object_id, message, bbox, source, category.
- Filter bar: severity (error / warning / advisory), source (engine / ai / imported), page-range.

## Actions

| Action | API | Notes |
|---|---|---|
| Open finding in viewer | Links to `<report-url>?finding=<inspection_id>` | Jumps the viewer to the page + highlights the bbox. |
| Export findings CSV | Client-side CSV of the current filter | Useful for customer-support escalations. |

## Gotchas

- Findings are tenant-scoped in storage but visible cross-tenant here. Respect privacy: don't quote findings in external communication without the tenant's consent.
- `source=imported` findings came from a PitStop / callas / Acrobat XML upload, not from the engine. The `inspection_id` for those is a stable hash of the source report's path, not an engine inspection registry key.

## Related

- [Jobs panel](./jobs) for the job-level view without the per-finding drill.
