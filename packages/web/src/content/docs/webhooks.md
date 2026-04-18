---
title: "Webhooks"
description: "Event catalog, delivery semantics, replay, and HMAC signing."
section: "api"
order: 37
---

# Webhooks

LintPDF notifies your systems of state changes in-flight — preflight results, approval decisions, viewer annotations + comments, billing thresholds — via signed HTTP POSTs. This page is the full event catalog and delivery contract.

## Register an endpoint

```sh
curl -X POST https://api.lintpdf.com/api/v1/webhooks \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
        "url": "https://hooks.example.com/lintpdf",
        "events": ["job.state_changed", "approval.chain.completed"]
      }'
```

`events` is optional — an empty list subscribes to **every** event. Registration returns a `secret`; store it server-side to verify HMAC signatures (shown below).

## Event catalog

### Preflight lifecycle

| Event | Fires when |
|---|---|
| `job.completed` | Preflight completes successfully. Payload includes summary counts. |
| `job.failed` | Engine exception or import parse failure. Payload includes `error`. |
| `job.state_changed` | **Umbrella.** Fires whenever `GET /jobs/{id}/state` would differ — job completion, approval decisions, verdict changes, annotation + comment mutations, report mints. Payload is the full `/state` digest inline plus a `reason` tag for routing. |

### Approvals

| Event | Fires when |
|---|---|
| `approval.chain.started` | Chain attached + step 0 kicked off. |
| `approval.step.started` | Step enters active review. |
| `approval.step.decided` | Approver submits a decision (approved or rejected) + optional notes. |
| `approval.chain.completed` | Final step approved → chain success. |
| `approval.chain.rejected` | Any step rejected → chain terminates. |
| `approval.chain.cancelled` | Chain manually cancelled. |
| `approval.chain.timeout` | Step expires without decision. |

### Viewer annotations + comments

| Event | Fires when |
|---|---|
| `annotation.created` | A reviewer draws a rect/circle/arrow/note/freehand on a page. |
| `annotation.deleted` | Annotation is removed. |
| `comment.created` | New comment on an annotation thread. |

### Verdicts

| Event | Fires when |
|---|---|
| `verdict.changed` | `POST /viewer/jobs/{id}/verdict` flips `pass` → `fail` or vice versa. Payload includes `previous`, `current`, `verdict_by`, `notes`. |

### Reports

| Event | Fires when |
|---|---|
| `report.minted` | `POST /jobs/{id}/reports` returns at least one URL. Payload lists every minted `{format, url, token, expires_at}`. |
| `report.expired` | A report token's `expires_at` passes and the nightly sweep deletes it. One event per token. |

### Share links

| Event | Fires when |
|---|---|
| `share_link.visited` | First touch per `(token, visitor_email)` pair. Subsequent visits update `last_seen_at` silently — no event spam. |

### Billing thresholds

| Event | Fires when |
|---|---|
| `billing.file_quota.low` | Monthly file pool drops from >10% to ≤10% on deduction. One-shot per crossing. |
| `billing.file_quota.exhausted` | Submit rejected with 402 because the pool is empty and overage is off. |
| `billing.ai_credits.low` | AI credits crossed the 10% watermark (CREDIT_PACKAGE billing mode only). |
| `billing.ai_credits.exhausted` | Credit package drained to zero. |

### Tenant admin

| Event | Fires when |
|---|---|
| `tenant.plan.changed` | Admin `PATCH /admin/tenants/{id}/plan` sets a new plan value. Payload carries `previous_plan` + `new_plan`. |

## Delivery semantics

Every delivery is recorded in a `webhook_deliveries` audit table. For each event the engine:

1. Creates a `WebhookDelivery` row with the exact JSON body we'll sign.
2. Queues a Celery task that POSTs the body with HMAC-SHA256 signing, updates the row with `attempt_count`, `final_status_code`, `delivered_at`, and `last_error`.
3. On 2xx response → row marked `success = true`, no more attempts.
4. On 5xx / timeout / network error → Celery `self.retry()` is invoked with exponential backoff until `max_retries` is hit. Every retry updates the SAME row, so `attempt_count` reflects the total tries.
5. On 4xx → row marked `success = false`, **no retry** (the caller's endpoint rejected the payload shape; retrying the same body won't fix it).

### Retry config

Configurable per endpoint at create or update time:

| Field | Default | Range | Purpose |
|---|---|---|---|
| `max_retries` | 3 | 0–10 | Upper bound on retry attempts for one delivery. Capped at 10 platform-wide so a misconfiguration can't DoS the dispatch pool. |
| `retry_base_delay_seconds` | 5 | 1–600 | Initial delay before the first retry. |
| `retry_max_delay_seconds` | 300 | 1–3600 | Ceiling on the exponential backoff — attempt N sleeps `min(base * 2**(N-1), max)` seconds. |

Any field set to `null` inherits the platform default.

### Retention

| Field | Default | Range | Purpose |
|---|---|---|---|
| `delivery_retention_days` | `null` (forever) | 1–365 | Nightly sweep deletes `webhook_deliveries` rows older than this for the endpoint. `null` keeps forever. |
| `retention_overrides` | `{}` | — | Per-event overrides keyed by fnmatch glob. E.g. `{"billing.*": 365, "annotation.*": 7}`. Longest-match wins; events that don't match any key use `delivery_retention_days`. |

The sweep runs daily via Celery Beat (`sweep_webhook_deliveries` task). Deletion is tenant-scoped — rows from other tenants' endpoints are never touched.

Operators and integrators can inspect / replay every past delivery:

```sh
# List recent deliveries, newest first.
curl "https://api.lintpdf.com/api/v1/webhooks/deliveries?page=1&page_size=50" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}"

# Filter to failures on a specific endpoint.
curl "https://api.lintpdf.com/api/v1/webhooks/deliveries?webhook_id=...&success=false" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}"

# Inspect the full signed payload of one delivery.
curl "https://api.lintpdf.com/api/v1/webhooks/deliveries/${DELIVERY_ID}" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}"

# Re-fire. Creates a NEW delivery row with the same event + payload
# (audit history is preserved, nothing is mutated in place).
curl -X POST "https://api.lintpdf.com/api/v1/webhooks/deliveries/${DELIVERY_ID}/replay" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}"
```

Replay fails with `409 Conflict` when the origin endpoint is deleted or deactivated — rotating a secret is fine, but a dead URL needs to be re-registered first.

## Signing

Every delivery carries two headers:

```
X-LintPDF-Event:     job.state_changed
X-LintPDF-Signature: sha256=<hmac-sha256-of-body>
```

Verify in your handler:

```python
import hmac, hashlib

def verify(secret: bytes, body: bytes, signature_header: str) -> bool:
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
```

The signed body is the raw JSON LintPDF POSTed — keys are sorted alphabetically (`sort_keys=True`) so the canonical form is stable and not dependent on Python dict ordering.

## Example payloads

Each event has a sample payload under [`docs/examples/webhook-events/`](https://github.com/thinkneverland/lint-pdf/tree/main/docs/examples/webhook-events). Start with `job-state-changed.json` if you're wiring up the umbrella subscription.

## Related

- [Universal Job State API](/docs/job-state) — the shape embedded in `job.state_changed`.
- [Approval Verdicts](/docs/viewer-verdict)
- [Share Links](/docs/share-links)
