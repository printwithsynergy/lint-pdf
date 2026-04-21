---
title: "Webhook DLQ panel"
description: "Cross-tenant dead-letter queue with one-click replay."
---

# Webhook dead letters

**Path:** `/dashboard/admin/webhooks` · **Who:** Super admin · **Scope:** Cross-tenant

Every webhook delivery whose retries have been exhausted. Replay them one-by-one after the receiving endpoint is fixed.

## What you see

- Checkbox **Show all deliveries** (off by default → only `is_dead=true` rows). Tick to include successful + failed-but-still-retrying deliveries.
- Table: created-at, tenant ID (first 8 chars), event name, target URL, attempt count, status badge (DEAD / OK / FAILED), last-error tail, replay-count, per-row **Replay** button.
- Pagination: 50 rows per page.

## Actions

| Action | API | Notes |
|---|---|---|
| Toggle "show all" | Client-side only; re-fetches with `dead=true` query param | |
| Replay a row | `POST /api/v1/admin/webhooks/deliveries/{id}/replay` | Creates a **new** `WebhookDelivery` row, re-signs with the endpoint's current secret, and queues the Celery dispatch task. Clears `is_dead=true` on the original + increments `replay_count`. |
| Refresh | Re-fetches the current page | |

## Gotchas

- **Signing uses the current secret.** If the customer rotated their webhook secret since the original delivery failed, the replay will sign with the new secret — the caller's HMAC validation will still pass as long as they rotated on their side too.
- **Replay creates a new audit row,** not an overwrite. The original `WebhookDelivery` stays in place with `is_dead=false` and its `replay_count` bumped; the new row captures the replay's attempts.
- **The DLQ is never swept automatically.** Rows stay until the per-endpoint `delivery_retention_days` cleanup catches up with them, which skips dead-letters by design.

## Related

- [Replay a dead webhook delivery](../runbooks/webhook-dlq-replay) — step-by-step runbook.
- [Tenant-scoped DLQ](../../webhooks) is available to customers at their own `/api/v1/webhooks/deliveries?dead=true`; the admin version here is the cross-tenant superset.
