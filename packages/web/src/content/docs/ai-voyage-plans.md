---
title: "AI in Voyage Plans"
description: "Using AI inspections in Voyage Plans, presets, and per-request overrides."
---

# AI in Voyage Plans

AI inspections integrate with the existing Voyage Plan system. Use pre-built AI presets, add AI categories to custom Voyage Plans, or override AI settings per-request.

## AI Presets

Seven pre-built AI presets are available:

| Preset | ID | Inspections | Description |
|--------|----|-------------|-------------|
| FDA Food | `fda-food` | 12 | All FDA nutrition and labeling inspections |
| EU Food | `eu-food` | 10 | EU FIR 1169/2011 compliance checks |
| Pharma EU | `pharma-eu` | 9 | EU FMD, Braille, font compliance |
| GHS Chemical | `ghs-chemical` | 12 | GHS/CLP hazard labeling compliance |
| Packaging QC | `packaging-qc` | 14 | Barcode, content quality, visual checks |
| Brand Compliance | `brand-compliance` | 7 | Logo verification, palette matching |
| Full AI Scan | `full-ai` | 33 | All AI inspections |

### Using a Preset

Include the `ai_preset` field in your Launch request:

```bash
curl -X POST https://api.nevergrounded.io/api/v1/launch \
  -H "Authorization: Bearer grd_..." \
  -F file=@label.pdf \
  -F voyage_plan=packaging \
  -F ai_preset=fda-food
```

The core Voyage Plan (`packaging`) runs as normal. The AI preset (`fda-food`) adds AI inspections on top.

## Adding AI to Custom Voyage Plans

When creating a custom Voyage Plan, include an `ai` configuration block:

```bash
curl -X POST https://api.nevergrounded.io/api/v1/voyage-plans \
  -H "Authorization: Bearer grd_..." \
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

The `categories` array enables entire AI categories. The `inspections_override` object enables or disables individual AI inspections within those categories.

## Per-Request Overrides

Override AI settings on individual Launch requests without modifying your Voyage Plan:

```bash
curl -X POST https://api.nevergrounded.io/api/v1/launch \
  -H "Authorization: Bearer grd_..." \
  -F file=@label.pdf \
  -F voyage_plan=us-food-packaging \
  -F ai_categories=barcode,regulatory_fda \
  -F ai_skip=ai.content.spell_check
```

### Override Precedence

1. Per-request `ai_categories` and `ai_skip` fields take highest priority
2. Voyage Plan `ai` configuration applies next
3. Account-level AI category settings apply as defaults

## Disabling AI for a Request

To run a Launch without any AI inspections (even if your Voyage Plan includes them):

```bash
curl -X POST https://api.nevergrounded.io/api/v1/launch \
  -H "Authorization: Bearer grd_..." \
  -F file=@document.pdf \
  -F voyage_plan=us-food-packaging \
  -F ai_enabled=false
```

## Listing Available AI Presets

```bash
curl https://api.nevergrounded.io/api/v1/ai/presets \
  -H "Authorization: Bearer grd_..."
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
