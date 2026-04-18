---
title: "Approval Verdicts"
description: "Mark a job approved, rejected, or needs-review from the viewer or API."
section: "viewer-workflow"
order: 42
---

# Approval Verdicts

Every LintPDF job carries a verdict row that records the human approval state. Verdicts are surfaced in the viewer toolbar and share-link landing pages when `verdict_mode` on the active viewer config is `auto` or `manual`.

## Verdict states

| State | Meaning |
|---|---|
| `pending` | Default. No reviewer has taken an action yet. |
| `approved` | Reviewer has approved the job. The viewer surfaces a green banner. |
| `rejected` | Reviewer has rejected the job. The viewer surfaces a red banner and suggested action. |
| `needs_review` | Reviewer has escalated. The viewer surfaces an amber banner. |

## Read a verdict

```bash
curl https://api.lintpdf.com/api/v1/viewer/jobs/{job_id}/verdict \
  -H "Authorization: Bearer lpdf_live_..."
```

Response:

```json
{
  "job_id": "d4e5f6a7-...",
  "status": "approved",
  "reviewer_name": "Alex Chen",
  "reviewed_at": "2026-04-12T15:22:11Z",
  "comments": "Looks good. Proceed to print."
}
```

On public share links, use the unauthenticated path:

```bash
curl https://api.lintpdf.com/api/v1/viewer/public/{token}/verdict
```

## Set a verdict

```bash
curl -X POST https://api.lintpdf.com/api/v1/viewer/jobs/{job_id}/verdict \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "comments": "Looks good. Proceed to print."
  }'
```

Request fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | `"approved"` \| `"rejected"` \| `"needs_review"` | Yes | Target state. |
| `comments` | string \| `null` | No | Free-form reviewer notes. Up to 4096 characters. |

Reviewer name is derived from the API key's associated user (for dashboard calls) or can be overridden with a `reviewer_name` field on integration calls.

## Verdict mode

The viewer config carries `verdict_mode`:

- `"auto"` — verdict defaults from finding severity (no errors + no warnings → approved; any errors → rejected; otherwise needs-review).
- `"manual"` — verdict starts `pending` and only changes via explicit `POST /verdict` calls.
- `"disabled"` — verdict is hidden entirely from the viewer.

Set the default for a tenant via the profile editor or override per viewer config call with `?verdict_mode=manual`.

## Approval chains

For multi-stage review workflows (designer → QA → print manager), use Approval Templates (`/api/v1/approvals/templates`) which compose multiple verdicts into a chain. Each stage carries its own verdict and can gate the next. Approval chains are out of scope for this page; see the [API Reference](/docs/api-reference) for the full `/api/v1/approvals/*` surface.

## Related

- [Universal Job State API](/docs/job-state) — fetch verdict + approval chain with notes + annotations with comments in one call.
- [Viewer Capabilities & On-Demand Fill-In](/docs/viewer-capabilities)
- [Share Links](/docs/share-links)
- [API Reference](/docs/api-reference)
