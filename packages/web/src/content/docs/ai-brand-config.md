---
title: "AI Brand Configuration"
description: "Setting up brand palette, uploading reference logos, and configuring custom dictionaries for AI checks."
---

# AI Brand Configuration

LintPDF AI checks can validate files against your brand guidelines. Configure your brand palette, upload reference logos, and maintain a custom dictionary for spell checking.

## Brand Palette

Define your approved brand colors so the `ai.color.brand_palette` inspection can flag off-brand color usage.

### Via Dashboard

Navigate to **Settings > AI Brand > Color Palette** and add your brand colors as hex values with optional names:

- Primary: #1a365d
- Secondary: #3b6fb5
- Accent: #e2a832

### Via API

```bash
curl -X PUT https://api.lintpdf.com/api/v1/ai/brand/palette \
  -H "Authorization: Bearer lpdf_..." \
  -H "Content-Type: application/json" \
  -d '{
    "colors": [
      {"hex": "#1a365d", "name": "Primary Navy"},
      {"hex": "#3b6fb5", "name": "Secondary Blue"},
      {"hex": "#e2a832", "name": "Accent Gold"}
    ],
    "tolerance": 5
  }'
```

The `tolerance` field sets the maximum Delta E (CIE2000) difference allowed before flagging a color as off-brand. Default is 5.

## Reference Logos

Upload reference versions of your logos so the `ai.brand.logo_match` inspection can verify logo usage in submitted files.

### Via Dashboard

Navigate to **Settings > AI Brand > Logos** and upload your reference logo files. Supported formats: PNG, SVG, PDF, EPS.

Upload multiple variations if needed (horizontal, stacked, icon-only, reversed, etc.). LintPDF will match detected logos against all uploaded references.

### Via API

```bash
curl -X POST https://api.lintpdf.com/api/v1/ai/brand/logos \
  -H "Authorization: Bearer lpdf_..." \
  -F file=@logo-horizontal.png \
  -F name="Horizontal Logo" \
  -F variant="horizontal"
```

### Logo Matching Behavior

When the `ai.brand.logo_match` inspection runs, it:

1. Scans each page for logo-like elements
2. Compares detected elements against all uploaded reference logos
3. Reports findings for: logo not found, distorted logo, incorrect variant, low-resolution logo

## Custom Dictionary

Add brand-specific words, product names, and technical terms to your custom dictionary so the `ai.content.spell_check` inspection does not flag them as misspellings.

### Via Dashboard

Navigate to **Settings > AI Brand > Dictionary** and add words one per line or upload a text file.

### Via API

```bash
curl -X PUT https://api.lintpdf.com/api/v1/ai/brand/dictionary \
  -H "Authorization: Bearer lpdf_..." \
  -H "Content-Type: application/json" \
  -d '{
    "words": [
      "LintPDF",
      "PreflightPro",
      "XtraShield",
      "BioClean"
    ],
    "mode": "append"
  }'
```

Use `mode: "replace"` to overwrite the entire dictionary or `mode: "append"` to add to existing entries.

### Dictionary Limits

| Plan       | Max Words |
| ---------- | --------- |
| Starter    | 500       |
| Growth     | 2,000     |
| Scale      | 10,000    |
| Enterprise | Unlimited |
