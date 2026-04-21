---
title: "Webhooks"
description: "Register endpoints, rotate secrets, inspect delivery history, replay dead letters."
section: "panels"
order: 3
---

# Webhooks

**Path:** `/dashboard/webhooks` · **Who:** Owner / Admin

Register HTTPS endpoints to receive real-time events (job state changes, billing thresholds, approval decisions) as HMAC-signed JSON POSTs.

## What you see

- **Endpoints** table: URL, subscribed events, active flag, created date.
- **Recent deliveries** panel: last 50 dispatches with status, attempt count, and a link to the full delivery detail.
- **Dead letters** filter: tick to show only deliveries whose retries were exhausted.

## Actions

| Action | API | Notes |
|---|---|---|
| Create endpoint | `POST /api/v1/webhooks` | Returns the signing secret once — copy it immediately. |
| Rotate secret | `POST /api/v1/webhooks/{id}/rotate` | Invalidates the old secret. In-flight deliveries complete with the old signature; new ones use the new secret. |
| Test fire | `POST /api/v1/webhooks/{id}/test` | Sends a synthetic `ping` event so you can verify your endpoint is reachable before subscribing to real events. |
| View delivery | `GET /api/v1/webhooks/deliveries/{id}` | Full signed payload + every attempt's status code + error. |
| Replay | `POST /api/v1/webhooks/deliveries/{id}/replay` | Re-fires the original payload. Creates a new delivery row so the audit log stays append-only. |

## Retry + retention

Each endpoint has tunable retry config: `max_retries` (up to 10), `retry_base_delay_seconds`, `retry_max_delay_seconds`. Exponential backoff capped at `retry_max_delay_seconds`. Retention controls (`delivery_retention_days`, per-event `retention_overrides`) let you keep billing events for a year while expiring annotation events in a week.

## Gotchas

- **Only 5xx and network errors retry.** A 4xx response means *you* rejected the payload — retrying won't help. The dispatcher marks the row `success=false` and moves on.
- **Secrets are per-endpoint**, not per-tenant. Rotating one doesn't affect others.
- **Deliveries aren't globally unique** — subscribing two endpoints to the same event sends two separate signed POSTs.

## Related

- [Webhooks docs](../webhooks) — event catalogue, HMAC signing algorithm, payload shapes
- [Postman collection](../postman) — import to try webhook events in a sandbox
