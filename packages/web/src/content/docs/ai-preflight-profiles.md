---
title: "AI in Preflight Profiles"
description: "Using AI checks in Preflight Profiles, presets, and per-request overrides."
section: "ai"
order: 11
---

# AI in Preflight Profiles

AI checks integrate with the existing Preflight Profile system. Use pre-built AI presets, add AI categories to custom Preflight Profiles, or override AI settings per-request.

## AI Presets

Seven pre-built AI presets are available:

| Preset           | ID                 | Checks | Description                             |
| ---------------- | ------------------ | ------ | --------------------------------------- |
| FDA Food         | `fda-food`         | 12     | All FDA nutrition and labeling checks   |
| EU Food          | `eu-food`          | 10     | EU FIR 1169/2011 compliance checks      |
| Pharma EU        | `pharma-eu`        | 9      | EU FMD, Braille, font compliance        |
| GHS Chemical     | `ghs-chemical`     | 12     | GHS/CLP hazard labeling compliance      |
| Packaging QC     | `packaging-qc`     | 14     | Barcode, content quality, visual checks |
| Brand Compliance | `brand-compliance` | 7      | Logo verification, palette matching     |
| Full AI Scan     | `full-ai`          | 33     | All AI checks                           |

### Using a Preset

Include the `ai_preset` field in your Submit request:

```bash
curl -X POST https://api.lintpdf.com/api/v1/submit \
  -H "Authorization: Bearer lpdf_..." \
  -F file=@label.pdf \
  -F ruleset=packaging \
  -F ai_preset=fda-food
```

The core Preflight Profile (`packaging`) runs as normal. The AI preset (`fda-food`) adds AI checks on top.

## Adding AI to Custom Preflight Profiles

When creating a custom Preflight Profile, include an `ai` configuration block:

```bash
curl -X POST https://api.lintpdf.com/api/v1/rulesets \
  -H "Authorization: Bearer lpdf_..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "US Food Packaging",
    "base": "packaging",
    "ai": {
      "categories": ["barcode", "content_quality", "regulatory_fda", "brand"],
      "inspections_override": {
        "ai.content.duplicate_detect": false,
        "ai.brand.palette_match": true
      }
    }
  }'
```

The `categories` array enables entire AI categories. The `inspections_override` object enables or disables individual AI checks within those categories.

## Per-Request Overrides

Override AI settings on individual Submit requests without modifying your Preflight Profile:

```bash
curl -X POST https://api.lintpdf.com/api/v1/submit \
  -H "Authorization: Bearer lpdf_..." \
  -F file=@label.pdf \
  -F ruleset=us-food-packaging \
  -F ai_categories=barcode,regulatory_fda \
  -F ai_skip=ai.content.spell_check
```

### Override Precedence

1. Per-request `ai_categories` and `ai_skip` fields take highest priority
2. Preflight Profile `ai` configuration applies next
3. Account-level AI category settings apply as defaults

## Disabling AI for a Request

To submit a file without any AI checks (even if your Preflight Profile includes them):

```bash
curl -X POST https://api.lintpdf.com/api/v1/submit \
  -H "Authorization: Bearer lpdf_..." \
  -F file=@document.pdf \
  -F ruleset=us-food-packaging \
  -F ai_enabled=false
```

## Listing Available AI Presets

```bash
curl https://api.lintpdf.com/api/v1/ai/presets \
  -H "Authorization: Bearer lpdf_..."
```

Response:

```json
{
  "presets": [
    {
      "id": "fda-food",
      "name": "FDA Food",
      "inspections": 12,
      "categories": ["barcode", "content_quality", "regulatory_fda"],
      "tier": "vision"
    }
  ]
}
```
