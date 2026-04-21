---
title: "AI overview"
description: "Enable, configure, and submit with AI-powered preflight inspections."
section: "ai"
order: 1
---

# AI overview

AI-powered preflight inspections run on top of the detection engine — barcode decoding, spell check, brand compliance, regulatory labelling, image quality. This page is the full "turn it on and use it" walkthrough. If you want to go deeper, see [Presets](./presets), [Credits](./credits), [Brand config](./brand-config), or the [AI API reference](./api).

## Getting started — four steps

1. **Request access.** AI is invite-only alpha on all paid plans. Email [sales@lintpdf.com](mailto:sales@lintpdf.com) with your account ID and a one-line use case.
2. **Purchase credits.** Pay-per-use ($0.12/credit) or volume packages starting at 100 credits for $10. Set up under **Settings → AI Billing** in the dashboard.
3. **Configure categories.** Enable the categories you want under **Settings → AI Inspections**. Choose from barcode, content quality, colour compliance, regulatory (FDA / EU / GHS / Pharma), brand, and visual quality.
4. **Submit with AI.** Add `ai_preset` or `ai_categories` to your submit request.

## Quick example

```sh
# Submit a PDF with the FDA food preset
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -F file=@food-label.pdf \
  -F profile_id=lintpdf-default \
  -F ai_preset=fda-food

# Check your credit balance
curl https://api.lintpdf.com/api/v1/ai/credits \
  -H "Authorization: Bearer lpdf_your_api_key"
```

## Prerequisites

- Active account on a paid plan (Starter, Growth, Scale, or Enterprise).
- AI features enabled for your account (request via [sales@lintpdf.com](mailto:sales@lintpdf.com)).
- A valid API key with AI scope.

Once AI is enabled, the dashboard surfaces an **AI Inspections** section under Settings.

## AI categories

| Category            | Inspections | Tier   | What it covers                              |
| ------------------- | ----------- | ------ | ------------------------------------------- |
| `barcode`           | 7           | Text   | Type detection, decode, quiet zones, contrast, placement |
| `content_quality`   | 3           | Text   | Spell check, language detection, duplicates |
| `color_compliance`  | 2           | Text   | Brand palette validation, contrast ratio    |
| `regulatory_fda`    | 5           | Vision | FDA Nutrition Facts (21 CFR 101.9)          |
| `regulatory_eu`     | 4           | Vision | EU Food Information (Reg. 1169/2011)        |
| `regulatory_ghs`    | 5           | Vision | GHS/CLP chemical labels (Reg. 1272/2008)    |
| `regulatory_pharma` | 3           | Vision | EU FMD serialization, Braille, font         |
| `brand`             | 2           | Mixed  | Logo matching, palette compliance           |
| `visual_quality`    | 2           | Vision | Image quality, NSFW screening               |

Enable categories under **Settings → AI Inspections**; they apply to every submission unless you override them per-request.

## Configuration levels

AI settings resolve at three levels, from broadest to most specific:

1. **Account defaults** — Your standing category selection under Settings.
2. **Ruleset settings** — A ruleset can bake in its own `ai_categories`; see the [Presets](./presets) doc for the named bundles.
3. **Per-request** — `ai_preset=<name>` or `ai_categories=barcode,content_quality,regulatory_fda` on the submit payload override both of the above for that single job.

## Brand configuration

Brand-related inspections read three kinds of assets from **Settings → AI Brand**:

- **Colour palette** — approved brand colours as hex values with Delta E tolerance.
- **Reference logos** — upload variations (horizontal, stacked, icon-only, reversed).
- **Custom dictionary** — brand names, product names, and technical terms that the spell checker should treat as valid.

More under [AI Brand config](./brand-config).

## Confidence threshold

Set the minimum confidence score for AI findings under **Settings → AI Inspections**. Default is **0.75**. Findings below the threshold are still computed but hidden from the report unless you query the `?include_low_confidence=true` variant.

## Billing modes

Choose your billing mode under **Settings → AI Billing**:

- **Pay-per-use** — credits consumed at $0.12 each, no minimum. Optional auto top-up when balance runs low.
- **Credit package** — buy a block at volume discount. Starter (100) / Growth (500) / Scale (2,000) / Enterprise (10,000).

See [Credits](./credits) for the full billing model and [Monitoring](./monitoring) for usage analytics.

## Verification

After submitting with AI enabled, the report's findings include entries with `source: "ai"` alongside core engine findings. Check balance via the dashboard (Settings → AI Billing) or the API:

```sh
curl https://api.lintpdf.com/api/v1/ai/credits \
  -H "Authorization: Bearer lpdf_..."
```

## Submit with category override

Want a specific category cocktail instead of a named preset? Pass `ai_categories` explicitly:

```sh
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_..." \
  -F file=@packaging.pdf \
  -F profile_id=lintpdf-default \
  -F ai_categories=barcode,content_quality,regulatory_fda
```

## Related

- [Presets](./presets) — curated category bundles for common use cases
- [Credits](./credits) — billing model + cost estimation
- [Brand config](./brand-config) — palette, logos, dictionary
- [Monitoring](./monitoring) — time-series usage dashboards
- [Troubleshooting](./troubleshooting) — FAQ + error reference
