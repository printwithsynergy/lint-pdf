---
title: "System health panel"
description: "Live status of the engine, database, Redis, and Celery workers."
---

# System health

**Path:** `/dashboard/admin/health` · **Who:** Super admin · **Scope:** Global

Live dashboard of every piece of infrastructure the engine talks to. Use this as a quick "is it on fire?" check before digging into Railway logs.

## What you see

- Engine status: response from `/api/v1/status` — DB, Redis, queue depths (by queue: default / priority / webhooks), worker count.
- Latest deploy info: git sha, deploy timestamp, Railway service link.
- Recent error-level log tail (last 50 entries) from the engine.

## Actions

| Action | API | Notes |
|---|---|---|
| Refresh | Re-fetches `/api/v1/status` | Polled every 10s automatically. |
| Open in Railway | External link | Jumps to the service-level metrics view. |

## Gotchas

- If `queue_depth` on `webhooks` is high (10k+), the webhook dispatcher is probably backed up — check for repeated 5xx responses from a specific endpoint, then replay via the [Webhook DLQ panel](./webhooks) once it's fixed.
- `worker_count: 0` with `queue_depth > 0` means workers crashed and haven't come back. Railway's restart policy should handle this within a minute; if it doesn't, check the Worker service logs.

## Related

- Engine `/ready` endpoint is the source of truth for Railway's healthcheck; if it returns 503, new traffic stops flowing to that replica.
