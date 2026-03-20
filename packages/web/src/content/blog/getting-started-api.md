---
title: "Getting Started with the LintPDF API"
date: "2026-03-13"
author: "Think Neverland"
category: "API Guides"
excerpt: "A step-by-step guide to integrating LintPDF into your application. From signup to your first Report in under five minutes."
tags: ["tutorial", "api", "getting-started"]
---

Integrating LintPDF into your application takes three steps: sign up, get your API Key, and submit your first file. This guide walks through each step with working code examples.

## Step 1: Create your account

Head to [app.lintpdf.com](https://app.lintpdf.com) and create an account. The Free plan includes 50 files per month with full Check coverage — no credit card required.

## Step 2: Generate an API Key

Navigate to the Dashboard and open the API Keys section. Generate a new API Key. Your key will start with `lpdf_` — copy it and store it securely. Never expose it in client-side code or public repositories.

## Step 3: Submit your first file

The Submit endpoint accepts a file and a Ruleset. Here is a curl example:

```bash
curl -X POST https://api.lintpdf.com/api/v1/submit \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -F file=@brochure.pdf \
  -F ruleset=gwg-sheetfed
```

The response includes a job ID and a status of `processing` — your file is being processed on the Queue.

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "processing",
  "ruleset": "gwg-sheetfed",
  "file_name": "brochure.pdf",
  "created_at": "2026-03-15T10:30:00Z"
}
```

## Step 4: Retrieve the Report

Once processing is complete (status changes to `complete`), retrieve the Report:

```bash
curl https://api.lintpdf.com/api/v1/reports/f47ac10b-... \
  -H "Authorization: Bearer lpdf_your_api_key"
```

The Report includes a verdict (`pass` or `failed`), a summary with finding counts by severity, and the full list of findings:

```json
{
  "id": "f47ac10b-...",
  "status": "complete",
  "verdict": "failed",
  "summary": {
    "total_findings": 2,
    "error": 1,
    "warning": 1,
    "info": 0
  },
  "findings": [
    {
      "inspection_id": "font.not_embedded",
      "severity": "error",
      "message": "Font 'Helvetica' is not embedded",
      "page": 1
    },
    {
      "inspection_id": "color.spot_color_usage",
      "severity": "warning",
      "message": "Spot color 'PANTONE 185 C' found on page 2",
      "page": 2
    }
  ]
}
```

## Using Webhooks instead of polling

Instead of polling for the Report, register a Webhook to receive a callback when processing completes:

```bash
curl -X POST https://api.lintpdf.com/api/v1/webhooks \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app.com/webhook", "events": ["job.complete"]}'
```

LintPDF will POST to your endpoint the instant the Report is ready.

## Choosing a Ruleset

LintPDF includes four built-in Rulesets:

- **GWG Sheetfed** — Commercial offset, sheetfed lithography (196 Checks)
- **GWG Digital** — Digital printing, wide-format, variable data (180 Checks)
- **PDF/X-4** — ISO 15930-7 conformance (120 Checks)
- **Packaging** — Packaging-specific checks including barcode grading (210 Checks)

List all available Rulesets with:

```bash
curl https://api.lintpdf.com/api/v1/rulesets
```

Growth plans and above can create custom Rulesets with specific Checks and thresholds.

## Next steps

Explore the [full API documentation](/docs) for detailed endpoint references, report format schemas, and SDK examples in Python, Node.js, and PHP.
