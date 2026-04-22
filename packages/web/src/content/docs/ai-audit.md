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
| `error` | The audit call failed (Modal timeout, rate limit). Retry the job. |

## Who gets it

**Scale** and **Enterprise** plans only, via the `ai_audit_enabled` entitlement. No configuration required on the tenant side once the plan tier allows it — audit runs automatically after every preflight.

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
    "model": "modal:qwen2-vl-7b",
    "at": "2026-04-22T18:05:34Z"
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

## Related

- [Preflight Modes](/docs/preflight-modes)
- [AI Presets](/docs/api-reference)
- [Scale plan](/pricing)
