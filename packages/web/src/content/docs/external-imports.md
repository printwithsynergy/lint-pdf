---
title: "External Preflight Imports"
description: "Submit a PDF plus your existing PitStop, callas, Acrobat, or LintPDF-native preflight report and open the results in the interactive viewer."
section: "preflight"
order: 21
---

# External Preflight Imports

External imports let you keep running preflight in your tool of choice — Enfocus PitStop, callas pdfToolbox, Adobe Acrobat Preflight, or anything that emits XML/JSON — while using LintPDF as the viewer, reporting, and distribution surface. You upload the PDF plus your report; we parse the report into LintPDF findings and render them identically to engine-produced findings.

## When to use it

- You've already invested in a preflight toolchain and don't want to rerun the same checks in LintPDF.
- You want the interactive viewer, branded PDF/HTML reports, share links, and approval workflows layered on top of findings your operators trust.
- You want to consolidate reporting across teams that use different preflight tools.

## Viewer tier customers

Most external-import workloads land naturally on the **Viewer tier** ($15 / month, 150 files / month) — you already have your preflight findings, you just need a hosted viewer + share link. On the Viewer tier:

- `preflight_source=external` submissions are allowed and behave exactly as documented below.
- `preflight_source=minimal` is also allowed, for jobs where you want the viewer with nothing else.
- `preflight_source=engine` returns `403 plan_upgrade_required` — upgrade to Starter if you want to run our 600+ check pipeline.
- Report downloads (PDF / JSON / XML) are disabled. The output is the interactive viewer share link only.
- Annotations are off.

See [Pricing](/pricing) for the full tier matrix.

## Supported formats

| `external_format` | Tool | Notes |
|---|---|---|
| `pitstop_xml` | Enfocus PitStop | Handles `<Hit>`, `<Error>`, `<Warning>`, `<Info>` with page + bbox. |
| `callas_json` | callas pdfToolbox | JSON variant. |
| `callas_xml` | callas pdfToolbox | XML variant. |
| `acrobat_xml` | Adobe Acrobat Preflight | XML export (Acrobat Pro DC "Save As XML"). |
| `lintpdf_json` | Any tool | Canonical LintPDF-native schema — see [Import Schema](/docs/import-schema). |

Omit `external_format` entirely to let LintPDF auto-detect based on the file's root element or JSON shape. Auto-detect is reliable on all shipped formats; set `external_format` explicitly only if auto-detect mis-classifies a borderline payload.

If your tool doesn't emit any of the above, use a [Custom Import Mapping](/docs/custom-mappings) — a tenant-defined parser that translates proprietary XML or JSON into LintPDF findings with no parser-level change on our side.

## Submission

The PDF is required. The report is required unless you're using a custom mapping. Both ride on the same `multipart/form-data` request to `POST /api/v1/jobs`.

### PitStop XML

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@pitstop-report.xml \
  -F preflight_source=external \
  -F external_format=pitstop_xml \
  -F profile_id=lintpdf-default
```

### callas JSON

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@callas-report.json \
  -F preflight_source=external \
  -F external_format=callas_json \
  -F profile_id=lintpdf-default
```

### callas XML

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@callas-report.xml \
  -F preflight_source=external \
  -F external_format=callas_xml \
  -F profile_id=lintpdf-default
```

### Adobe Acrobat XML

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@acrobat-preflight.xml \
  -F preflight_source=external \
  -F external_format=acrobat_xml \
  -F profile_id=lintpdf-default
```

### LintPDF native JSON

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@findings.json \
  -F preflight_source=external \
  -F external_format=lintpdf_json \
  -F profile_id=lintpdf-default
```

Auto-detect variant (omit `external_format`):

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@report.xml \
  -F preflight_source=external \
  -F profile_id=lintpdf-default
```

## Response

Every submission returns `202 Accepted` with a job ID:

```json
{
  "job_id": "7c9a4b0e-5d3a-4f2b-92e1-1a3c0b9d8e4f",
  "status": "pending",
  "message": "Job submitted successfully"
}
```

Poll `GET /api/v1/jobs/{job_id}` until `status=complete`, then open the interactive viewer at `https://app.lintpdf.com/dashboard/preflight/{job_id}/viewer` or generate a share link via `POST /api/v1/jobs/{job_id}/reports`. External-mode jobs complete in under three seconds in almost every case because no analyzers run.

## Findings taxonomy

Each parsed finding lands in the job with:

- **`severity`** — `error`, `warning`, or `advisory` (your tool's severity is normalised with a fuzzy map, then overridden by any explicit `severity_map` on custom mappings).
- **`message`** — the human-readable description your tool emitted.
- **`page_num`** — 1-indexed page number.
- **`bbox`** — `[x0, y0, x1, y1]` in PDF points when the report carries geometry; used to draw highlights in the viewer.
- **`inspection_id`** — a stable identifier derived from your tool's check ID so repeated findings on different jobs collate correctly in the dashboard.
- **`source`** — `external:pitstop`, `external:callas`, `external:acrobat`, `external:lintpdf_json`, or `external:custom:<mapping-id>` for a custom mapping.
- **`category`**, **`object_id`**, **`object_type`**, **`iso_clause`** — optional metadata preserved when the upstream report carries them.

## Capabilities on external jobs

External reports usually carry findings but rarely carry separations, total-area-coverage (TAC), font-embedding detail, or image-resolution maps. LintPDF marks those capabilities `false` on the job and surfaces them in the viewer as **Load** buttons. One click fills the capability by running just the responsible analyzer — the job's findings remain authoritative (we don't second-guess your tool) but the viewer gains separations preview, TAC heatmap, or full font/image inspection on demand.

See [Viewer Capabilities & On-Demand Fill-In](/docs/viewer-capabilities) for the full capability registry.

## Error reference

| Status | Reason |
|---|---|
| `400` | PDF is corrupt, encrypted, or not a PDF. |
| `403` | Custom profile or brand profile not owned by your tenant. |
| `409` | `external_report` provided but `preflight_source` is `engine`, or missing when `preflight_source=external` and no `mapping_id`. |
| `413` | `external_report` exceeds the 50 MB cap. |
| `422` | `preflight_source` is not one of `engine`/`external`/`minimal`; or `external_format` is not in the supported enum; or `external_report` is empty; or the report parser rejected the payload (wrong format vs declared `external_format`). |
| `429` | Plan rate limit exceeded. |

## Worked examples

Copy-pasteable samples are hosted on this site:

- [`pitstop-report.xml`](https://lintpdf.com/examples/pitstop-report.xml)
- [`callas-report.json`](https://lintpdf.com/examples/callas-report.json), [`callas-report.xml`](https://lintpdf.com/examples/callas-report.xml)
- [`acrobat-report.xml`](https://lintpdf.com/examples/acrobat-report.xml)
- [`lintpdf-native.json`](https://lintpdf.com/examples/lintpdf-native.json)
- [`submit-external.sh`](https://lintpdf.com/examples/submit-external.sh)

## Related

- [Preflight Modes](/docs/preflight-modes)
- [LintPDF Native Import Schema](/docs/import-schema)
- [Custom Import Mappings](/docs/custom-mappings)
- [Importing from Enfocus PitStop](/docs/imports/vendors#enfocus-pitstop)
- [Importing from callas pdfToolbox](/docs/imports/vendors#callas-pdftoolbox)
- [Importing from Adobe Acrobat Preflight](/docs/imports/vendors#adobe-acrobat-preflight)
- [Viewer Capabilities & On-Demand Fill-In](/docs/viewer-capabilities)
