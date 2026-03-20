---
title: "AI Setup Guide"
description: "How to enable and configure AI-powered preflight inspections on your LintPDF account."
---

# AI Setup Guide

AI-powered preflight inspections are available as an invite-only alpha on all paid plans. This guide walks through enabling AI features, configuring categories, and setting up billing.

## Prerequisites

- An active LintPDF account on a paid plan (Starter, Growth, Scale, or Enterprise)
- AI features enabled on your account (request access via sales@lintpdf.com)
- A valid API Key

## Step 1: Request Access

Email sales@lintpdf.com with your account ID and a brief description of your use case. We enable AI features on accounts individually during the alpha period.

Once enabled, you will see an "AI Inspections" section in the Dashboard under Settings.

## Step 2: Configure AI Categories

Navigate to **Settings > AI Inspections** in the Dashboard. You can enable or disable entire categories:

- **Barcode Detection** — Type identification, decode, quiet zones, contrast, placement
- **Content Quality** — Spell check, language detection, duplicate detection
- **Color Compliance** — Brand palette validation, contrast ratio checks
- **Regulatory: FDA** — Nutrition Facts panel validation per 21 CFR 101.9
- **Regulatory: EU** — Food Information per Regulation 1169/2011
- **Regulatory: GHS/CLP** — Chemical labeling per Regulation 1272/2008
- **Regulatory: Pharma** — EU FMD serialization, Braille, font compliance
- **Brand Verification** — Logo matching, palette compliance
- **Visual Quality** — Image quality assessment, NSFW detection

Enabled categories are applied to all submissions that include AI inspections. You can also override categories per-request (see AI Rulesets documentation).

## Step 3: Set Billing Mode

Choose your credit billing mode in **Settings > AI Billing**:

- **Pay-per-use**: Credits consumed at $0.12 each. No minimum. Auto top-up optional.
- **Credit Package**: Purchase a block of credits at volume discount. Choose from Starter (100), Growth (500), Scale (2,000), or Enterprise (10,000) packages.

## Step 4: Purchase Credits

For pay-per-use, add a payment method and credits will be billed as consumed. For credit packages, purchase from **Settings > AI Billing > Purchase Credits**.

## Step 5: Submit a File with AI

Include the `ai_preset` or `ai_categories` field in your Submit request:

```bash
curl -X POST https://api.lintpdf.com/api/v1/submit \
  -H "Authorization: Bearer lpdf_..." \
  -F file=@packaging.pdf \
  -F ruleset=packaging \
  -F ai_preset=fda-food
```

Or specify individual categories:

```bash
curl -X POST https://api.lintpdf.com/api/v1/submit \
  -H "Authorization: Bearer lpdf_..." \
  -F file=@packaging.pdf \
  -F ruleset=packaging \
  -F ai_categories=barcode,content_quality,regulatory_fda
```

## Verification

After submitting a file with AI enabled, the Report will include AI findings with `source: "ai"` alongside core engine findings. Check your credit balance in the Dashboard or via the API:

```bash
curl https://api.lintpdf.com/api/v1/ai/credits \
  -H "Authorization: Bearer lpdf_..."
```
