---
title: "PrintVis Integration"
description: "Integrate LintPDF with PrintVis via Microsoft Dynamics 365 APIs and Power Automate."
section: "integrations"
order: 9
---

# PrintVis Integration

PrintVis is built on Microsoft Dynamics 365 Business Central. This means it inherits all D365 integration capabilities: REST/OData APIs, Power Automate connectors, Azure Logic Apps, and the full Microsoft integration ecosystem.

This is potentially the **easiest direct integration** of any print MIS because of the Power Automate no-code path.

## Option 1: Power Automate (No-Code)

Microsoft Power Automate can connect PrintVis to LintPDF without writing any code.

### Flow Design

```
[Trigger: New job in PrintVis]
    ↓
[Get file: Download artwork PDF from D365]
    ↓
[HTTP: POST to LintPDF /api/v1/jobs]
    ↓
[Delay: Wait 10 seconds]
    ↓
[HTTP: GET LintPDF /api/v1/jobs/{id}]
    ↓
[Condition: Is status "complete"?]
    ├── No → [Loop back to GET]
    └── Yes →
        [Parse JSON: Extract summary]
            ↓
        [Condition: summary.passed == true?]
            ├── Yes → [Update PrintVis: Preflight passed]
            └── No  → [Update PrintVis: Preflight failed]
                       [Send notification email]
```

### Step-by-Step Setup

#### 1. Create the Flow Trigger

In Power Automate, create a new flow with trigger:

- **Trigger:** "When a record is created" (Dataverse / Business Central connector)
- **Table:** Your PrintVis jobs table
- **Filter:** Status equals "artwork received" (adjust to your workflow)

#### 2. Download the Artwork

Add a **Business Central** action:

- **Action:** "Get record" or download the artwork file attachment
- The exact action depends on how PrintVis stores artwork files

#### 3. Submit to LintPDF

Add an **HTTP** action:

- **Method:** POST
- **URI:** `https://api.lintpdf.com/api/v1/jobs`
- **Headers:**
  - `Authorization`: `Bearer lpdf_your_api_key`
- **Body:** Form-data with:
  - `file`: The artwork file content from the previous step
  - `profile_id`: `gwg-sheetfed`

#### 4. Poll for Results

Add a **Do Until** loop:

- **Condition:** `status` equals `complete` OR `status` equals `failed`
- **Inside the loop:**
  - **HTTP** action: GET `https://api.lintpdf.com/api/v1/jobs/{job_id}` with auth header
  - **Delay:** 5 seconds
  - **Parse JSON:** Extract `status` from the response

#### 5. Route Based on Results

Add a **Condition** action:

- **Condition:** `body('Parse_JSON')?['summary']?['passed']` equals `true`
- **If yes:** Update PrintVis job record to "preflight passed"
- **If no:** Update PrintVis job record to "preflight failed" + send notification

## Option 2: D365 Business Central OData API (Code)

For developers who prefer code over Power Automate:

### Python Middleware

```python
"""
PrintVis (D365 Business Central) → LintPDF integration.

Uses D365 Business Central OData API for job data
and LintPDF REST API for preflight.
"""

import httpx
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# ----- D365 Business Central configuration -----
D365_BASE = "https://api.businesscentral.dynamics.com/v2.0/{tenant_id}/{environment}/ODataV4"
D365_TOKEN = "your_d365_oauth_token"  # OAuth 2.0 bearer token

# ----- LintPDF configuration -----
LINTPDF_BASE = "https://api.lintpdf.com"
LINTPDF_API_KEY = "lpdf_your_api_key"
LINTPDF_PROFILE = "gwg-sheetfed"


def get_pending_jobs(d365: httpx.Client) -> list[dict]:
    """Query PrintVis jobs needing preflight via OData."""
    resp = d365.get(
        "/Company('Your Company')/printVisJobs",
        params={"$filter": "preflightStatus eq 'pending'"},
    )
    resp.raise_for_status()
    return resp.json().get("value", [])


def preflight(lp: httpx.Client, pdf_data: bytes, filename: str) -> dict:
    """Submit PDF to LintPDF and poll for results."""
    resp = lp.post(
        "/api/v1/jobs",
        files={"file": (filename, pdf_data, "application/pdf")},
        data={"profile_id": LINTPDF_PROFILE},
    )
    resp.raise_for_status()
    job_id = resp.json()["id"]

    for _ in range(120):
        time.sleep(5)
        resp = lp.get(f"/api/v1/jobs/{job_id}")
        resp.raise_for_status()
        data = resp.json()
        if data["status"] in ("complete", "failed"):
            return data

    raise TimeoutError(f"Job {job_id} timed out")


def update_job(d365: httpx.Client, job_id: str, result: dict):
    """Write preflight results back to PrintVis via OData."""
    summary = result.get("summary", {})
    d365.patch(
        f"/Company('Your Company')/printVisJobs('{job_id}')",
        json={
            "preflightStatus": "pass" if summary.get("passed") else "fail",
            "preflightFindings": summary.get("total_findings", 0),
        },
    )


def main():
    d365 = httpx.Client(
        base_url=D365_BASE,
        headers={"Authorization": f"Bearer {D365_TOKEN}"},
        timeout=60,
    )
    lp = httpx.Client(
        base_url=LINTPDF_BASE,
        headers={"Authorization": f"Bearer {LINTPDF_API_KEY}"},
        timeout=60,
    )

    while True:
        try:
            for job in get_pending_jobs(d365):
                log.info("Processing PrintVis job: %s", job["id"])
                # Download artwork - adjust based on your D365 attachment API
                pdf_resp = d365.get(f"/Company('Your Company')/jobAttachments('{job['artworkId']}')/content")
                result = preflight(lp, pdf_resp.content, f"{job['id']}.pdf")
                update_job(d365, job["id"], result)
                log.info("Job %s: %s", job["id"], "PASS" if result["summary"]["passed"] else "FAIL")
        except Exception:
            log.exception("Error in polling loop")
        time.sleep(30)


if __name__ == "__main__":
    main()
```

> **Note:** D365 Business Central OData endpoints and field names vary by tenant configuration. The examples above use illustrative entity names. Refer to your D365 Business Central API documentation and PrintVis customization guide for exact endpoints.

## Option 3: Azure Logic Apps

Azure Logic Apps provides a similar no-code experience to Power Automate but runs in Azure infrastructure. The flow design is identical — use the Business Central connector and HTTP actions to bridge PrintVis and LintPDF.

## Comparison

| Approach         | Complexity    | Maintenance | Best For                      |
| ---------------- | ------------- | ----------- | ----------------------------- |
| Power Automate   | Low (no-code) | Low         | Quick setup, small teams      |
| D365 OData API   | Medium (code) | Medium      | Custom logic, high volume     |
| Azure Logic Apps | Low (no-code) | Low         | Enterprise Azure environments |

## Tips

- **OAuth 2.0:** D365 Business Central APIs require OAuth 2.0 authentication. Register an Azure AD application and obtain tokens using the client credentials flow.
- **Webhook alternative:** Instead of polling LintPDF, register a webhook to receive results and trigger a Power Automate flow on webhook receipt.
- **Batch processing:** Power Automate has execution limits. For high-volume operations, use the OData API approach with a dedicated service.
