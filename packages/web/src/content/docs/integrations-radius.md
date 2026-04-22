---
title: "Radius Integration"
description: "Integrate LintPDF with Radius MIS via JDF workflows through Esko AE / Hybrid CLOUDFLOW, or direct middleware."
section: "integrations"
order: 10
---

# Radius Integration

Radius is a label and packaging print MIS. Like other MIS systems in this category, Radius integrates with LintPDF through an **indirect path** — JDF job tickets flow through a prepress workflow engine (Esko Automation Engine or Hybrid CLOUDFLOW), which calls LintPDF as a preflight step. Shops with in-house developers can also bridge Radius directly via polling middleware.

> **Direct REST API is not a standard offering.** Radius installations typically expose data through JDF/JMF exchange and database-level integrations rather than a public REST API. The integration path below is JDF-based through workflow engines, which is the supported approach for most sites.

## Integration Architecture

```
┌─────────┐  JDF + files  ┌──────────────┐  HTTP POST  ┌──────────┐
│ Radius  │──────────────→│  Esko AE /   │────────────→│ LintPDF  │
│  MIS    │               │  CLOUDFLOW   │             │ API      │
│         │◄──────────────│              │◄────────────│          │
│         │  JDF status   │              │  Results    │          │
└─────────┘               └──────────────┘             └──────────┘
```

## How It Works

### Step 1: Radius Sends JDF to Workflow Engine

Radius writes JDF job tickets and drops them into hotfolders monitored by the prepress workflow engine. The JDF ticket contains job specifications, artwork references, and production parameters.

**Recommended workflow engines:**

- **Esko Automation Engine** — JDF/JMF communication, widely deployed in label and packaging
- **Hybrid CLOUDFLOW** — REST-based workflow engine with a custom node for LintPDF

### Step 2: Workflow Engine Runs LintPDF Preflight

The workflow engine picks up the JDF ticket, extracts the artwork file(s), and submits them to LintPDF for preflight.

**For Esko AE:** See [Esko Automation Engine integration](/docs/integrations-esko-ae) for step-by-step setup.

**For CLOUDFLOW:** See [Hybrid CLOUDFLOW integration](/docs/integrations-hybrid-cloudflow) for setup details.

The workflow engine:

1. Parses the JDF ticket to identify artwork files
2. Submits each file to LintPDF via `POST /api/v1/jobs`
3. Polls for results via `GET /api/v1/jobs/{job_id}`
4. Routes files based on pass/fail

### Step 3: Results Flow Back to Radius

The workflow engine reports preflight results back to Radius through the JDF/JMF channel, or by updating a shared database field / hotfolder status file depending on the Radius configuration at your site.

## Example Flow

```
Radius creates job → JDF ticket written to hotfolder
    ↓
Esko AE / CLOUDFLOW picks up JDF
    ↓
Workflow extracts artwork PDF
    ↓
POST /api/v1/jobs → LintPDF preflight
    ↓
GET /api/v1/jobs/{id} → Poll for results
    ↓
Results: passed=true/false, error/warning/advisory counts
    ↓
Workflow routes file (pass/fail)
    ↓
JDF/JMF status update → Radius
    ↓
Radius displays preflight status on job record
```

## LintPDF API Call (from Workflow Engine)

The LintPDF portion is identical regardless of which MIS originated the job:

```bash
# Submit the artwork PDF
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -F file=@artwork.pdf \
  -F profile_id=gwg-sheetfed

# Poll for results
curl https://api.lintpdf.com/api/v1/jobs/{job_id} \
  -H "Authorization: Bearer lpdf_your_api_key"
```

## Option 2: Direct Middleware (Advanced)

For sites with in-house developers and database access to the Radius schema, a lightweight Python service can poll the Radius database for jobs needing preflight and invoke LintPDF directly — bypassing the workflow engine for simple cases.

```python
"""
Radius → LintPDF direct middleware.

Polls Radius for jobs in a "needs-preflight" state, submits the
artwork to LintPDF, writes the result back to the Radius job record.

Adapt the Radius access layer (DB cursor / hotfolder / vendor API)
to match your site's configuration.
"""

import httpx
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

LINTPDF_BASE = "https://api.lintpdf.com"
LINTPDF_API_KEY = "lpdf_your_api_key"
LINTPDF_PROFILE = "gwg-sheetfed"


def fetch_pending_jobs():
    """
    Return Radius jobs awaiting preflight. Implement against your
    Radius data source — SQL view, hotfolder, or vendor tooling.
    """
    raise NotImplementedError


def fetch_artwork(job) -> tuple[bytes, str]:
    """Return (pdf_bytes, filename) for the given Radius job."""
    raise NotImplementedError


def update_job(job, result: dict):
    """Write preflight status + findings back to Radius."""
    raise NotImplementedError


def preflight(lp: httpx.Client, pdf: bytes, filename: str) -> dict:
    resp = lp.post(
        "/api/v1/jobs",
        files={"file": (filename, pdf, "application/pdf")},
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


def main():
    lp = httpx.Client(
        base_url=LINTPDF_BASE,
        headers={"Authorization": f"Bearer {LINTPDF_API_KEY}"},
        timeout=60,
    )

    while True:
        try:
            for job in fetch_pending_jobs():
                log.info("Processing Radius job: %s", job["id"])
                pdf, filename = fetch_artwork(job)
                result = preflight(lp, pdf, filename)
                update_job(job, result)
                log.info("Job %s: %s", job["id"], "PASS" if result["summary"]["passed"] else "FAIL")
        except Exception:
            log.exception("Error in polling loop")
        time.sleep(30)


if __name__ == "__main__":
    main()
```

## Tips

- **Profile selection:** Map Radius job parameters (substrate, print method, product family) to LintPDF profiles at the workflow engine or middleware layer. Use `gwg-sheetfed` for offset, `gwg-digital` for digital, or a custom profile.
- **JDF extensions:** If Radius ships custom JDF extensions at your site, make sure your workflow engine parses them correctly before relying on them to drive profile selection.
- **Webhooks:** Instead of polling LintPDF, register a webhook to fire when a job completes and have the workflow engine / middleware push results back to Radius on receipt.
- **Hotfolder monitoring:** Ensure the JDF hotfolder is correctly configured and monitored. Test with a sample JDF ticket before going live.
