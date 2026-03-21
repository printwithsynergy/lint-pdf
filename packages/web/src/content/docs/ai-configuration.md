---
title: "AI Configuration"
description: "Configure AI features at account, Ruleset, and per-request levels."
section: "ai"
order: 3
---

# AI Configuration

AI features are configured at three levels: account defaults, Ruleset settings, and per-request overrides.

## Account-Level Settings

In **Settings > AI Inspections**, enable or disable entire AI categories. These serve as defaults for all submissions.

| Category | Inspections | Tier | Description |
| --- | --- | --- | --- |
| `barcode` | 7 | Text | Barcode detection, decode, validation |
| `content_quality` | 3 | Text | Spell check, language, duplicates |
| `color_compliance` | 2 | Text | Brand palette, contrast ratio |
| `regulatory_fda` | 5 | Vision | FDA Nutrition Facts (21 CFR 101.9) |
| `regulatory_eu` | 4 | Vision | EU Food Information (1169/2011) |
| `regulatory_ghs` | 5 | Vision | GHS/CLP Chemical Labels (1272/2008) |
| `regulatory_pharma` | 3 | Vision | Pharmaceutical Packaging (EU FMD) |
| `brand` | 2 | Mixed | Logo matching, palette compliance |
| `visual_quality` | 2 | Vision | Image quality, NSFW screening |

## Brand Configuration

For brand-related AI inspections, configure your assets in **Settings > AI Brand**:

- **Color Palette** — Add approved brand colors as hex values with Delta E tolerance
- **Reference Logos** — Upload logo variations (horizontal, stacked, icon-only, reversed)
- **Custom Dictionary** — Add brand names, product names, and technical terms for spell checking

## Confidence Threshold

Set the minimum confidence score for AI findings in **Settings > AI Inspections**. Default is 0.75. Only findings above this threshold appear in your Report.
