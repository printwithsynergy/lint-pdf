---
title: "Esko Automation Engine Integration"
description: "Preflight files in Esko Automation Engine using the Interact with Web Service task and SmartNames."
section: "integrations"
order: 3
---

# Esko Automation Engine Integration

> **Already preflighting in Esko?** If AE's preflight task produces a structured report (XML or JSON), feed it into LintPDF in `preflight_source=external` mode. Use a built-in parser (callas, PitStop) or define a [Custom Import Mapping](/docs/custom-mappings) for Esko's internal schema. The PDF and its findings end up in LintPDF's viewer with no re-check cost.

Esko Automation Engine (AE) can call LintPDF as a preflight step using the **Interact with Web Service** task. Results are captured into SmartNames for downstream routing.

## Integration Architecture

```
┌──────────┐   JDF + files   ┌──────────────┐   HTTP POST    ┌──────────┐
│  ERP /   │────────────────→│  Esko AE     │──────────────→│ LintPDF  │
│  MIS     │                 │  Workflow    │               │ API      │
└──────────┘                 └──────┬───────┘               └────┬─────┘
                                    │                            │
                                    │◄───── HTTP response ───────┘
                                    │
                              ┌─────┴──────┐
                              │ Map Data / │
                              │ SmartNames │
                              └─────┬──────┘
                                    │
                          ┌─────────┴─────────┐
                          ▼                   ▼
                     [Pass route]        [Fail route]
```

## Step-by-Step Setup

### Step 1: Submit the PDF

Add an **Interact with Web Service** task to your workflow.

**Configuration:**

- **URL:** `https://api.lintpdf.com/api/v1/jobs`
- **Method:** POST
- **Headers:**
  - `Authorization: Bearer lpdf_your_api_key`
- **Body:** The input file (multipart upload)
- **Additional fields:**
  - `profile_id`: `gwg-sheetfed` (or use a SmartName for dynamic selection)

**Response handling:** The task returns a JSON response. Capture the job ID from the response for the next step.

> **Note:** If the Interact with Web Service task does not support `multipart/form-data` file uploads natively, use a **Run Script** task with a Python or curl command instead:
>
> ```bash
> curl -s -X POST "https://api.lintpdf.com/api/v1/jobs" \
>   -H "Authorization: Bearer lpdf_your_api_key" \
>   -F "file=@[File]" \
>   -F "profile_id=gwg-sheetfed"
> ```
>
> Replace `[File]` with the appropriate AE SmartName for the input file path. This is a known consideration — test with your AE version to confirm which method works.

### Step 2: Poll for Results (XML Format Recommended)

Add a second **Interact with Web Service** task to poll for results. Request XML format for easier processing with AE's built-in XML tools.

**Configuration:**

- **URL:** `https://api.lintpdf.com/api/v1/jobs/{job_id}?format=xml`
- **Method:** GET
- **Headers:**
  - `Authorization: Bearer lpdf_your_api_key`

Replace `{job_id}` with the SmartName captured from Step 1.

**Polling logic:** Use a **Router** task with a condition:

- If response `status` is `complete` or `failed` → proceed to Step 3
- Otherwise → wait (use a **Wait** task with 5-second delay) → loop back to poll

### Step 3: Map Data to SmartNames

Use the **Map Data** task to extract values from the XML response into SmartNames.

**SmartName mappings:**

| SmartName               | XPath                         |
| ----------------------- | ----------------------------- |
| `LintPDF_Passed`        | `/job/summary/passed`         |
| `LintPDF_ErrorCount`    | `/job/summary/error_count`    |
| `LintPDF_WarningCount`  | `/job/summary/warning_count`  |
| `LintPDF_AdvisoryCount` | `/job/summary/advisory_count` |
| `LintPDF_TotalFindings` | `/job/summary/total_findings` |

### Step 4: Route Based on Results

Add a **Router** task after the Map Data step:

- **Pass condition:** `[LintPDF_Passed]` equals `true`
  - Route to next production step (impose, proof, RIP)
