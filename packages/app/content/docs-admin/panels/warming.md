---
title: "Tile warming panel"
description: "Monitor + trigger viewer-tile warming jobs for large PDFs."
---

# Tile warming

**Path:** `/dashboard/admin/warming` · **Who:** Super admin · **Scope:** Cross-tenant

The viewer renders large PDFs as tiled images that get generated + cached on R2 on first open. Warming proactively pre-renders those tiles for specific jobs so the first viewer visit is instant instead of taking 5–30s.

## What you see

- Summary: total tiles warmed today, avg time-to-warm, count of jobs queued / in-progress / failed.
- Events table: last 100 warming events with job_id, status, started-at, duration.
- Jobs table: per-job warming status with re-warm button.

## Actions

| Action | API | Notes |
|---|---|---|
| Re-warm a job | `POST /api/v1/admin/warming/jobs/{id}` | Re-kicks the Celery task that renders every page-tile + TAC/separation layers for the job. Idempotent — skips already-warmed tiles. |
| Purge job tiles | `DELETE /api/v1/admin/warming/jobs/{id}` | Deletes the R2-hosted tiles. Viewer will fall back to on-demand rendering. |

## Gotchas

- Tiles are served via `tile_cdn_base_url` (Cloudflare R2 custom domain, configurable per-env). A misconfigured CDN URL → viewer shows broken images until the on-demand path kicks in.
- Warming a 500-page PDF can take 2–3 minutes. Queue it during off-hours for noisy jobs.

## Related

- Viewer docs explain the tile model to end users.
