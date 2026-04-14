---
title: "Share Links"
description: "Mint tokenized share links for viewer and PDF reports with per-link branding and expiry."
section: "branding"
order: 31
---

# Share Links

Share links let you hand a preflight report or interactive viewer to a stakeholder who doesn't have a LintPDF account. Every link is a tokenized, unauthenticated URL that resolves to a specific job with its branding, detail level, and summary configuration frozen at mint time.

## What you can share

| Surface | URL shape | Access |
|---|---|---|
| HTML report | `https://reports.lintpdf.com/r/{token}` | Unauthenticated; token-gated. |
| PDF report | `https://reports.lintpdf.com/r/{token}.pdf[?download=1]` | Same. `download=1` forces attachment disposition. |
| JSON report | `https://reports.lintpdf.com/r/{token}.json` | Same. LintPDF v1 schema; re-importable as `external_format=lintpdf_json`. |
| XML report | `https://reports.lintpdf.com/r/{token}.xml` | Same. Same field taxonomy as JSON, in the `urn:lintpdf:preflight:1.0` namespace. |
| Public viewer | `https://app.lintpdf.com/view/{token}` (proxies to `/api/v1/viewer/public/{token}/*`) | Same. Interactive viewer with separations, TAC, layers, verdict — all gated by the job's captured capabilities. |

## Mint a share link

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs/{job_id}/reports \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "formats": ["html", "pdf"],
    "expiry_days": 30,
    "email_to": null,
    "branding": null,
    "detail_level": "standard",
    "summary_page": "prepend"
  }'
```

### Request fields

| Field | Type | Default | Description |
|---|---|---|---|
| `formats` | array of `"html"` \| `"pdf"` \| `"json"` \| `"xml"` \| `"annotated_pdf"` \| `"annotated_pdf_markup"` | `["html", "pdf"]` | Which formats to mint. Each returns its own token. `annotated_pdf` and `annotated_pdf_markup` are silently skipped if their inputs are missing (original PDF unreadable, or zero annotations, respectively); the other formats in the same request still mint. |
| `expiry_days` | int \| `null` | Plan default (7 for Free, 30 for Starter, 90 for Growth+, `null`/never for Enterprise) | Token lifetime. `null` = no expiry. |
| `email_to` | string \| `null` | `null` | When set, the share link is emailed to this address on mint. The email envelope honors the job's brand resolution (anonymous sends from `no-reply@reports.lintpdf.com`). |
| `branding` | object \| `null` | Job/tenant default | Inline branding override. Accepts `name`, `logo_url`, `primary_color`, `accent_color`, `hide_footer`. Use with care — prefer BrandProfile references. |
| `detail_level` | `"executive"` \| `"standard"` \| `"comprehensive"` | `"standard"` | Summary density. Executive = 1-page overview, Standard = per-category, Comprehensive = every finding with detail. |
| `summary_page` | `"prepend"` \| `"only"` \| `"off"` | `"prepend"` | `prepend`: summary page + full findings. `only`: summary page, no detailed findings. `off`: findings only. |

### Response

```json
{
  "reports": [
    {
      "format": "html",
      "url": "https://reports.lintpdf.com/r/tok_9a8b7c6d5e4f",
      "token": "tok_9a8b7c6d5e4f",
      "expires_at": "2026-05-12T14:30:00Z"
    },
    {
      "format": "pdf",
      "url": "https://reports.lintpdf.com/r/tok_9a8b7c6d5e4f.pdf",
      "token": "tok_9a8b7c6d5e4f",
      "expires_at": "2026-05-12T14:30:00Z"
    }
  ]
}
```

## Branding immutability

The brand resolution at mint time is **frozen for the life of the token**. The `ReportToken` row records:

- `brand_mode` — `anonymous` / `lintpdf` / `profile`
- `brand_profile_id` — non-null only for `profile`

If your tenant later flips its default branding, previously-minted links are unaffected. This is deliberate: distributors on the receiving end of anonymous broker links need the guarantee.

To re-brand an existing share link, revoke the old token and mint a new one.

## List existing share links

```bash
curl https://api.lintpdf.com/api/v1/jobs/{job_id}/reports \
  -H "Authorization: Bearer lpdf_live_..."
