---
title: "LLM Cost Cap"
description: "Per-tenant monthly cap on LLM API spend (AI-Explain, audit) — enabled, ceiling, alert threshold, used-this-cycle."
section: "ai"
order: 95
---

# LLM Cost Cap

The **LLM cost cap** is a per-tenant ceiling on the dollar value of LLM API calls (AI-Explain, audit, future LLM features) per calendar month. When the cap is exhausted the engine returns `HTTP 402` on LLM endpoints — preflight, reports, and analyzers keep working; only the LLM features pause until the next monthly reset (or a higher cap).

## Why a cap

Without a cap, a runaway integration that calls AI-Explain in a tight loop could rack up unbounded cost overnight. The cap defaults to **off** (`enabled: false`) so existing tenants don't get surprise 402s; turn it on once your usage stabilises. Lockable at TENANT scope so finance can prevent rogue escalation by individual administrators.

## Endpoints

### Read

```
GET /api/v1/ai/cost-cap
Authorization: Bearer lpdf_live_...
```

```json
{
  "enabled": true,
  "monthly_cap_cents": 10000,
  "alert_threshold_pct": 80,
  "used_cents": 1500
}
```

### Update (tenant-scope only)

```
POST /api/v1/ai/cost-cap
Content-Type: application/json
Authorization: Bearer lpdf_live_...

{
  "enabled": true,
  "monthly_cap_cents": 10000,
  "alert_threshold_pct": 80
}
```

## Knobs

| Field | Description |
|---|---|
| `enabled` | Master toggle. `false` = unlimited. |
| `monthly_cap_cents` | Hard ceiling per calendar month. `0` = no cap (use `enabled: false` to disable). |
| `alert_threshold_pct` | Emit a webhook + dashboard banner when usage crosses this percentage of the cap (e.g. `80` = warn at 80%). |
| `used_cents` | (Read-only) Dollars used this calendar month, at the time of the call. Resets on the 1st. |

## Where it shows up

- **Dashboard** — `/dashboard/account/billing/credits` exposes the cap toggle + Save button + used-this-cycle readout.
- **Desktop** — `get_cost_cap` / `set_cost_cap` Tauri commands.
- **SDK** — `get_cost_cap()` / `set_cost_cap()` methods.
- **Plugin + Postman** — same tenant-scoped REST endpoints.

## What happens when the cap fires

```
HTTP/1.1 402 Payment Required
Content-Type: application/json

{
  "detail": "Cost cap exceeded — raise the cap in Account → Billing.",
  "used_cents": 9987,
  "monthly_cap_cents": 10000
}
```

- `POST .../findings/{id}/explain` returns 402.
- Cached explanations remain readable (no new API call needed).
- `record_usage` calls that would have logged a charge are skipped.
- A dashboard banner + webhook fire (if subscribed) at `alert_threshold_pct`.
- The cap resets at 00:00 UTC on the 1st of the next month.

## Lockability

`epm_thresholds` and `ai_cost_cap` are **lockable** ToggleOverride categories — a TENANT-scope row marked `locked=true` blocks WORKFLOW and CALL overrides from raising it. Use this when finance needs to enforce a hard ceiling against individual administrators.
