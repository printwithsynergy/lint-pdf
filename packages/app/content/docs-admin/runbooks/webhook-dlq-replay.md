---
title: "Replay a dead webhook delivery"
description: "Step-by-step recovery when a customer's webhook endpoint exhausts its retries."
---

# Replay a dead webhook delivery

When a customer's webhook endpoint returns 5xx (or times out) for long enough that the dispatcher exhausts `max_retries`, the delivery is flagged `is_dead=true` and stops retrying. After the customer fixes their endpoint, you replay from the admin UI to re-send the original payload.

## Prerequisites

- Super-admin access to `/dashboard/admin/webhooks`.
- Confirmation from the customer that their endpoint is actually fixed. Replaying into a still-broken endpoint just creates another dead-letter row.

## Steps

### 1. Find the dead deliveries

Open `/dashboard/admin/webhooks`. The page defaults to `dead=true` so the table only shows exhausted deliveries. Filter by tenant (first 8 chars of their UUID) or by event name if you know it.

Each row shows:

- **Created** — when the original dispatch happened.
- **Event** — e.g. `job.completed`, `billing.file-quota.low`.
- **URL** — the customer's endpoint.
- **Attempts** — usually 11 (1 initial + 10 retries, assuming default `max_retries`).
- **Error** — last failure message (HTTP status or exception).
- **Replays** — how many times this delivery has already been manually replayed.

### 2. Verify the endpoint is up

Before hitting Replay, confirm the customer's endpoint is actually serving 2xx again. Either ask them to trigger a test event from their own `/dashboard/webhooks` panel, or curl it directly from a terminal:

```sh
curl -i -X POST https://customer.example.com/lintpdf/webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "ping", "ts": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"}'
```

If that returns 401/403 (because you're not signing), that's fine — the endpoint is at least reachable.

### 3. Click Replay

From the row's action menu, click **Replay**. This:

1. Fetches the original payload + URL from the `webhook_deliveries` row.
2. Creates a *new* `WebhookDelivery` row with `attempt_count=0`, `is_dead=false`.
3. Signs the body with the endpoint's **current** secret (if it was rotated since the original, the replay uses the new one).
4. Queues the Celery dispatch task.
5. On the original row: sets `is_dead=false` and increments `replay_count`.

A success banner appears within ~1s. The new row shows up at the top of the non-dead table — watch it go `processing → complete` (or `failed` if the endpoint is still broken).

### 4. Spot-check the replay

Refresh the page. The new delivery row should show:

- **Status** badge: OK (green) — endpoint returned 2xx.
- Or: FAILED (yellow) and still retrying → wait for the full retry window before giving up.
- Or: DEAD (red) — the endpoint is still broken. Back to step 2.

### 5. Batch replay

There's no bulk-replay UI today. If you have dozens of dead deliveries to the same endpoint, script it:

```sh
ADMIN_KEY="$LINTPDF_ADMIN_API_KEY"
WEBHOOK_ID="<uuid>"
curl -sH "X-Admin-Key: $ADMIN_KEY" \
  "https://api.lintpdf.com/api/v1/admin/webhooks/deliveries?dead=true&webhook_id=$WEBHOOK_ID&page_size=100" \
  | jq -r '.deliveries[].id' \
  | while read id; do
      curl -X POST -H "X-Admin-Key: $ADMIN_KEY" \
        "https://api.lintpdf.com/api/v1/admin/webhooks/deliveries/$id/replay"
      echo
    done
```

## Troubleshooting

**Replay returns 409 Conflict.**
The endpoint was deactivated or deleted between the original dispatch and now. The customer needs to re-register the webhook first; the old `WebhookDelivery` can't be replayed because there's no active endpoint to dispatch to.

**Replay succeeds but the new delivery also dies.**
The customer's endpoint isn't actually fixed. Don't keep replaying — it just creates noise. Share the `last_error` with the customer, ask them to debug their side, then come back.

**The original delivery's `is_dead` didn't clear.**
Check the engine logs for the replay task. If the Postgres commit failed silently, the new row was created but the original's flag update rolled back. Manually patch the row:

```sql
UPDATE webhook_deliveries SET is_dead = false, replay_count = replay_count + 1
WHERE id = '<original-uuid>';
```

## Related

- [Webhook DLQ panel](../panels/webhooks) documents the UI this runbook drives.
- [Admin APIs + Swagger](../admin-api) for the underlying endpoint reference.
