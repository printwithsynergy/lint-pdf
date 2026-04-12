---
title: "Hybrid CLOUDFLOW Integration"
description: "Embed LintPDF preflight into Hybrid Software CLOUDFLOW workflows via REST API."
section: "integrations"
order: 4
---

# Hybrid CLOUDFLOW Integration

> **Already running preflight in CLOUDFLOW?** Submit the PDF to LintPDF in `preflight_source=external` mode with your CLOUDFLOW preflight report attached. Use a built-in parser where possible or wire up a [Custom Import Mapping](/docs/custom-mappings). See [External Preflight Imports](/docs/external-imports) for the full flow.

Hybrid Software CLOUDFLOW is a browser-based prepress workflow platform with a full REST API. LintPDF can be integrated as a preflight step in CLOUDFLOW workflows.

## Integration Architecture

CLOUDFLOW supports two integration approaches:

1. **Workflow node** — A custom CLOUDFLOW application node that calls LintPDF during workflow execution
2. **External script** — A script triggered by CLOUDFLOW that submits files to LintPDF

```
┌──────────┐   JDF / API    ┌────────────────┐   HTTP POST    ┌──────────┐
│  ERP /   │───────────────→│   CLOUDFLOW    │──────────────→│ LintPDF  │
│  MIS     │                │   Workflow     │               │ API      │
│  (CERM,  │                │   Engine       │               │          │
│  LTraxx) │                └───────┬────────┘               └────┬─────┘
└──────────┘                        │                             │
                                    │◄──── Results ───────────────┘
                                    │
                              ┌─────┴──────┐
                              │   Route    │
                              │  Pass/Fail │
                              └────────────┘
```

## Reference: GlobalVision Pattern

GlobalVision's VerifyAPI integration with CLOUDFLOW is a useful reference. It embeds quality inspection (text, artwork, barcode, color, braille verification) directly as a workflow node. LintPDF follows the same pattern — an external inspection API called from within CLOUDFLOW's workflow engine.

## Method 1: REST API Calls from Workflow

CLOUDFLOW workflows can make HTTP calls to external services. Use this to submit files to LintPDF and process results.

### Submit a File

```bash
# From within a CLOUDFLOW workflow script or external trigger:
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -F file=@/path/to/artwork.pdf \
  -F profile_id=gwg-sheetfed
```

**Response:**

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "pending"
}
```

### Poll for Results

```bash
curl https://api.lintpdf.com/api/v1/jobs/f47ac10b-58cc-4372-a567-0e02b2c3d479 \
  -H "Authorization: Bearer lpdf_your_api_key"
```

**Response when complete:**

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "complete",
  "summary": {
    "passed": false,
    "error_count": 2,
    "warning_count": 1,
    "advisory_count": 3,
    "total_findings": 6
  },
  "findings": [
    {
      "inspection_id": "GRD_FONT_001",
      "severity": "error",
      "message": "Font not embedded: Helvetica",
      "page_num": 1
    }
  ]
}
```

### Python Script for CLOUDFLOW

If CLOUDFLOW triggers external scripts, use this Python example:

```python
"""CLOUDFLOW external script: Submit PDF to LintPDF and return results."""

import httpx
import json
import sys
import time

API_KEY = "lpdf_your_api_key"
BASE_URL = "https://api.lintpdf.com"
PROFILE = "gwg-sheetfed"

def preflight(pdf_path: str) -> dict:
    headers = {"Authorization": f"Bearer {API_KEY}"}

    # Submit
    with open(pdf_path, "rb") as f:
        resp = httpx.post(
            f"{BASE_URL}/api/v1/jobs",
            headers=headers,
            files={"file": f},
            data={"profile_id": PROFILE},
            timeout=60,
        )
    resp.raise_for_status()
    job_id = resp.json()["id"]

    # Poll
    for _ in range(120):
        time.sleep(5)
        resp = httpx.get(
            f"{BASE_URL}/api/v1/jobs/{job_id}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data["status"] in ("complete", "failed"):
            return data

    raise TimeoutError(f"Job {job_id} did not complete within 10 minutes")


if __name__ == "__main__":
    pdf_path = sys.argv[1]
    result = preflight(pdf_path)

    # Write sidecar JSON
    with open(pdf_path + ".lintpdf.json", "w") as f:
        json.dump(result, f, indent=2)

    # Exit code for CLOUDFLOW routing
    passed = result.get("summary", {}).get("passed", False)
    sys.exit(0 if passed else 1)
```

## Method 2: DataLink Module

CLOUDFLOW's DataLink module connects to external data sources via XML, JDF, and SQL. This enables bidirectional data flow between your MIS/ERP and CLOUDFLOW.

**Integration pattern:**

1. MIS sends a JDF job ticket to CLOUDFLOW (via DataLink or folder drop)
2. CLOUDFLOW processes the job, calling LintPDF as part of the workflow
3. DataLink writes preflight results back to the MIS database or returns them via JDF/JMF

This is particularly relevant for CERM and Label Traxx integrations, which communicate with CLOUDFLOW via JDF.

## Method 3: Custom Workflow Node

For a native CLOUDFLOW experience, create a custom workflow node that wraps the LintPDF API. This requires working with Hybrid Software's partner team.

**Recommended approach:**

1. Contact Hybrid Software's partner/integration team
2. Request guidance on creating a custom CLOUDFLOW application node
3. The node would: accept a file input → call LintPDF API → output pass/fail with findings

The exact mechanism for creating custom workflow nodes is not fully documented in public resources. Hybrid's team can provide the SDK and documentation needed.

## Webhook Alternative

Instead of polling, register a webhook to receive results asynchronously:

```bash
curl -X POST https://api.lintpdf.com/api/v1/webhooks \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-cloudflow-server/api/webhook/lintpdf",
    "events": ["job.completed", "job.failed"]
  }'
```

CLOUDFLOW's Web Service Access Point can receive the webhook and trigger downstream workflow steps.

## Tips

- **File access:** CLOUDFLOW manages files internally. When triggering external scripts, ensure the file path is accessible from the script's execution context.
- **Profile selection:** Use CLOUDFLOW workflow variables to dynamically select the LintPDF profile based on job metadata (substrate type, print method, customer requirements).
- **Batch workflows:** CLOUDFLOW's workflow engine processes jobs independently. Each file in a batch triggers its own LintPDF submission.
- **Error handling:** Always handle API errors gracefully. Route files that fail to submit (network errors, auth failures) to an error queue rather than silently dropping them.
