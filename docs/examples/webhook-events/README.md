# Webhook event sample payloads

Each file in this directory is a sample body for one event type. Wire
your handler against these shapes; the engine guarantees the keys shown
are always present (additional keys may be added in a non-breaking way).

## Preflight lifecycle

| File | Event |
|---|---|
| `job-state-changed.json` | `job.state_changed` — umbrella with full `/state` digest |

## Approvals

| File | Event |
|---|---|
| `approval-step-decided.json` | `approval.step.decided` |
| `approval-chain-completed.json` | `approval.chain.completed` |

## Viewer

| File | Event |
|---|---|
| `annotation-created.json` | `annotation.created` |
| `annotation-deleted.json` | `annotation.deleted` |
| `comment-created.json` | `comment.created` |
| `verdict-changed.json` | `verdict.changed` |

## Reports & sharing

| File | Event |
|---|---|
| `report-minted.json` | `report.minted` |
| `report-expired.json` | `report.expired` |
| `share-link-visited.json` | `share_link.visited` |

## Billing thresholds

| File | Event |
|---|---|
| `billing-file-quota-low.json` | `billing.file_quota.low` |
| `billing-file-quota-exhausted.json` | `billing.file_quota.exhausted` |
| `billing-ai-credits-low.json` | `billing.ai_credits.low` |
| `billing-ai-credits-exhausted.json` | `billing.ai_credits.exhausted` |

## Tenant admin

| File | Event |
|---|---|
| `tenant-plan-changed.json` | `tenant.plan.changed` |

See [`webhooks.md`](../../../packages/web/src/content/docs/webhooks.md)
for the full catalog + delivery semantics + replay endpoint usage.
The interactive Swagger reference lives at
<https://lintpdf.com/swagger>.
