---
title: "Enfocus Switch Integration"
description: "Call LintPDF from Enfocus Switch flows using the HTTP Request element, Scripter, or webhooks."
section: "integrations"
order: 2
---

# Enfocus Switch Integration

> **Already running PitStop in Switch?** Send the PitStop XML report alongside the PDF in `preflight_source=external` mode — LintPDF consumes the findings, renders them in the viewer, and mints share/approval surfaces without re-checking. See [Importing from Enfocus PitStop](/docs/imports/vendors#enfocus-pitstop) and [External Preflight Imports](/docs/external-imports).

Enfocus Switch can call LintPDF as a preflight step in any flow. There are three integration methods:

1. **Switch Scripter** — Full control via JavaScript (recommended)
2. **HTTP Request flow element** — Built-in, no scripting required
3. **Webhook via Web Service Access Point** — Push results back to Switch

## Method 1: Switch Scripter (Recommended)

The Scripter flow element gives full control over the HTTP request, response parsing, and job routing. This example submits the incoming job file to LintPDF, polls for results, and routes the file to pass or fail.

### Scripter Configuration

Create a new Scripter element with:

- **Incoming connections:** One input from your flow
- **Outgoing connections:** Two outputs — one for pass, one for fail
- **Private data:** Add `LintPDF_JobId` and `LintPDF_Passed` fields

### Script: Entry Point

```javascript
// ----- LintPDF Preflight via Switch Scripter -----
// Submits the job file to LintPDF, polls for completion,
// and routes based on pass/fail.

var LINTPDF_API_KEY = "lpdf_your_api_key";
var LINTPDF_BASE_URL = "https://api.lintpdf.com";
var LINTPDF_PROFILE = "gwg-sheetfed";
var POLL_INTERVAL_SEC = 5;
var MAX_POLL_ATTEMPTS = 120; // 10 minutes at 5s intervals

function jobArrived(s, flowElement, job) {
  var filePath = job.getPath();

  // --- Step 1: Submit the PDF ---
  var httpClient = new HTTP(HTTP.SSL);
  httpClient.url = LINTPDF_BASE_URL + "/api/v1/jobs";
  httpClient.addHeader("Authorization", "Bearer " + LINTPDF_API_KEY);
  httpClient.setAttachedFile(filePath);

  // Add profile_id as a form field
  // Note: Switch Scripter sends the attached file as multipart/form-data.
  // The profile_id is passed as a query parameter or additional form field.
  httpClient.url =
    LINTPDF_BASE_URL + "/api/v1/jobs?profile_id=" + LINTPDF_PROFILE;

  httpClient.post();
  httpClient.waitForFinished(60);

  if (httpClient.finishedStatus !== HTTP.Ok || httpClient.statusCode !== 202) {
    s.log(1, "LintPDF submit failed. HTTP " + httpClient.statusCode);
    job.sendToData(1, job.getDataset()); // Route to fail
    return;
  }

  var submitResponse = JSON.parse(
    httpClient.getServerResponse().toString("UTF-8"),
  );
  var jobId = submitResponse.id;
  s.log(3, "LintPDF job submitted: " + jobId);

  // Store job ID in private data for reference
  job.setPrivateData("LintPDF_JobId", jobId);

  // --- Step 2: Poll for completion ---
  var attempts = 0;
  var status = "pending";
  var resultData = null;

  while (
    status !== "complete" &&
    status !== "failed" &&
    attempts < MAX_POLL_ATTEMPTS
  ) {
    s.sleep(POLL_INTERVAL_SEC);
    attempts++;

    var pollClient = new HTTP(HTTP.SSL);
    pollClient.url = LINTPDF_BASE_URL + "/api/v1/jobs/" + jobId;
    pollClient.addHeader("Authorization", "Bearer " + LINTPDF_API_KEY);
    pollClient.get();
    pollClient.waitForFinished(30);

    if (
      pollClient.finishedStatus === HTTP.Ok &&
      pollClient.statusCode === 200
    ) {
      resultData = JSON.parse(pollClient.getServerResponse().toString("UTF-8"));
      status = resultData.status;
    }
  }

  if (status !== "complete" || !resultData) {
    s.log(1, "LintPDF job did not complete. Status: " + status);
    job.sendToData(1, job.getDataset()); // Route to fail
    return;
  }

  // --- Step 3: Route based on results ---
  var passed = resultData.summary.passed;
  var errorCount = resultData.summary.error_count || 0;
  var warningCount = resultData.summary.warning_count || 0;
  var advisoryCount = resultData.summary.advisory_count || 0;

  s.log(
    3,
    "LintPDF result — Passed: " +
      passed +
      " | Error: " +
      errorCount +
      " | Warning: " +
      warningCount +
      " | Advisory: " +
      advisoryCount,
  );

  job.setPrivateData("LintPDF_Passed", passed ? "true" : "false");

  if (passed) {
    job.sendToData(2, job.getDataset()); // Route to pass output
  } else {
    job.sendToData(1, job.getDataset()); // Route to fail output
  }
}
```

### Flow Layout

```
[Input] → [Scripter: LintPDF Preflight] → (Pass) → [Next step]
                                         → (Fail) → [Hold / Notify]
```

## Method 2: HTTP Request Flow Element

For simpler setups, use the built-in HTTP Request element. This method is limited — it can submit the file but cannot easily poll for results or parse JSON responses. Best used with webhooks (Method 3).

### Configuration

1. Add an **HTTP Request** element to your flow
2. Set **Method** to `POST`
3. Set **URL** to `https://api.lintpdf.com/api/v1/jobs?profile_id=gwg-sheetfed`
4. Add header: `Authorization: Bearer lpdf_your_api_key`
5. Enable **Attach file** — this sends the incoming job file as the request body
6. The response contains the job ID for later retrieval

**Limitation:** The HTTP Request element cannot poll for completion. Pair it with a webhook (Method 3) or use the Scripter (Method 1) instead.

## Method 3: Webhook via Web Service Access Point

Instead of polling, configure LintPDF to push results back to Switch via a Web Service Access Point.

### Setup

1. **In Switch:** Add a Web Service Access Point to your flow. Note the URL it provides (e.g., `https://your-switch-server:port/ws/lintpdf-results`).

2. **In LintPDF:** Register the webhook:

```bash
curl -X POST https://api.lintpdf.com/api/v1/webhooks \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-switch-server:port/ws/lintpdf-results",
    "events": ["job.completed", "job.failed"]
  }'
```

3. **In Switch:** The Web Service Access Point receives the webhook payload as a JSON file. Use a Scripter or JSON processing element downstream to parse the results and route accordingly.

### Webhook Payload

LintPDF sends a POST with these headers:

- `X-LintPDF-Event: job.completed` (or `job.failed`)
- `X-LintPDF-Signature: sha256={hmac_hex_digest}`

The body contains the full job result including `summary.passed`, severity counts, and all findings.

## Data Flow Summary

```
┌──────────────┐    PDF file     ┌──────────────┐
│  Upstream     │───────────────→│  Switch       │
│  (ERP / MIS)  │                │  Scripter     │
└──────────────┘                └──────┬───────┘
                                       │ POST /api/v1/jobs
                                       ▼
                                ┌──────────────┐
                                │   LintPDF    │
                                │   API        │
                                └──────┬───────┘
                                       │ GET /api/v1/jobs/{id}
                                       ▼
                                ┌──────────────┐
                                │   Results    │
                                │   (pass/fail) │
                                └──────┬───────┘
                                       │
                          ┌────────────┴────────────┐
                          ▼                         ▼
                   ┌──────────┐              ┌──────────┐
                   │  Pass    │              │  Fail    │
                   │  Output  │              │  Output  │
                   └──────────┘              └──────────┘
```

## Tips

- **Profile selection:** Use Switch variables to dynamically select the LintPDF profile based on job metadata (e.g., `gwg-sheetfed` for offset, `gwg-digital` for digital).
- **Error handling:** Always check `httpClient.finishedStatus` and `httpClient.statusCode`. Network failures should route to a hold queue, not silently fail.
- **Metadata:** Store the LintPDF job ID in Switch private data or job metadata for traceability.
- **Rate limits:** If submitting many files, check the `X-RateLimit-Remaining` response header to avoid hitting limits.
