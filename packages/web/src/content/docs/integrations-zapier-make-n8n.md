---
title: "Zapier, Make & n8n Integration"
description: "Connect LintPDF to Zapier, Make (Integromat), and n8n using webhooks and HTTP modules."
section: "integrations"
order: 10
---

# Zapier, Make & n8n Integration

LintPDF works with any webhook-capable automation platform. This guide covers Zapier, Make (formerly Integromat), and n8n.

The pattern is the same across all three:

1. **Trigger** on a new file (from cloud storage, email, form upload, etc.)
2. **Submit** the file to LintPDF via HTTP POST
3. **Wait** for results (webhook or poll)
4. **Route** based on pass/fail
5. **Notify** or take action

## General Flow

```
[Trigger: New file arrives]
    ↓
[HTTP POST: Submit to LintPDF /api/v1/jobs]
    ↓
[Wait for results]
    ├── Option A: Webhook (recommended)
    └── Option B: Delay + Poll
    ↓
[Parse results: summary.passed, severity counts]
    ↓
[Branch: passed == true?]
    ├── Yes → [Move file to "approved" folder / notify]
    └── No  → [Move file to "review" folder / notify with findings]
```

## Option A: Webhook-Driven (Recommended)

Webhooks eliminate polling. LintPDF pushes results to your automation platform when the job completes.

### Setup

#### 1. Create a Webhook Trigger

In your automation platform, create a new workflow with a **Webhook** trigger. Copy the webhook URL provided.

**Example URLs:**
- Zapier: `https://hooks.zapier.com/hooks/catch/123456/abcdef/`
- Make: `https://hook.us1.make.com/abcdefghijk`
- n8n: `https://your-n8n.com/webhook/lintpdf-results`

#### 2. Register the Webhook with LintPDF

```bash
curl -X POST https://api.lintpdf.com/api/v1/webhooks \
  -H "Authorization: Bearer lpdf_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://hooks.zapier.com/hooks/catch/123456/abcdef/",
    "events": ["job.completed", "job.failed"]
  }'
```

#### 3. Create a Submit Workflow

Create a separate workflow (or the first part of the same workflow) that submits files:

**Trigger:** New file in Google Drive / Dropbox / S3 / email attachment / form upload

**HTTP Action:**
- **Method:** POST
- **URL:** `https://api.lintpdf.com/api/v1/jobs`
- **Headers:** `Authorization: Bearer lpdf_your_api_key`
- **Body type:** Form-data / Multipart
- **Fields:**
  - `file`: The file content from the trigger
  - `profile_id`: `gwg-sheetfed` (or your preferred profile)

#### 4. Process Webhook Results

When the job completes, LintPDF sends a POST to your webhook URL with:

- **Headers:**
  - `X-LintPDF-Event`: `job.completed` or `job.failed`
  - `X-LintPDF-Signature`: HMAC-SHA256 signature for verification
- **Body:** Full job result with summary and findings

**Parse the JSON body** to extract:
- `summary.passed` — boolean
- `summary.aground_count` — critical issue count
- `summary.squall_count` — warning count
- `summary.advisory_count` — informational count
- `findings` — array of individual issues

#### 5. Branch and Act

Add a **Filter** or **Router** step:

- **If passed:** Move file to "approved" folder, update your system, send confirmation
- **If failed:** Move file to "review" folder, send email/Slack with finding details

## Option B: Delay + Poll

If you prefer not to set up webhooks, use a delay + poll pattern.

### Steps

#### 1. Submit (Same as Above)

HTTP POST to `https://api.lintpdf.com/api/v1/jobs` with file and profile_id.

**Save the job ID** from the response: `response.id`

#### 2. Delay

Add a **Delay** step: wait 15–30 seconds (adjust based on typical file size).

#### 3. Poll

HTTP GET to `https://api.lintpdf.com/api/v1/jobs/{job_id}` with auth header.

**Check `status` field:**
- If `complete` or `failed` → proceed to step 4
- If `pending` or `processing` → loop back to delay (add a max retry count to avoid infinite loops)

#### 4. Parse and Route

Same as webhook approach — parse `summary.passed` and route accordingly.

## Platform-Specific Notes

### Zapier

- Use the **Webhooks by Zapier** trigger for receiving LintPDF results
- Use the **Code by Zapier** step (JavaScript or Python) if you need to parse complex JSON
- The **Paths** feature handles pass/fail branching
- **File handling:** Use "File" fields in the HTTP action for multipart upload

### Make (Integromat)

- Use the **HTTP** module with "Make a request" for submission
- Use the **Webhooks** module for receiving results
- The **Router** module handles pass/fail branching
- **File handling:** Make handles multipart/form-data natively in the HTTP module
- Use the **JSON** module to parse response bodies

### n8n

- Use the **HTTP Request** node for submission and polling
- Use the **Webhook** node for receiving results
- The **IF** node handles pass/fail branching
- **File handling:** n8n passes binary data between nodes natively
- Self-hosted n8n instances need a publicly accessible URL for webhooks (use a tunnel or reverse proxy during development)

## Complete Zapier Example

```
1. Trigger: New File in Google Drive (folder: "Incoming Artwork")
2. Action: Webhooks by Zapier → POST
   - URL: https://api.lintpdf.com/api/v1/jobs
   - Headers: Authorization = Bearer lpdf_your_api_key
   - Data: profile_id = gwg-sheetfed
   - File: {{file_content}} from step 1
3. Action: Delay → Wait 20 seconds
4. Action: Webhooks by Zapier → GET
   - URL: https://api.lintpdf.com/api/v1/jobs/{{step2_id}}
   - Headers: Authorization = Bearer lpdf_your_api_key
5. Path A (passed = true):
   - Move file to "Approved" folder in Google Drive
   - Send Slack message: "✓ {filename} passed preflight"
6. Path B (passed = false):
   - Move file to "Needs Review" folder
   - Send email with finding details
```

## Tips

- **Webhook verification:** LintPDF signs webhook payloads with HMAC-SHA256. Verify the `X-LintPDF-Signature` header in production to ensure requests come from LintPDF.
- **File size limits:** Automation platforms may limit file sizes for HTTP uploads. Check your platform's limits. For large files, consider using the [Hot Folder](/docs/integrations-hot-folder) approach instead.
- **Rate limits:** LintPDF has per-plan rate limits. If you're processing many files, add delays between submissions or upgrade your plan.
- **Error handling:** Always handle HTTP errors. Use retry logic for 5xx errors and respect 429 (rate limit) responses.
- **Profile selection:** Use a variable or lookup table to dynamically select the LintPDF profile based on the file source, customer, or job type.
