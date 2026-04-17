---
title: "AI Credits"
description: "How AI credits work: pay-per-use vs packages, consumption, balance checking, and top-ups."
section: "ai"
order: 4
---

# AI Credits

AI inspections in LintPDF are metered using a credit system. Core preflight checks (500+ checks) stay unlimited on all paid plans. AI credits are a metered resource with two sources:

1. **Plan-included monthly allotment** — granted automatically when your Stripe subscription renews. Resets each billing cycle. See the table below.
2. **Top-up credit packs** — one-off Stripe Checkout purchases that roll over for 12 months.

Separately, LintPDF also meters file submissions (each preflighted PDF counts as one "file"). Plan-included monthly file allotments and one-off file packs use the same mechanism; see [File Packs](#file-packs) below.

## Monthly Plan Allotments

| Plan       | AI credits / month | Files / month |
| ---------- | ------------------ | ------------- |
| Free       | 0                  | 50            |
| Viewer     | 0                  | 50            |
| Starter    | 100                | 500           |
| Growth     | 500                | 2,500         |
| Scale      | 2,000              | 10,000        |
| Enterprise | 10,000             | 100,000       |

Monthly allotments expire at the end of each billing cycle. Unused credits do not roll over. Top-up purchases are separate and DO roll over (12-month expiry).

## How Credits Are Consumed

Each AI inspection consumes credits when it runs:

| Tier   | Cost      | Examples                                                                                                 |
| ------ | --------- | -------------------------------------------------------------------------------------------------------- |
| Text   | 1 credit  | Spell check, language detection, barcode decode, palette matching, duplicate detection                   |
| Vision | 2 credits | FDA panel analysis, EU compliance, GHS pictogram detection, logo matching, NSFW screening, image quality |

Credits are consumed per-inspection, per-file. If you run 5 Text inspections and 3 Vision inspections on a single file, that file consumes 5 + 6 = 11 credits.

## Billing Modes

### Pay-per-use

- $0.12 per credit
- No minimum purchase
- Billed to your payment method as credits are consumed
- Optional auto top-up: set a threshold and LintPDF automatically adds credits when your balance drops below it

### Credit Packs (one-off top-ups)

Three fixed-size packs via Stripe Checkout. Each pack rolls over for 12 months from purchase date.

| Pack       | Credits | Price | Per Credit | Savings  |
| ---------- | ------- | ----- | ---------- | -------- |
| Starter    | 500     | $25   | $0.050     | baseline |
| Growth     | 2,000   | $90   | $0.045     | 10% off  |
| Volume     | 10,000  | $400  | $0.040     | 20% off  |

Buy from the dashboard (**Account → AI Credits → Buy more**) or directly via API (see below). You can stack multiple packs.

## Checking Your Balance

### Via Dashboard

Navigate to **Settings > AI Billing** to view your current credit balance, consumption history, and billing mode.

### Via API

```bash
curl https://api.lintpdf.com/api/v1/ai/credits \
  -H "Authorization: Bearer lpdf_..."
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

### Via Dashboard

**Account → AI Credits → Buy more.** Click a pack tile → redirected to Stripe Checkout → on success your credits land within ~10 seconds.

### Via API

```bash
curl -X POST https://api.lintpdf.com/api/v1/ai/credits/topup \
  -H "Authorization: Bearer lpdf_..." \
  -H "Content-Type: application/json" \
  -d '{"pack": "500"}'
```

Response:

```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_test_...",
  "session_id": "cs_test_...",
  "pack_size": 500,
  "usd_cents": 2500
}
```

Redirect the customer to `checkout_url`. When Stripe fires `checkout.session.completed` to the LintPDF webhook the package is inserted and credits become immediately available. Repeated calls with the same `Stripe-Session` never double-grant (idempotency via the unique index on `stripe_session_id`).

`pack` must be one of `"500"`, `"2000"`, `"10000"`.

## File Packs

Each PDF submission consumes one file from your monthly allotment. Once the monthly pool is empty, further submits either:

- Return `402 Payment Required` — unless you have an active file pack or overage billing is enabled.
- Consume from a purchased file pack (FIFO across the pool).
- Incur overage charges (per-job rate, billed via Stripe metered usage) if `overage_enabled=true`.

File packs are sold via Stripe Checkout in the same way as credits:

| Pack      | Files  | Price | Per File | Savings  |
| --------- | ------ | ----- | -------- | -------- |
| Starter   | 500    | $15   | $0.030   | baseline |
| Growth    | 2,500  | $60   | $0.024   | 20% off  |
| Volume    | 10,000 | $200  | $0.020   | 33% off  |

```bash
curl -X POST https://api.lintpdf.com/api/v1/files/topup \
  -H "Authorization: Bearer lpdf_..." \
  -H "Content-Type: application/json" \
  -d '{"pack": "500"}'
```

Check your file quota balance:

```bash
curl https://api.lintpdf.com/api/v1/files/quota \
  -H "Authorization: Bearer lpdf_..."
```

```json
{
  "tenant_id": "...",
  "total_remaining": 1750,
  "monthly_allotment_remaining": 500,
  "purchased_remaining": 1250,
  "active_packages": 1,
  "monthly_allotment": 500
}
```

## Low Balance Alerts

Set up Webhooks for credit balance notifications:

```bash
curl -X POST https://api.lintpdf.com/api/v1/webhooks \
  -H "Authorization: Bearer lpdf_..." \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhook",
    "events": ["ai.credits.low", "ai.credits.depleted"]
  }'
```

## What Happens When Credits Run Out

When your credit balance reaches zero:

- AI inspections are **skipped** (not queued)
- Core engine checks continue to run normally
- The Report includes an info noting which AI inspections were skipped due to insufficient credits
- Webhook `ai.credits.depleted` fires if configured
