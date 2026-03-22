---
title: "EFI Pace Integration"
description: "Integrate LintPDF with EFI Pace via the REST API (direct) or JDF/Fiery workflow (indirect)."
section: "integrations"
order: 7
---

# EFI Pace Integration

EFI Pace (eProductivity Software) is a print MIS with REST API capabilities and JDF/JMF support through Fiery. LintPDF integrates via two paths:

1. **Direct** — Middleware connects Pace's API to LintPDF
2. **Indirect** — Pace sends JDF via Fiery to a prepress workflow engine, which calls LintPDF

## Direct Integration

A middleware script monitors Pace for new jobs with artwork, submits PDFs to LintPDF, and writes results back.

### Architecture

```
┌──────────┐   Poll / webhook   ┌──────────────┐   Submit PDF   ┌──────────┐
│  EFI     │◄──────────────────│  Middleware   │──────────────→│ LintPDF  │
│  Pace    │                   │  Script       │               │ API      │
│  API     │   Write results   │              │◄──────────────│          │
│          │◄──────────────────│              │   Results     │          │
└──────────┘                   └──────────────┘               └──────────┘
```

### Middleware Pattern (Python)

```python
"""
EFI Pace → LintPDF middleware pattern.

Monitors Pace for jobs needing preflight, submits to LintPDF,
and writes results back to Pace.

Note: Pace API documentation is not publicly available.
Adjust endpoints and field names per your Pace API docs
and Connectivity Toolkit documentation.
"""

import httpx
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# ----- Configuration -----
PACE_BASE = "https://your-pace-instance.com/api"
PACE_API_KEY = "your_pace_api_key"

LINTPDF_BASE = "https://api.lintpdf.com"
LINTPDF_API_KEY = "lpdf_your_api_key"
LINTPDF_PROFILE = "gwg-sheetfed"


def get_pending_jobs(pace: httpx.Client) -> list[dict]:
    """Fetch jobs needing preflight from Pace.

    Refer to your Pace API / PaceConnect documentation
    for the correct endpoint and query parameters.
    """
    resp = pace.get("/jobs", params={"preflight_status": "pending"})
    resp.raise_for_status()
    return resp.json().get("items", [])


def submit_and_wait(lp: httpx.Client, pdf_data: bytes, filename: str) -> dict:
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

    raise TimeoutError(f"LintPDF job {job_id} timed out")


def update_pace(pace: httpx.Client, job_id: str, result: dict):
    """Write preflight results back to Pace job record.

    Adjust the endpoint and payload per your Pace API docs.
    """
    summary = result.get("summary", {})
    pace.patch(
        f"/jobs/{job_id}/preflight",
        json={
            "status": "pass" if summary.get("passed") else "fail",
            "findings_count": summary.get("total_findings", 0),
            "critical_count": summary.get("aground_count", 0),
        },
    )


def main():
    pace = httpx.Client(
        base_url=PACE_BASE,
        headers={"Authorization": f"Bearer {PACE_API_KEY}"},
        timeout=60,
    )
    lp = httpx.Client(
        base_url=LINTPDF_BASE,
        headers={"Authorization": f"Bearer {LINTPDF_API_KEY}"},
        timeout=60,
    )

    while True:
        try:
            for job in get_pending_jobs(pace):
                pdf_data = pace.get(job["content_url"]).content
                result = submit_and_wait(lp, pdf_data, f"{job['id']}.pdf")
                update_pace(pace, job["id"], result)
                passed = result.get("summary", {}).get("passed", False)
                log.info("Pace job %s: %s", job["id"], "PASS" if passed else "FAIL")
        except Exception:
            log.exception("Error in polling loop")

        time.sleep(30)


if __name__ == "__main__":
    main()
```

> **Note:** EFI Pace API documentation is not publicly available. The endpoints shown above are illustrative patterns. Refer to your Pace REST API documentation or Connectivity Toolkit for exact endpoint URLs, authentication methods, and field names.

## Indirect Integration (JDF via Fiery)

EFI Pace integrates with Fiery digital front ends via JDF/JMF. Fiery JDF technology provides certified integration between Pace and Fiery-driven devices.

### Architecture

```
┌──────────┐  PaceConnect  ┌──────────┐  JDF/JMF  ┌──────────────┐  HTTP  ┌──────────┐
│  EFI     │──────────────→│  Fiery   │──────────→│  Prepress    │──────→│ LintPDF  │
│  Pace    │               │  DFE     │           │  Workflow    │       │ API      │
└──────────┘               └──────────┘           │  (AE/Switch) │       └──────────┘
                                                  └──────────────┘
```

### Setup

1. **Pace → Fiery:** Configure PaceConnect or JDF output from Pace to Fiery
2. **Fiery → Workflow Engine:** Fiery passes JDF + files to your prepress workflow engine
3. **Workflow Engine → LintPDF:** Configure the workflow engine to call LintPDF:
   - [Enfocus Switch integration](/docs/integrations-enfocus-switch)
   - [Esko Automation Engine integration](/docs/integrations-esko-ae)

### When to Use Each Path

| Criteria                                  | Direct    | Indirect (JDF/Fiery)     |
| ----------------------------------------- | --------- | ------------------------ |
| Already using Fiery + workflow engine     | —         | Preferred                |
| Want minimal dependencies                 | Preferred | —                        |
| Need workflow automation beyond preflight | —         | Preferred                |
| Pace Connectivity Toolkit available       | Preferred | —                        |
| Real-time status updates in Pace          | Preferred | Depends on JDF roundtrip |

## Tips

- **PaceConnect:** The PaceConnect functionality bridges MIS and prepress. It can trigger actions when job status changes, making it a natural trigger point for preflight.
- **Content file management:** Pace supports content file imports via PaceConnect, API, or Connectivity Toolkit. Use whichever method your installation supports.
- **Error handling:** Network failures between the middleware and either API should route to a retry queue, not silently fail.
