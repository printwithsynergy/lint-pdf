---
title: "Viewer-Only Submissions"
description: "Submit a PDF with no preflight and still open it in the interactive viewer."
section: "preflight"
order: 24
---

# Viewer-Only Submissions

Viewer-only (minimal) mode submits a PDF without running any analyzer pipeline and without requiring an external preflight report. The job completes in under two seconds — we extract the pages, their geometry, and the document metadata, and the viewer opens immediately with navigation, zoom, page thumbnails, and download. Preflight tools in the viewer are rendered as **Load** affordances you can invoke individually.

## When to use minimal mode

- You're building a review or approval workflow where the stakeholder — not the operator — decides which inspections to run.
- You're embedding the LintPDF viewer in another product and want a fast open on files that may never need a full preflight pass.
- You want branded / anonymised / tokenized sharing of a PDF without burning a full engine run.
- You're triaging a large queue and want to preview files before committing compute to a full preflight.

## Submission

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F preflight_source=minimal \
  -F profile_id=lintpdf-default
```

You still supply `profile_id` — even though no analyzers run, the profile's viewer configuration (default zoom, DPI, TAC limit, toolbar layout) still applies. No `external_report` is required or accepted.

Response:

```json
{
  "job_id": "d4e5f6a7-...",
  "status": "pending",
  "message": "Job submitted successfully"
}
```

Jobs typically complete within 1–2 seconds. Poll `GET /api/v1/jobs/{job_id}` until `status=complete`.

## What the viewer shows

On a minimal-mode job the viewer config comes back with:

```json
{
  "preflight_source": "minimal",
  "capabilities": {
    "findings": false,
    "separations": false,
    "tac": false,
    "fonts": false,
    "images": false,
    "layers": true,
    "thumbnails": true,
    "metadata": true
  },
  "enable_findings_panel": false,
  "enable_separations": false,
  "enable_tac_heatmap": false,
  "enable_page_thumbnails": true,
  "enable_zoom": true,
  "enable_download": true,
  "...": "..."
}
```

Features that render immediately on every minimal-mode job:

- Page navigation, zoom (50–400%), page thumbnails.
- Media/crop/trim/bleed box overlay.
- Page rotation awareness.
- PDF download.
- Branded/anonymised viewer chrome and share-link generation.

## On-demand capability fill-in

The viewer's toolbar shows every tool your profile allows, with a **Load** button on tools whose capability is currently `false`. One click enqueues a targeted analyzer run and the tool activates when it completes — typically 3–10 seconds depending on file size and capability:

| Capability | Backing analyzer | Viewer tool unlocked |
|---|---|---|
| `findings` | Full engine pipeline | Findings panel (all 500+ checks) |
| `separations` | Spot-color analyzer | Ink channel viewer |
| `tac` | Ink-coverage analyzer | TAC heatmap overlay |
| `fonts` | Font analyzer | Font inspector |
| `images` | Image analyzer | Image inventory |

`layers` (PDF optional-content groups) is populated at extraction time when present in the PDF itself — it's not an on-demand fill-in.

See [Viewer Capabilities & On-Demand Fill-In](/docs/viewer-capabilities) for the full API and polling pattern.

## Cost and metering

A minimal-mode submission counts as **one file processed** against your plan. Each capability fill-in is counted separately, at roughly the same rate as one analyzer pass — typically cheaper than a full engine run. See [Pricing](/pricing) for tier limits and overage.

## The Viewer tier

For teams who always submit in minimal or external mode, the dedicated **Viewer tier** ($15 / month, 150 files / month) packages this workflow at a lower price point. The trade-off is a tighter feature envelope:

- `preflight_source=engine` is **not allowed** — engine-mode submissions return a `403 plan_upgrade_required` envelope. Submit in `minimal` or `external` only.
- On-demand capability fill-in is **not available** — the `POST /api/v1/viewer/jobs/{id}/capabilities/{capability}` endpoint 403s. The viewer shows read-only copies of whatever came in with your submission (minimal = pages + metadata; external = pages + imported findings).
- Viewer annotations are **off** — the annotation toolbar is hidden and the viewer ships read-only. Share-link tokens carry `allow_annotations=false` regardless of what was requested at mint time.
- Report downloads are **disabled** — `allowed_report_formats` is empty, so PDF / JSON / XML exports return 403. The only output of the tier is the interactive viewer share link.

Upgrade to **Starter** to unlock engine submissions, on-demand fill-in, annotations, and downloadable reports. The viewer config response (`GET /api/v1/viewer/jobs/{id}/config`) surfaces these gates as `capability_fillin_enabled`, `annotations_enabled`, and `allowed_report_formats` so frontends can render appropriate upgrade prompts instead of raw 403s.

## Share links and branding

Minimal-mode jobs work with share links and branding resolution exactly like engine- or external-mode jobs. You can:

- Generate a tokenized viewer/PDF share link via `POST /api/v1/jobs/{job_id}/reports`.
- Override branding per-request with `brand=anonymous`, `brand=lintpdf`, or `brand=<profile_uuid>`.
- Rely on the tenant default (anonymous-by-default for brokers; branded for direct customers).

Anonymous minimal-mode jobs still sanitize PDF metadata on the downloaded PDF and use neutral filenames. See [Branded, LintPDF-Default, and Anonymous Outputs](/docs/branding-and-anonymous).

## Related

- [Preflight Modes](/docs/preflight-modes)
- [Viewer Capabilities & On-Demand Fill-In](/docs/viewer-capabilities)
- [Share Links](/docs/share-links)
- [Branded, LintPDF-Default, and Anonymous Outputs](/docs/branding-and-anonymous)
