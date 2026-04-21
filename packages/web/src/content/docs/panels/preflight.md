---
title: "Preflight"
description: "Upload a PDF from the browser and see the report live."
section: "panels"
order: 4
---

# Preflight

**Path:** `/dashboard/preflight` · **Who:** Any signed-in tenant user

Drag-and-drop preflight from the browser — the fastest way to sanity-check a file without wiring up the API.

## What you see

- Drop zone (or file picker) at the top.
- Profile picker — pick a system profile (`lintpdf-default`, `press-ready`, etc.) or one of your tenant's custom profiles.
- AI toggle — on/off + preset picker when enabled. Shows credit cost estimate before you submit.
- Recent uploads from this session stay visible for quick re-run.

## Actions

| Action | API | Notes |
|---|---|---|
| Upload + run | `POST /api/v1/jobs` (multipart) | Accepts PDF only. Max size = tenant's `max_file_size_mb` (default 1 GB). |
| Re-run with different profile | Resubmits the same file | Re-consumes one file from the quota. |
| Open report | Links to `reports.<your-domain>/r/<token>` | Respects your share-link expiry setting. |
| Download JSON | Same report token with `.json` suffix | |

## Gotchas

- **Uploads stream.** A 500 MB file against a 10 MB tenant cap rejects with 413 within milliseconds — you won't wait for the whole upload.
- **Encrypted PDFs** (password-protected) return 422 at ingest. Remove the password upstream.
- **AI toggle consumes credits at submit time**, not when the job completes. If the job fails, the credits are refunded automatically.

## Related

- [Getting started](../getting-started) — first-preflight walkthrough via curl
- [Reports](./reports) — where completed jobs land
- [Rulesets](./rulesets) — pick or author a custom profile
