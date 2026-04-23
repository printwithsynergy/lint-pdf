---
title: "AI Accuracy Audit"
description: "Opt-in AI verification of engine findings — per-finding confirmed / disputed / needs_context verdicts."
section: "ai-features"
order: 80
---

# AI Accuracy Audit

Every preflight finding the engine produces is a claim about the PDF — "this font isn't embedded", "this overprint renders wrong on press", "this spot color isn't in the brand palette". **AI Accuracy Audit** is a second AI pass that reads the rendered PDF with a vision model and independently verifies each finding. The audit attaches a verdict to every finding:

| Status | Meaning |
|---|---|
| `confirmed` | The AI agrees — the issue is visible in the rendered pixels. |
| `disputed` | The AI disagrees — describe what you see instead. Engine got it wrong. |
| `needs_context` | Can't decide without a JDF sidecar / brand profile / customer spec. Re-submit with that context and the verdict changes. |
| `pending_retry` | Audit is still retrying after a transient Claude failure (async back-off). Retries run for up to 24 h in the background; no action needed. |

## Who gets it

**Growth**, **Scale**, and **Enterprise** plans by default, via the `audit` entry in the tenant's `ai_features` grant list. Admins can flip `audit` on or off for any tenant at `/dashboard/admin/tenants/[id]` without changing the plan. The resolver gates every call on `ai_enabled AND "audit" in ai_features` — both must be true.

## Where the verdict lives

Each finding in the `findings` array of the job response carries an optional `audit` object:

```json
{
  "inspection_id": "LPDF_OVER_001",
  "severity": "warning",
  "message": "Overprint active on non-CMYK color space 'CS3'...",
  "page_num": 1,
  "audit": {
    "status": "confirmed",
    "rationale": "Yellow splatter overprints the navy band; rendered preview matches.",
    "model": "claude-haiku-4-5",
    "at": "2026-04-23T18:05:34Z"
  }
}
```

Findings that were not audited carry `"audit": null` (or omit the field entirely). Reasons a finding isn't audited:

- Tenant doesn't have `ai_audit_enabled`.
- Job was submitted before the audit feature shipped.
- Modal endpoint returned an unrecognized status (the engine drops invalid verdicts to `null` rather than write bogus DB rows).

## Viewer chip

In the interactive viewer, every audited finding gets a small chip next to its severity dot:

- **green check** — `confirmed`
- **amber triangle** — `disputed` (hover for rationale)
- **grey info** — `needs_context`
- **red ✕** — `error`

Unaudited findings display no chip — the row doesn't change layout, so a tenant that switches plans doesn't see the viewer shift.

## Model

The customer audit runs on a Modal-hosted vision LLM (Qwen2-VL-7B-Instruct on A10G). The model is chosen for strong JSON-output discipline and low latency; it doesn't read customer text off the page, only the rendered preview + finding metadata.

A separate **internal** audit pass on Claude Opus 4.7 (much more accurate, far more expensive) is used by LintPDF engineering to red-team the engine against a golden PDF corpus. Internal audit results never reach customer dashboards.

## Pricing

Rolled into the Scale / Enterprise AI credit budget. Each audited finding consumes one credit; a typical 50-finding preflight runs you ~50 credits against your monthly allotment.

## Caveats

- The AI audit is a **second opinion**, not a replacement. Disputed verdicts are a signal to triage, not an authoritative "the engine was wrong".
- Audits are best-effort: a Modal cold-start timeout leaves the verdict field `null` so the viewer renders nothing, rather than writing an `error` row that would need retry handling on your side.
- Findings with no `page_num` (document-level findings like PDF version errors) get audited against the full page set; the model judges them off finding text + page previews.

## Re-auditing a completed job

Need to refresh verdicts without resubmitting the PDF? `POST /api/v1/jobs/{job_id}/audit:rerun` runs the customer auditor against the findings already on the job and updates the `audit` field on each row. Useful when:

- The audit model has been tuned since the original run.
- Modal was down during the original preflight — the `audit` fields are `null` and you want them filled in now that the endpoint is healthy.
- A pilot tenant just had `ai_audit_enabled` flipped on and wants to backfill verdicts on its historical jobs.

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs/<job-id>/audit:rerun \
  -H "Authorization: Bearer lpdf_live_..."
```

```json
{
  "job_id": "48276823-644c-419f-bb07-f3649c9f8368",
  "findings_updated": 275,
  "model": "modal:qwen2-vl-7b"
}
```

The rerun endpoint deliberately bypasses the `ai_audit_enabled` entitlement check — flipping a pilot tenant on for a window and then refreshing their back-catalogue is the whole point. It still requires `LINTPDF_AUDIT_MODAL_URL` to be configured server-side; without that the endpoint returns `findings_updated: 0` with no error (the job is left as-is).

- `200 OK` → `{job_id, findings_updated, model}`
- `404 Not Found` → job doesn't exist or isn't in your tenant
- `409 Conflict` → job isn't in `complete` state (can't audit a pending / failed job)
- `502 Bad Gateway` → Modal auditor itself errored (timeout, 5xx, parse failure). Retry after the Modal dashboard shows a healthy endpoint.

Super-admins have a separate mirror at `POST /api/v1/admin/jobs/{id}/audit-rerun` (hyphen, not colon) that auths with `X-Admin-Key` and works across tenants — also reachable from the Re-audit button in the admin jobs drawer.

## Manually overriding a verdict

Sometimes the AI gets one wrong — "disputes" a finding that's actually correct, or "confirms" a false positive. Super-admins can flip the verdict directly:

```bash
curl -X PATCH https://api.lintpdf.com/api/v1/admin/findings/<finding-id>/audit \
  -H "X-Admin-Key: $LINTPDF_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed", "rationale": "Confirmed by hand — AI missed the embedded font reference on page 3."}'
```

Manual overrides set `audit_model` to `manual:<admin-email>` so they're visually distinct from AI verdicts in the viewer + audit reports. There's no UI surface for this yet; use the API directly.

## Related

- [Preflight Modes](/docs/preflight-modes)
- [AI Presets](/docs/api-reference)
- [Scale plan](/pricing)
