---
title: "Trials panel"
description: "Review, preflight, and send reports for /try-it submissions."
---

# Trial submissions

**Path:** `/dashboard/admin/trials` · **Who:** Super admin · **Scope:** Cross-tenant (trials live in the `__trial__` pseudo-tenant)

Inbox for every file submitted through the public `/try-it` page on the marketing site. Use this to turn prospect uploads into branded reports that sales can send out.

## What you see

- Top banner: `Auto-submit: ON/OFF` — reflects `LINTPDF_TRIAL_AUTO_SUBMIT` env. When OFF, submissions sit in `pending` until you click Run; when ON, preflight kicks off automatically.
- Paginated list: submission name, email, company, file count, status, created-at.
- Click a row → detail drawer: per-file ClamAV scan result, download link, preflight job id (once submitted), and "Send report" button.

## Actions

| Action | API | Notes |
|---|---|---|
| Download uploaded PDF | `GET /api/v1/admin/trials/{id}/files/{file_id}/download` | Streams the raw file for inspection. |
| Run preflight | `POST /api/v1/admin/trials/{id}/files/{file_id}/preflight` | Queues the job under the `__trial__` tenant with profile `lintpdf-default` (or `LINTPDF_TRIAL_AUTO_SUBMIT_PROFILE_ID`). Returns 409 if one's already running. |
| Send report email | `POST /api/v1/admin/trials/{id}/send-report` | Sends the branded HTML + PDF report to the submitter's email. No automation — always a manual click. |
| Edit admin notes | `PATCH /api/v1/admin/trials/{id}` | Free-text notes for internal hand-off. |

## Gotchas

- `LINTPDF_TRIAL_AUTO_SUBMIT=true` only auto-runs preflight; it **never** auto-sends reports. That's by design — you want a human to read the report before it goes to a prospect.
- If ClamAV flagged a file (`scan_clean=false`), Run will refuse. Download + inspect manually.
- Every trial submission notifies `LINTPDF_ADMIN_EMAIL`; if that's unset, notifications are silently dropped.

## Related

- [Trial / Try-It Page](../../start/getting-started) docs cover the public flow.
