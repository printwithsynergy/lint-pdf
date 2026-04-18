# Webhook event sample payloads

Each file in this directory is a sample body for one event type. Wire
your handler against these shapes; the engine guarantees the keys shown
are always present (additional keys may be added in a non-breaking way).

| File | Event |
|---|---|
| `job-state-changed.json` | `job.state_changed` — umbrella with full `/state` digest |
| `verdict-changed.json` | `verdict.changed` |
| `annotation-created.json` | `annotation.created` |
| `comment-created.json` | `comment.created` |
| `report-minted.json` | `report.minted` |
| `share-link-visited.json` | `share_link.visited` |
| `billing-file-quota-low.json` | `billing.file_quota.low` |
| `billing-ai-credits-exhausted.json` | `billing.ai_credits.exhausted` |
| `tenant-plan-changed.json` | `tenant.plan.changed` |

See [`webhooks.md`](../../packages/web/src/content/docs/webhooks.md) for
the full catalog + delivery semantics + replay endpoint usage.
