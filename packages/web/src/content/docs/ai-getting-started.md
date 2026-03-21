---
title: "AI Getting Started"
description: "Four steps to your first AI-powered LintPDF Report."
section: "ai"
order: 1
---

# AI Getting Started

AI features are available as an invite-only alpha on all paid plans. Four steps to your first AI-powered Report:

1. **Request Access** — Email [sales@lintpdf.com](mailto:sales@lintpdf.com) with your account ID and use case. We enable AI features individually during alpha.
2. **Purchase Credits** — Buy credits via pay-per-use ($0.12/credit) or volume packages starting at 100 credits for $10. Navigate to **Settings > AI Billing** in Dashboard.
3. **Configure Categories** — Enable AI categories in **Settings > AI Inspections**. Choose from barcode, content quality, regulatory, brand, and visual quality.
4. **Submit with AI** — Add `ai_preset` or `ai_categories` to your Submit request.

## Quick example

```bash
# Submit a PDF with FDA AI preset
curl -X POST https://api.lintpdf.com/api/v1/submit \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -F file=@food-label.pdf \
  -F ruleset=packaging \
  -F ai_preset=fda-food

# Report includes both core engine and AI findings
curl https://api.lintpdf.com/api/v1/reports/f47ac10b-... \
  -H "Authorization: Bearer lpdf_your_api_key"

# Check your credit balance
curl https://api.lintpdf.com/api/v1/ai/credits \
  -H "Authorization: Bearer lpdf_your_api_key"
```
