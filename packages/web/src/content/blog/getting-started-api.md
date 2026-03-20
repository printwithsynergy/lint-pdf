---
title: "Getting Started with the Never Grounded API"
date: "2026-03-13"
author: "Think Neverland"
category: "API Guides"
excerpt: "A step-by-step guide to integrating Never Grounded into your application. From signup to your first Captain's Log in under five minutes."
tags: ["tutorial", "api", "getting-started"]
---

Integrating Never Grounded into your application takes three steps: sign up, get your Boarding Pass, and submit your first Launch. This guide walks through each step with working code examples.

## Step 1: Create your account

Head to [app.thinkneverland.com](https://app.thinkneverland.com) and create an account. The Free plan includes 50 files per month with full Inspection coverage — no credit card required.

## Step 2: Generate a Boarding Pass

Navigate to The Bridge and open the API Keys section. Generate a new Boarding Pass. Your key will start with `grd_` — copy it and store it securely. Never expose it in client-side code or public repositories.

## Step 3: Submit your first Launch

The Launch endpoint accepts a file and a Voyage Plan. Here is a curl example:

```bash
curl -X POST https://api.nevergrounded.io/api/v1/launch \
  -H "Authorization: Bearer grd_your_boarding_pass" \
  -F file=@brochure.pdf \
  -F voyage_plan=gwg-sheetfed
```

The response includes a Launch ID and a status of `underway` — your file is being processed on The Channel.

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "underway",
  "voyage_plan": "gwg-sheetfed",
  "file_name": "brochure.pdf",
  "created_at": "2026-03-15T10:30:00Z"
}
```

## Step 4: Retrieve the Captain's Log

Once processing is complete (status changes to `docked`), retrieve the Captain's Log:

```bash
curl https://api.nevergrounded.io/api/v1/captains-log/f47ac10b-... \
  -H "Authorization: Bearer grd_your_boarding_pass"
```

The Captain's Log includes a verdict (`clear-to-sail` or `grounded`), a summary with finding counts by severity, and the full list of findings:

```json
{
  "id": "f47ac10b-...",
  "status": "docked",
  "verdict": "grounded",
  "summary": {
    "total_findings": 2,
    "aground": 1,
    "squall": 1,
    "advisory": 0
  },
  "findings": [
    {
      "inspection_id": "font.not_embedded",
      "severity": "aground",
      "message": "Font 'Helvetica' is not embedded",
      "page": 1
    },
    {
      "inspection_id": "color.spot_color_usage",
      "severity": "squall",
      "message": "Spot color 'PANTONE 185 C' found on page 2",
      "page": 2
    }
  ]
}
```

## Using Harbor Signals instead of polling

Instead of polling for the Captain's Log, register a Harbor Signal (webhook) to receive a callback when processing completes:

```bash
curl -X POST https://api.nevergrounded.io/api/v1/harbor-signals \
  -H "Authorization: Bearer grd_your_boarding_pass" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app.com/webhook", "events": ["launch.docked"]}'
```

Never Grounded will POST to your endpoint the instant the Captain's Log is ready.

## Choosing a Voyage Plan

Never Grounded includes four built-in Voyage Plans:

- **GWG Sheetfed** — Commercial offset, sheetfed lithography (196 Inspections)
- **GWG Digital** — Digital printing, wide-format, variable data (180 Inspections)
- **PDF/X-4** — ISO 15930-7 conformance (120 Inspections)
- **Packaging** — Packaging-specific checks including barcode grading (210 Inspections)

List all available Voyage Plans with:

```bash
curl https://api.nevergrounded.io/api/v1/voyage-plans
```

Growth plans and above can create custom Voyage Plans with specific Inspections and thresholds.

## Next steps

Explore the [full API documentation](/docs) for detailed endpoint references, report format schemas, and SDK examples in Python, Node.js, and PHP.
