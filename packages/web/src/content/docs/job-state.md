---
title: "Universal Job State API"
description: "Retrieve preflight results, approval chain, annotations + comments, verdict, and report links for a job in one call."
section: "api"
order: 36
---

# Universal Job State API

`GET /api/v1/jobs/{job_id}/state` returns the fully-stitched state of a preflight job in one call. Use it when you need everything a dashboard or audit exporter would display — preflight findings, every minted report link, the approval chain with per-step notes, the manual verdict, and every viewer annotation with its comment thread embedded.

## Why this exists

The individual retrieval endpoints (`GET /jobs/{id}`, `GET /jobs/{id}/approval-chain`, `GET /viewer/jobs/{id}/verdict`, `GET /viewer/jobs/{id}/annotations`, `GET .../{id}/comments`) still work exactly as before, but assembling "the full picture of job X" from them required **3+ round trips and an N+1 fan-out for comments** (one comments request per annotation). `/state` does it in one call with a single pair of JOINs.

## Auth

Tenant API key via `Authorization: Bearer <lpdf_...>`. Share-link visitors should use the public mirror at `GET /api/v1/viewer/public/{token}/state` — same shape minus the `reports` section (listing other share-link tokens for the same job from a single token would leak sibling shares).

## Request

```sh
curl -sS "https://api.lintpdf.com/api/v1/jobs/${JOB_ID}/state" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}"
```

Optional `?include=` query param filters the response to a subset of sections. Unknown keys return `422`. The core `job` block is always included.

| Include key | Section |
|---|---|
| `reports` | List of every minted report token, with `allow_annotations` + `require_visitor_email` metadata. |
| `approval_chain` | Attached approval chain, `null` if none. Includes per-step `notes`. |
| `verdict` | Manual verdict + aggregated approver notes + auto-passed flag. |
| `annotations` | Every viewer annotation with its `comments: []` thread embedded inline. |

Default (no `include=`) returns every section.

## Response shape

See [`docs/examples/job-state-response.json`](https://github.com/thinkneverland/lint-pdf/blob/main/docs/examples/job-state-response.json) for a runnable example. The top-level envelope is:

```json
{
  "job": { "...JobResponse...": "..." },
  "reports": [
    {
      "format": "annotated_pdf",
      "url": "https://reports.lintpdf.com/r/...",
      "token": "...",
      "expires_at": "2026-05-17T21:33:49+00:00",
      "allow_annotations": false,
      "require_visitor_email": null
    }
  ],
  "approval_chain": {
    "id": "...",
    "status": "approved",
    "current_step": 0,
    "step_history": [
      {
        "step_index": 0,
        "step_name": "Print ops",
        "approver_email": "ops@example.com",
        "decision": "approved",
        "notes": "Looks great, ship it.",
        "decided_at": "2026-04-17T22:10:00+00:00"
      }
    ]
  },
  "verdict": {
    "verdict": "approved",
    "auto_passed": true,
    "verdict_by": "ops@example.com",
    "verdict_at": "2026-04-17T22:10:00+00:00",
    "notes": "Print ops: Looks great, ship it."
  },
  "annotations": {
    "total": 1,
    "by_page": { "1": 1 },
    "items": [
      {
        "id": "...",
        "page_num": 1,
        "kind": "rect",
        "geometry": { "x": 10, "y": 10, "w": 100, "h": 50 },
        "color": "#dc2626",
        "text": "Fix the bleed",
        "author_email": "reviewer@example.com",
        "comments": [
          {
            "id": "...",
            "annotation_id": "...",
            "author_email": "reviewer@example.com",
            "body": "Will do by EOD."
          }
        ]
      }
    ]
  }
}
```

A section that was filtered out (e.g. `include=verdict` removes `reports`) is returned as `null`. A section that's intrinsically empty (no approval chain attached, no annotations drawn) is also `null` for `approval_chain` or an empty-shaped object for `annotations` (`total: 0`, `items: []`).

## Annotations without the full digest

When you only need annotations + comments, use the lighter-weight variant that was added alongside `/state`:

```sh
curl -sS "https://api.lintpdf.com/api/v1/viewer/jobs/${JOB_ID}/annotations?include=comments" \
  -H "Authorization: Bearer ${LINTPDF_API_KEY}"
```

Without the `include=` param the response is unchanged (back-compat): a flat `list[AnnotationResponse]`. With `include=comments`, each item carries an extra `comments: []` field. Same single-JOIN query under the hood — no N+1.

## Errors

| Status | Meaning |
|---|---|
| `404` | Job not found, or not owned by the caller's tenant. |
| `422` | `include=` contains a key other than `reports`, `approval_chain`, `verdict`, `annotations`. |

## Related

- [Approval Verdicts](/docs/viewer-verdict)
- [Share Links](/docs/share-links)
- [Viewer Capabilities](/docs/viewer-capabilities)
