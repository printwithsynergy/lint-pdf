---
title: "Label Traxx Integration"
description: "Integrate LintPDF with Label Traxx via the Cloud API (direct) or through Esko AE / Hybrid CLOUDFLOW (indirect)."
section: "integrations"
order: 5
---

# Label Traxx Integration

Label Traxx (by Amtech Software) is a label and packaging MIS with a REST-based Cloud API (v9+). LintPDF integrates via two paths:

1. **Direct** — Middleware polls Label Traxx for new jobs, submits PDFs to LintPDF, writes results back
2. **Indirect** — Label Traxx sends JDF + files to Esko AE or Hybrid CLOUDFLOW, which calls LintPDF

## Direct Integration

A middleware script bridges Label Traxx and LintPDF. This runs on your infrastructure — a server, a cron job, or a service.

### Architecture

```
┌──────────────┐   Poll for jobs   ┌──────────────┐   Submit PDF   ┌──────────┐
│  Label Traxx │◄─────────────────│  Middleware   │──────────────→│ LintPDF  │
│  Cloud API   │                  │  Script       │               │ API      │
│              │   Write results  │              │◄──────────────│          │
│              │◄─────────────────│              │   Results     │          │
└──────────────┘                  └──────────────┘               └──────────┘
```

### Middleware Example (Python)

```python
"""
Label Traxx → LintPDF middleware.

Polls Label Traxx for jobs with new artwork, submits PDFs to LintPDF,
and writes preflight results back to the Label Traxx job record.

Requirements: pip install httpx
"""

import httpx
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# ----- Configuration -----
LABEL_TRAXX_BASE = "https://your-instance.labeltraxx.cloud/api"
LABEL_TRAXX_API_KEY = "your_label_traxx_api_key"

LINTPDF_BASE = "https://api.lintpdf.com"
LINTPDF_API_KEY = "lpdf_your_api_key"
LINTPDF_PROFILE = "gwg-sheetfed"

POLL_INTERVAL = 30  # seconds between Label Traxx polls


def get_new_jobs(lt_client: httpx.Client) -> list[dict]:
    """Fetch jobs from Label Traxx that need preflight.

    Adjust the endpoint and filters to match your Label Traxx API.
    Refer to your Label Traxx Swagger docs for available endpoints.
    """
    resp = lt_client.get("/v1/jobs", params={"status": "artwork_received"})
    resp.raise_for_status()
    return resp.json().get("data", [])


def download_artwork(lt_client: httpx.Client, job: dict) -> bytes | None:
    """Download the artwork PDF from Label Traxx.

    The exact endpoint depends on your Label Traxx configuration.
    Check your Swagger docs for the file download endpoint.
    """
    artwork_url = job.get("artwork_url")
    if not artwork_url:
        return None
    resp = lt_client.get(artwork_url)
    resp.raise_for_status()
    return resp.content


def submit_to_lintpdf(lp_client: httpx.Client, pdf_data: bytes, filename: str) -> dict:
    """Submit a PDF to LintPDF and wait for results."""
    # Submit
    resp = lp_client.post(
        "/api/v1/jobs",
        files={"file": (filename, pdf_data, "application/pdf")},
        data={"profile_id": LINTPDF_PROFILE},
    )
    resp.raise_for_status()
    job_id = resp.json()["id"]
    log.info("LintPDF job submitted: %s", job_id)

    # Poll for completion
    for _ in range(120):
        time.sleep(5)
        resp = lp_client.get(f"/api/v1/jobs/{job_id}")
        resp.raise_for_status()
        data = resp.json()
        if data["status"] in ("complete", "failed"):
            return data

    raise TimeoutError(f"LintPDF job {job_id} timed out")


def update_label_traxx(lt_client: httpx.Client, job_id: str, result: dict):
    """Write preflight results back to the Label Traxx job record.

    Adjust the endpoint and payload to match your Label Traxx API.
    Refer to your Swagger docs for the job update endpoint.
    """
    summary = result.get("summary", {})
    lt_client.patch(
        f"/v1/jobs/{job_id}",
        json={
            "preflight_status": "pass" if summary.get("passed") else "fail",
            "preflight_findings": summary.get("total_findings", 0),
            "preflight_critical": summary.get("aground_count", 0),
        },
    )


def main():
    lt_client = httpx.Client(
        base_url=LABEL_TRAXX_BASE,
        headers={"Authorization": f"Bearer {LABEL_TRAXX_API_KEY}"},
        timeout=60,
    )
    lp_client = httpx.Client(
        base_url=LINTPDF_BASE,
        headers={"Authorization": f"Bearer {LINTPDF_API_KEY}"},
        timeout=60,
    )

    log.info("Starting Label Traxx → LintPDF middleware")

    while True:
        try:
            jobs = get_new_jobs(lt_client)
            for job in jobs:
                job_id = job["id"]
                log.info("Processing Label Traxx job: %s", job_id)

                pdf_data = download_artwork(lt_client, job)
                if not pdf_data:
                    log.warning("No artwork for job %s, skipping", job_id)
                    continue

                result = submit_to_lintpdf(lp_client, pdf_data, f"{job_id}.pdf")
                passed = result.get("summary", {}).get("passed", False)
                log.info("Job %s preflight: %s", job_id, "PASS" if passed else "FAIL")

                update_label_traxx(lt_client, job_id, result)

        except Exception:
            log.exception("Error in polling loop")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
```

