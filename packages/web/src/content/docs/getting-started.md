---
title: "Getting Started"
description: "Three steps to your first LintPDF Report — sign up, get an API key, and submit your first file."
section: "core"
order: 1
---

# Getting Started

LintPDF is a detection-only PDF preflight engine. You send a file, you get a report. Three steps to your first Report:

1. **Sign up** — Create an account at [app.lintpdf.com](https://app.lintpdf.com) and navigate to Dashboard.
2. **Get your API Key** — Generate an API key from the API Key section. Your key starts with `lpdf_live_` (production) or `lpdf_test_` (sandbox).
3. **Submit your first file** — POST a PDF to `/api/v1/jobs` and retrieve the job.

## Path A — run LintPDF's engine

This is the default. LintPDF runs its full analyzer suite — 600+ checks, plus all viewer capabilities (pages, separations, fonts, images, TAC, findings).

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F profile_id=lintpdf-default

# Response
# { "job_id": "d4e5f6a7-...", "status": "queued" }

curl https://api.lintpdf.com/api/v1/jobs/d4e5f6a7-... \
  -H "Authorization: Bearer lpdf_live_..."
```

## Path B — import an existing preflight report

If your shop already runs Enfocus PitStop, callas pdfToolbox, or Adobe Acrobat Preflight upstream, send the PDF plus the report file. LintPDF parses the findings and renders them in the viewer — no re-checking.

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@pitstop-report.xml \
  -F preflight_source=external \
  -F external_format=pitstop_xml
```

See [External Preflight Imports](/docs/external-imports) for the full list of supported formats and the [Custom Import Mappings](/docs/custom-mappings) page if your report shape isn't built in.

## Path C — viewer-only submission (no preflight)

When all you need is the PDF renderer, the share link, or approval verdicts — no analyzers — submit in `minimal` mode. Analyzer output like separations or TAC can still be filled on demand.

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F preflight_source=minimal
```

See [Viewer-Only Submissions](/docs/viewer-only-mode) and [Viewer Capabilities](/docs/viewer-capabilities) for the full behavior and fill-in pattern.

## What's next

- [Preflight Modes](/docs/preflight-modes) — when to pick engine / external / minimal.
- [API Reference](/docs/api-reference) — every route, every field.
- [Authentication](/docs/authentication) — key scopes and permissions.
