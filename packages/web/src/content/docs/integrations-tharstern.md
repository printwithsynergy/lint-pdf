---
title: "Tharstern Integration"
description: "Integrate LintPDF with Tharstern MIS via Esko Automation Engine or direct web services."
section: "integrations"
order: 8
---

# Tharstern Integration

Tharstern is a print MIS built on SQL and web services. LintPDF integrates primarily through an **indirect path** via Esko Automation Engine, with a potential direct path through Tharstern's web services architecture.

## Indirect Integration (via Esko AE)

Tharstern has documented integrations with Esko Automation Engine and Heidelberg Prinect. The recommended integration path routes through AE.

### Architecture

```
┌────────────┐   Job data    ┌──────────────┐   HTTP POST   ┌──────────┐
│  Tharstern │──────────────→│  Esko AE     │─────────────→│ LintPDF  │
│  MIS       │               │  Workflow    │              │ API      │
│            │◄──────────────│              │◄─────────────│          │
│            │   Status      │              │   Results    │          │
└────────────┘               └──────────────┘              └──────────┘
```

### Setup

1. **Tharstern → Esko AE:** Configure Tharstern to send job data and artwork files to Esko AE. This typically uses folder-based or API-based handoff depending on your Tharstern configuration.

2. **Esko AE → LintPDF:** Configure AE to call LintPDF as a preflight step. See [Esko Automation Engine integration](/docs/integrations-esko-ae) for complete setup instructions.

3. **Results → Tharstern:** AE reports preflight results back through the job status channel. Pass/fail status and finding counts are available for display in Tharstern.

## Direct Integration (Web Services)

Tharstern's architecture is described as SQL and web services based, which suggests direct integration is technically possible. However, specific API documentation is not publicly available.

### Pattern

If Tharstern exposes web service endpoints for job data and file access, a middleware script can bridge the two systems:

```python
"""
Tharstern → LintPDF middleware pattern.

Note: Tharstern API specifics are not publicly documented.
Adjust endpoints per your Tharstern web services documentation.
"""

import httpx
import time

THARSTERN_BASE = "https://your-tharstern-instance.com/api"
LINTPDF_BASE = "https://api.lintpdf.com"
LINTPDF_API_KEY = "lpdf_your_api_key"
LINTPDF_PROFILE = "gwg-sheetfed"


def preflight_file(lp: httpx.Client, pdf_data: bytes, filename: str) -> dict:
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
```

> **Note:** Tharstern's web services architecture suggests direct integration is feasible for developers with access to the system. Contact Tharstern support for API documentation and integration guidance.

## Recommendation

For most Tharstern installations, the **indirect path through Esko AE** is recommended:

- It leverages Tharstern's existing AE integration
- No custom middleware to build or maintain
- AE handles the workflow orchestration, retry logic, and reporting
- Preflight becomes one step in a larger prepress workflow

Use the direct path only if you need preflight results in Tharstern before the job reaches the prepress workflow, or if you don't use a prepress workflow engine.