> **Note:** Label Traxx Cloud API Swagger documentation requires login to access. The endpoints shown above (`/v1/jobs`, artwork download, job update) are illustrative patterns. Refer to your own Label Traxx API documentation for exact endpoint URLs, field names, and authentication details.

## Indirect Integration

Label Traxx communicates with Esko Automation Engine and Hybrid CLOUDFLOW via JDF. In this path, the workflow engine calls LintPDF — Label Traxx doesn't interact with LintPDF directly.

### Architecture

```
┌──────────────┐   JDF + files   ┌──────────────┐   HTTP POST   ┌──────────┐
│  Label Traxx │────────────────→│  Esko AE /   │─────────────→│ LintPDF  │
│              │                 │  CLOUDFLOW   │              │ API      │
│              │◄────────────────│              │◄─────────────│          │
│              │   JDF status    │              │   Results    │          │
└──────────────┘                 └──────────────┘              └──────────┘
```

### Setup

1. **Label Traxx → Workflow Engine:** Configure Label Traxx to submit jobs to your prepress workflow engine. Label Traxx supports JDF output to both Esko AE and Hybrid CLOUDFLOW.

2. **Workflow Engine → LintPDF:** Configure the workflow engine to call LintPDF as a preflight step. See:
   - [Esko Automation Engine integration](/docs/integrations-esko-ae)
   - [Hybrid CLOUDFLOW integration](/docs/integrations-hybrid-cloudflow)

3. **Results back to Label Traxx:** The workflow engine reports job status back to Label Traxx via JDF/JMF. Preflight results (pass/fail, finding counts) can be mapped into JDF audit messages or custom extensions.

### When to Use Each Path

| Criteria                             | Direct    | Indirect                        |
| ------------------------------------ | --------- | ------------------------------- |
| Already using AE/CLOUDFLOW           | —         | Preferred                       |
| Simple setup, minimal dependencies   | Preferred | —                               |
| Want prepress workflow integration   | —         | Preferred                       |
| Need real-time status in Label Traxx | Preferred | Depends on JDF roundtrip        |
| Custom preflight logic per job       | Preferred | Possible via workflow variables |

## Tips

- **API key scope:** The Label Traxx Cloud API uses its own API key. The LintPDF API uses a separate `lpdf_` key. Both are configured in the middleware.
- **Job matching:** Use Label Traxx job IDs as tags or metadata when submitting to LintPDF for traceability.
- **Data Warehouse:** Label Traxx's real-time cloud SQL replication (Data Warehouse) can be used to query job status and trigger preflight workflows.
