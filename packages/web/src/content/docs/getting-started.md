---
title: "Getting Started"
description: "Three steps to your first LintPDF Report — sign up, get an API key, and submit your first file."
section: "core"
order: 1
---

# Getting Started

LintPDF is a detection-only PDF preflight engine. You send a file, you get a report. Three steps to your first Report:

1. **Sign up** — Create an account at [app.lintpdf.com](https://app.lintpdf.com) and navigate to Dashboard.
2. **Get your API Key** — Generate an API key from the API Key section. Your key starts with `lpdf_`.
3. **Submit your first file** — Submit a PDF to the Submit endpoint and retrieve your Report.

## Quick example

```bash
# Submit a PDF for preflight
curl -X POST https://api.lintpdf.com/api/v1/submit \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -F file=@brochure.pdf \
  -F ruleset=gwg-sheetfed

# Retrieve the Report
curl https://api.lintpdf.com/api/v1/reports/f47ac10b-... \
  -H "Authorization: Bearer lpdf_your_api_key"
```
