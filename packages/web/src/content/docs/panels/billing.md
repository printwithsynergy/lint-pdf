---
title: "Billing"
description: "Subscription, invoices, payment method, plan changes, metered overages."
section: "panels"
order: 6
---

# Billing

**Path:** `/dashboard/billing` · **Who:** Owner / Admin

Manage your subscription, review invoices, and configure the one-off buttons that let you exceed the plan's monthly allotment (file packs + AI credits).

## What you see

- **Current plan** card: tier, monthly price, included AI credits + file quota, next renewal date.
- **Payment method** card: card on file (Stripe-hosted), "Update" opens Stripe Customer Portal.
- **Invoices** table: paid, date, amount, download PDF.
- Quick-link cards: [File packs](./billing-files) and [AI credits](./billing-credits) for extra capacity beyond plan defaults.

## Actions

| Action | API | Notes |
|---|---|---|
| Upgrade / downgrade | Stripe Checkout | Downgrades schedule for end-of-cycle; upgrades apply immediately (prorated). |
| Update payment method | Stripe Customer Portal | Redirects to the Stripe-hosted UI. |
| Cancel subscription | Stripe Customer Portal | Cancels at end of period. Your data stays — just becomes read-only once billing ends. |
| View invoice | Stripe-hosted PDF link | Always printable. |

## Gotchas

- **Overage billing** is opt-in. Until you enable it under the plan card, hitting your daily rate limit returns 429 instead of metering extra charges. Once enabled, set a hard `overage_cap_cents` to avoid surprise bills.
- Plan downgrades **don't retroactively adjust** metered packages (AI credits, file packs). Existing grants stay valid for their full 12-month window.
- **Stripe handles everything cardholder-related.** We never see your card number; LintPDF stores only the Stripe customer ID + subscription ID.

## Related

- [AI credits](./billing-credits) — buy extra credit packs outside your plan
- [File packs](./billing-files) — extra monthly file capacity
- [Usage](./usage) — where the numbers that drive billing come from
