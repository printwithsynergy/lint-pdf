---
title: "Usage"
description: "Jobs, AI credits, and file-pack consumption over time."
section: "panels"
order: 7
---

# Usage

**Path:** `/dashboard/usage` · **Who:** Owner / Admin (Members read-only)

Time-series charts of everything your plan meters. Use this to spot consumption trends before you hit a cap or to reconcile an invoice.

## What you see

- **Jobs per day** line chart — last 30 days by default, with profile breakdown.
- **AI credits** consumption — stacked by inspection category (brand, regulatory, spelling, barcode, image quality).
- **File-pack burn-down** — monthly allotment remaining.
- **Rate-limit headroom** — requests/min against your per-minute burst ceiling.

## Actions

| Action | API | Notes |
|---|---|---|
| Change window | Query param `?days=7|30|90|365` | 365-day views aggregate to weekly buckets. |
| Export CSV | Client-side of the current chart data | Matches what the chart shows. |
| Drill into a day | Click a point → opens [Reports](./reports) filtered to that date | |

## Gotchas

- **Counters refresh every ~30s**, not in real time. A burst of jobs takes up to a minute to appear here.
- **AI credits used vs. consumed differ.** Credits are *reserved* at submit time and *refunded* if the job fails or the specific inspection didn't run. The chart shows net consumption.
- **Rate-limit headroom is per-tenant**, summed across every API key on your account.

## Related

- [Billing](./billing) — where consumption turns into dollars
- [Authentication](../authentication#rate-limits) — rate-limit mechanics
