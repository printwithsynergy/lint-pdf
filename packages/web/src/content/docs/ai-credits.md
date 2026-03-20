---
title: "AI Credits"
description: "How AI credits work: pay-per-use vs packages, consumption, balance checking, and top-ups."
---

# AI Credits

AI inspections in Never Grounded are metered using a credit system. Core preflight checks (250+ inspections) remain unlimited on all paid plans. AI credits are purchased and consumed separately.

## How Credits Are Consumed

Each AI inspection consumes credits when it runs:

| Tier | Cost | Examples |
|------|------|----------|
| Text | 1 credit | Spell check, language detection, barcode decode, palette matching, duplicate detection |
| Vision | 2 credits | FDA panel analysis, EU compliance, GHS pictogram detection, logo matching, NSFW screening, image quality |

Credits are consumed per-inspection, per-file. If you run 5 Text inspections and 3 Vision inspections on a single file, that file consumes 5 + 6 = 11 credits.

## Billing Modes

### Pay-per-use

- $0.12 per credit
- No minimum purchase
- Billed to your payment method as credits are consumed
- Optional auto top-up: set a threshold and Never Grounded automatically adds credits when your balance drops below it

### Credit Packages

Volume discounts for predictable usage:

| Package | Credits | Price | Per Credit | Savings |
|---------|---------|-------|------------|---------|
| Starter | 100 | $10 | $0.10 | Save 17% |
| Growth | 500 | $40 | $0.08 | Save 33% |
| Scale | 2,000 | $120 | $0.06 | Save 50% |
| Enterprise | 10,000 | $500 | $0.05 | Save 58% |

Credits from packages never expire. You can purchase multiple packages to stack credits.

## Checking Your Balance

### Via The Bridge

Navigate to **Settings > AI Billing** to view your current credit balance, consumption history, and billing mode.

### Via API

```bash
curl https://api.nevergrounded.io/api/v1/ai/credits \
  -H "Authorization: Bearer grd_..."
```

Response:

```json
{
  "balance": 4250,
  "billing_mode": "package",
  "auto_topup": false,
  "consumed_this_month": 750,
  "consumed_total": 3250
}
```

## Top-ups

### Manual Top-up

Purchase additional credits anytime from **Settings > AI Billing > Purchase Credits** or via API:

```bash
curl -X POST https://api.nevergrounded.io/api/v1/ai/credits/topup \
  -H "Authorization: Bearer grd_..." \
  -H "Content-Type: application/json" \
  -d '{"package": "starter"}'
```

### Auto Top-up

Enable auto top-up to automatically purchase credits when your balance drops below a threshold:

```bash
curl -X PUT https://api.nevergrounded.io/api/v1/ai/credits/auto-topup \
  -H "Authorization: Bearer grd_..." \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "threshold": 100,
    "package": "starter"
  }'
```

When your balance drops below 100 credits, a Starter package (1,000 credits) will be purchased automatically.

## Low Balance Alerts

Set up Harbor Signals for credit balance notifications:

```bash
curl -X POST https://api.nevergrounded.io/api/v1/harbor-signals \
  -H "Authorization: Bearer grd_..." \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhook",
    "events": ["ai.credits.low", "ai.credits.depleted"]
  }'
```

## What Happens When Credits Run Out

When your credit balance reaches zero:

- AI inspections are **skipped** (not queued)
- Core engine inspections continue to run normally
- The Captain's Log includes an advisory noting which AI inspections were skipped due to insufficient credits
- Harbor Signal `ai.credits.depleted` fires if configured
