---
title: "Integrations Overview"
description: "Connect LintPDF to prepress workflow engines, print ERP/MIS systems, and no-code automation platforms."
section: "integrations"
order: 1
---

# Integrations Overview

LintPDF is a REST API. Any system that can make HTTP calls can integrate with it. This section covers documented integration paths for common print industry systems.

## Integration Approaches

### Direct API Integration

Your system calls LintPDF directly:

1. `POST /api/v1/jobs` with a PDF file and a profile ID
2. Poll `GET /api/v1/jobs/{job_id}` until status is `complete` or `failed`
3. Read findings from the response

This works for any system with HTTP client capabilities — ERP/MIS platforms, custom scripts, no-code tools.

### Indirect Integration (via Workflow Engine)

Your ERP sends jobs to a prepress workflow engine (Enfocus Switch, Esko Automation Engine, Hybrid CLOUDFLOW), which calls LintPDF as a preflight step:

1. ERP sends JDF + files to the workflow engine
2. Workflow engine submits the PDF to LintPDF
3. LintPDF returns findings
4. Workflow engine routes pass/fail and reports back to the ERP

### Webhook-Driven Integration

Instead of polling, register a webhook endpoint to receive results automatically:

```bash
curl -X POST https://api.lintpdf.com/api/v1/webhooks \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-system.com/lintpdf-webhook",
    "events": ["job.completed", "job.failed"]
  }'
```

LintPDF sends a POST to your URL when the job finishes. The payload includes the full job result with findings and summary.

## Quick Reference

The core submit-and-check flow in any integration:

```bash
# 1. Submit a PDF
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -F file=@artwork.pdf \
  -F profile_id=gwg-sheetfed

# Response: { "id": "job_abc123", "status": "pending" }

# 2. Poll for results
curl https://api.lintpdf.com/api/v1/jobs/job_abc123 \
  -H "Authorization: Bearer lpdf_your_api_key"

# Response when complete:
# {
#   "status": "complete",
#   "summary": {
#     "passed": false,
#     "error_count": 2,
#     "warning_count": 1,
#     "advisory_count": 3
#   },
#   "findings": [...]
# }
```

**Severity levels:**

| Severity   | Meaning                                        |
| ---------- | ---------------------------------------------- |
| `error`    | Critical — file will cause production issues   |
| `warning`  | Warning — should be reviewed before production |
| `advisory` | Informational — no action required             |

A job passes when `error_count` is 0.

## Integration Guides

### Prepress Workflow Engines

| System                 | Integration Type                 | Guide                                                   |
| ---------------------- | -------------------------------- | ------------------------------------------------------- |
| Enfocus Switch         | HTTP Request element or Scripter | [Enfocus Switch](/docs/integrations-enfocus-switch)     |
| Esko Automation Engine | Interact with Web Service task   | [Esko AE](/docs/integrations-esko-ae)                   |
| Hybrid CLOUDFLOW       | REST API / custom workflow node  | [Hybrid CLOUDFLOW](/docs/integrations-hybrid-cloudflow) |

### Print ERP / MIS

| System      | Integration Type                              | Guide                                         |
| ----------- | --------------------------------------------- | --------------------------------------------- |
| Label Traxx | Direct (Cloud API) or indirect (AE/CLOUDFLOW) | [Label Traxx](/docs/integrations-label-traxx) |
| CERM        | Indirect (JDF via AE/CLOUDFLOW)               | [CERM](/docs/integrations-cerm)               |
| EFI Pace    | Direct (API) or indirect (JDF/Fiery)          | [EFI Pace](/docs/integrations-efi-pace)       |
| Tharstern   | Indirect (AE) or direct (web services)        | [Tharstern](/docs/integrations-tharstern)     |
| PrintVis    | Direct (D365 APIs / Power Automate)           | [PrintVis](/docs/integrations-printvis)       |

### Desktop & Automation Tools

| System              | Integration Type                                      | Guide                                                    |
| ------------------- | ----------------------------------------------------- | -------------------------------------------------------- |
| Desktop App         | Native GUI hot folder manager (macOS, Windows, Linux) | [Desktop App](/docs/desktop-app)                         |
| Hot Folder CLI      | Python CLI directory watcher for servers              | [Hot Folder](/docs/integrations-hot-folder)              |
| Zapier / Make / n8n | Webhook + HTTP modules                                | [Zapier, Make & n8n](/docs/integrations-zapier-make-n8n) |

## Authentication

All integrations use the same auth method:

```
Authorization: Bearer lpdf_your_api_key
```

Generate your API key in the [LintPDF dashboard](https://app.lintpdf.com). See [Authentication](/docs/authentication) for details.
