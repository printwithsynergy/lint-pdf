---
title: "AI Usage Monitoring"
description: "Monitor AI credit consumption, usage trends, and quality metrics with built-in analytics."
---

# AI Usage Monitoring

LintPDF provides detailed usage analytics for AI inspections, including per-feature breakdowns, trend analysis, and spending tracking.

## Viewing Usage

Fetch AI usage data for your tenant:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.lintpdf.com/api/v1/ai/usage?start_date=2026-03-01&end_date=2026-03-16"
```

### Filtering Options

| Parameter    | Description                    | Example             |
| ------------ | ------------------------------ | ------------------- |
| `start_date` | Start of date range (ISO 8601) | `2026-03-01`        |
| `end_date`   | End of date range (ISO 8601)   | `2026-03-16`        |
| `category`   | Filter by AI category          | `barcode_detection` |
| `feature`    | Filter by specific feature     | `barcode_decode`    |

### Response

```json
{
  "usage": [
    {
      "date": "2026-03-15",
      "category": "barcode_detection",
      "feature": "barcode_decode",
      "job_count": 42,
      "credits_consumed": 42,
      "total_cost": "5.04",
      "avg_processing_time_ms": 1250
    }
  ],
  "total_credits": 156,
  "total_cost": "18.72",
  "period": {
    "start": "2026-03-01",
    "end": "2026-03-16"
  }
}
```

## Usage Trends (SPC)

The trends endpoint provides statistical process control (SPC) data for monitoring submission quality over time:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.lintpdf.com/api/v1/ai/usage/trends"
```

### Response

```json
{
  "trends": [
    {
      "date": "2026-03-15",
      "total_jobs": 50,
      "ai_jobs": 35,
      "total_findings": 120,
      "ai_findings": 45,
      "error_count": 2,
      "warning_count": 18,
      "info_count": 25,
      "avg_findings_per_job": 2.4,
      "pass_rate": 0.82
    }
  ],
  "spc": {
    "mean_findings": 2.1,
    "ucl": 4.8,
    "lcl": 0.0,
    "std_dev": 0.9,
    "out_of_control_dates": []
  }
}
```

The SPC (Statistical Process Control) data includes:

- **mean_findings**: Average findings per job over the period
- **ucl / lcl**: Upper and lower control limits (mean +/- 3 standard deviations)
- **std_dev**: Standard deviation of findings per job
- **out_of_control_dates**: Dates where findings exceeded control limits (signals quality shifts)

## Admin Usage View

Admins can view AI usage across all tenants:

```bash
curl -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  "https://api.lintpdf.com/api/v1/admin/ai/usage?start_date=2026-03-01"
```

This returns aggregated usage grouped by tenant, useful for billing reconciliation and capacity planning.

## Spending Alerts

Configure Webhooks for proactive credit balance notifications:

```bash
curl -X POST https://api.lintpdf.com/api/v1/webhooks \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhook",
    "events": ["ai.credits.low", "ai.credits.depleted"]
  }'
```

Available AI-specific events:

| Event                      | Description                                                                 |
| -------------------------- | --------------------------------------------------------------------------- |
| `ai.credits.low`           | Credit balance dropped below 20% of last package purchase                   |
| `ai.credits.depleted`      | Credit balance reached zero — AI inspections will be skipped                |
| `ai.circuit_breaker.open`  | Vision circuit breaker tripped — Vision inspections temporarily unavailable |
| `ai.circuit_breaker.close` | Vision circuit breaker reset — Vision inspections available again           |

If a `monthly_spending_limit` is configured on your AI config, AI inspections are skipped when the limit is reached. Core engine checks continue normally. Monitor your spending via the credits endpoint:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.lintpdf.com/api/v1/ai/credits"
```

This returns your current balance, active packages, and month-to-date spending.

## Best Practices

1. **Set spending limits** — Configure `monthly_spending_limit` to prevent unexpected charges
2. **Monitor trends** — Use the SPC endpoint to detect quality regressions early
3. **Review by category** — Filter usage by category to understand which AI features provide the most value
4. **Archive usage data** — Periodically export usage data for long-term analysis and compliance