```

Response:

```json
{
  "reports": [
    {
      "token": "tok_9a8b7c6d5e4f",
      "format": "html",
      "expires_at": "2026-05-12T14:30:00Z",
      "created_at": "2026-04-12T14:30:00Z",
      "accessed_count": 3
    }
  ]
}
```

`accessed_count` increments on every token resolution (including bots and link previews — treat as approximate).

## Revoke

```bash
curl -X DELETE https://api.lintpdf.com/api/v1/jobs/{job_id}/reports/{token} \
  -H "Authorization: Bearer lpdf_live_..."
```

Revocation is immediate. Any subsequent token resolution returns `410 Gone`. The token string is permanently retired — re-generating the same token is not possible.

## Programmatic token lookup

For integrations that want to resolve a token without needing an API key (e.g., a receiving system that only has the token):

```bash
# Job metadata for the token
curl https://api.lintpdf.com/api/v1/reports/tokens/{token}
```

Response:

```json
{
  "job_id": "d4e5f6a7-...",
  "tenant_id": "7c9a4b0e-...",
  "file_name": "brochure.pdf",
  "email_required": false
}
```

```bash
# Findings for the token (shape identical to authenticated /jobs/{id}.findings)
curl https://api.lintpdf.com/api/v1/reports/tokens/{token}/findings
```

`404` on unknown token, `410` on expired. No authentication header on either.

## Public viewer surface

The public viewer exposes the same endpoints as the authenticated viewer, with `/api/v1/viewer/public/{token}/` replacing `/api/v1/viewer/jobs/{job_id}/`:

- `GET /pages`
- `GET /pages/{n}/tile?dpi=`
- `GET /pages/{n}/info`
- `GET /separations`
- `GET /pages/{n}/channel/{name}?dpi=`
- `GET /pages/{n}/tac-heatmap?dpi=&tac_limit=`
- `GET /pages/{n}/tac-heatmap/runs?dpi=&tac_limit=` (per-text-run mean TAC metadata for tooltip overlays)
- `GET /config` (returns branding captured at mint time)
- `GET /pages/{n}/sample?x=&y=&dpi=` (RGB color picker)
- `GET /pages/{n}/densitometer?x=&y=&dpi=&tac_limit=` (per-channel CMYK + spot ink readings)
- `GET /layers`
- `GET /verdict`

None of these require authentication. The token itself is the authorization.

## Markup, comments, and email fan-out

When the issuing tenant mints a share link with `allow_annotations=true`, the recipient can draw markup (rectangles, circles, arrows, freehand strokes, sticky-note pins) directly on the interactive viewer. Writes require an `X-Visitor-Email` header so every markup row carries an audit trail — the viewer prompts once per session and remembers the answer in `localStorage`.

Threaded comments on a note are enabled under the same `allow_annotations` flag. Each comment post triggers an email fan-out to:

1. The annotation's original author (dashboard writer or earlier share-link visitor).
2. Every earlier distinct commenter on the same thread.
3. The commenter themselves is excluded so nobody gets their own echo.

Emails include a deep-link fragment (`#ann=<annotation_id>`) that scrolls the receiving viewer to the referenced markup and auto-opens its thread panel. The deep link points at the share-link URL for public writers and at the authenticated dashboard URL for tenant users.

### Bake-to-PDF

Once the markup phase is done, call the mint endpoint with `formats: ["annotated_pdf_markup"]` to get a PDF copy of the original with the reviewer's markup stamped on each page plus an appendix that resolves numbered note pins to their bodies and full comment threads. This is independent of `annotated_pdf`, which stamps preflight findings (not reviewer markup).

## Expiry semantics

- Expired tokens return `410 Gone` with no retry hint.
- There's no auto-renewal. Mint a fresh token when you need continued access.
- Plan default expiry is applied when `expiry_days` is omitted; pass an explicit value to override (up to your plan's cap; `null` works only on Enterprise).

## Access counting and auditing

Each token resolution increments `accessed_count` and writes an audit row with timestamp, IP hash, and user agent. The row is accessible via the dashboard at `Account → Share Links → Audit`.

## Related

- [Branded, LintPDF-Default, and Anonymous Outputs](/docs/branding-and-anonymous)
- [Custom Domains](/docs/custom-domains)
- [Report Formats](/docs/report-formats)