- **Fail condition:** `[LintPDF_Passed]` equals `false`
  - Route to reject/hold queue
  - Optionally trigger a notification task with finding details

### Example Workflow

```
[Folder Access Point]
    │
    ▼
[Interact with Web Service: Submit to LintPDF]
    │
    ▼
[Wait: 5 seconds]
    │
    ▼
[Interact with Web Service: Poll for Results (XML)]
    │
    ├──→ (status != complete) → [Loop back to Wait]
    │
    ▼
[Map Data: Extract SmartNames]
    │
    ▼
[Router]
    ├──→ (passed = true)  → [Continue workflow]
    └──→ (passed = false) → [Hold / Notify / Reject]
```

## Alternative: Run Script Task

If the Interact with Web Service task is insufficient for your needs, use a **Run Script** task with Python:

```python
#!/usr/bin/env python3
"""AE Run Script: Submit PDF to LintPDF and output results."""

import json
import sys
import time
import urllib.request
import urllib.parse

API_KEY = "lpdf_your_api_key"
BASE_URL = "https://api.lintpdf.com"
PROFILE = "gwg-sheetfed"
POLL_INTERVAL = 5
MAX_WAIT = 600  # 10 minutes

# The input file path is passed as an argument by AE
pdf_path = sys.argv[1]

# --- Submit ---
import subprocess
result = subprocess.run([
    "curl", "-s", "-X", "POST",
    f"{BASE_URL}/api/v1/jobs",
    "-H", f"Authorization: Bearer {API_KEY}",
    "-F", f"file=@{pdf_path}",
    "-F", f"profile_id={PROFILE}",
], capture_output=True, text=True)

submit_data = json.loads(result.stdout)
job_id = submit_data["id"]

# --- Poll ---
elapsed = 0
while elapsed < MAX_WAIT:
    time.sleep(POLL_INTERVAL)
    elapsed += POLL_INTERVAL

    result = subprocess.run([
        "curl", "-s",
        f"{BASE_URL}/api/v1/jobs/{job_id}",
        "-H", f"Authorization: Bearer {API_KEY}",
    ], capture_output=True, text=True)

    job_data = json.loads(result.stdout)
    if job_data["status"] in ("complete", "failed"):
        break

# --- Output ---
if job_data["status"] == "complete":
    summary = job_data.get("summary", {})
    passed = summary.get("passed", False)

    # Write result to a sidecar file for AE to pick up
    output_path = pdf_path + ".lintpdf.json"
    with open(output_path, "w") as f:
        json.dump({
            "job_id": job_id,
            "passed": passed,
            "error_count": summary.get("error_count", 0),
            "warning_count": summary.get("warning_count", 0),
            "advisory_count": summary.get("advisory_count", 0),
        }, f, indent=2)

    # Exit code signals pass/fail to AE
    sys.exit(0 if passed else 1)
else:
    sys.exit(2)  # Error / timeout
```

Configure the Router after the Run Script task to check the exit code:

- Exit 0 → pass
- Exit 1 → fail (preflight issues found)
- Exit 2 → error (timeout or API failure)

## Access Points

AE supports several Access Points for triggering workflows:

- **Folder Access Point** — Monitor a directory for new files (most common for ERP integration)
- **Web Service Access Point** — Receive HTTP requests (useful for webhook-driven flows)
- **FTP Access Point** — Monitor an FTP location
- **Email Access Point** — Process email attachments

For ERP integration, the typical pattern is: ERP drops files into a folder monitored by an AE Folder Access Point, which triggers the preflight workflow.

## Tips

- **XML over JSON:** AE's Map Data and Split XML tasks work natively with XML. Request XML format from LintPDF (`?format=xml`) for easier data extraction.
- **SmartNames:** Use SmartNames to make the workflow configurable — store API key, profile ID, and polling intervals as workflow parameters.
- **Notifications:** Use AE's notification tasks to alert operators when files fail preflight.
- **Batch processing:** AE handles batching natively. Each file in the Access Point triggers an independent workflow instance.
