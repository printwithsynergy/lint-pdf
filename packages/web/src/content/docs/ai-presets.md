---
title: "AI Presets"
description: "Pre-built collections of AI inspections for common use cases."
section: "ai"
order: 6
---

# AI Presets

Pre-built collections of AI inspections for common use cases. Use a preset ID in your Submit request to run a curated set of AI inspections.

| Preset           | ID                 | Inspections | Categories                                                 |
| ---------------- | ------------------ | ----------- | ---------------------------------------------------------- |
| FDA Food         | `fda-food`         | 12          | barcode, content_quality, regulatory_fda                   |
| EU Food          | `eu-food`          | 10          | barcode, content_quality, regulatory_eu                    |
| Pharma EU        | `pharma-eu`        | 9           | barcode, regulatory_pharma, visual_quality                 |
| GHS Chemical     | `ghs-chemical`     | 12          | barcode, content_quality, regulatory_ghs                   |
| Packaging QC     | `packaging-qc`     | 14          | barcode, content_quality, color_compliance, visual_quality |
| Brand Compliance | `brand-compliance` | 7           | brand, color_compliance, content_quality                   |
| Full AI Scan     | `full-ai`          | 32          | All categories                                             |

## Listing Presets via API

```bash
curl https://api.lintpdf.com/api/v1/ai/presets \
  -H "Authorization: Bearer lpdf_..."

# Response
{
  "presets": [
    {
      "id": "fda-food",
      "name": "FDA Food",
      "inspections": 12,
      "categories": ["barcode", "content_quality", "regulatory_fda"],
      "tier": "gpu"
    },
    ...
  ]
}
```
