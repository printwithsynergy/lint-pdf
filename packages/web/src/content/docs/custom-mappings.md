---
title: "Custom Import Mappings"
description: "Teach LintPDF how to read your proprietary preflight XML or JSON without us shipping a new parser."
section: "preflight"
order: 23
---

# Custom Import Mappings

Custom mappings let you bring a proprietary preflight format — in-house tooling, a niche vendor, an older PitStop version with a quirky export — into LintPDF's external-import flow. You describe where each canonical finding field lives in your payload, save the mapping, and submit jobs with `mapping_id=<your-mapping-uuid>` instead of a built-in `external_format`.

Mappings are tenant-scoped, CRUD-managed, and live-previewable against a saved sample. Managing them requires the `branding:manage` permission.

## Mapping editor

Every mapping is editable at:

**https://app.lintpdf.com/dashboard/account/import-mappings**

The editor provides the following controls for each mapping:

- **Name** — operator-friendly label; shown in the submit-page picker.
- **Description** — free-form notes (vendor, version, owner).
- **Format** — `xml` or `json`.
- **Item selector** — the path to each finding element inside your payload.
- **Fields** — per-canonical-field selectors. Drag the row handle to reorder visually.
- **Severity map** — translate your tool's severity tokens (`HIGH`, `MEDIUM`, `INFO`…) into canonical `error`/`warning`/`advisory`.
- **Default severity** — fallback used when no severity map entry and no selector matches.
- **Source tool label** — rendered in the report header and viewer empty-state.
- **Sample payload** — paste or drop in a real report; the editor previews what findings come out.
- **Sample MIME** — the content type of the sample (auto-detected on drop).
- **Active** — inactive mappings are kept for historical audit but rejected on new submissions.

## Canonical fields

| Field | Required | What to map |
|---|---|---|
| `message` | Yes (implicitly — rows without a message selector produce no finding) | Human-readable description |
| `severity` | No (falls back to `default_severity`) | Your tool's severity/level |
| `page` | No | 1-indexed page number |
| `bbox` | No | Bounding box; see [BBox formats](#bbox-formats) |
| `check_id` | No | Your tool's check identifier — becomes `inspection_id` |
| `object_id` | No | Object name (image resource, font name) |
| `object_type` | No | `image` / `text` / `path` / `font` / `page` / `document` |
| `category` | No | Grouping key |
| `iso_clause` | No | ISO standard reference |

## XML selectors

The XML parser is namespace-insensitive — it matches on local names, so you don't need to declare prefixes. Supported selector grammar:

- **Element paths** — `Results/Error`, `root/Issues/Issue`, `//Hit` (the `//` form walks the whole tree).
- **Attributes** — prefix with `@`: `@level`, `@page`.
- **Nested text** — `Geometry/Box` extracts the text content of the `Box` child of `Geometry`.
- **Attributes on nested elements** — `Location/@page` reads the `page` attribute from a `Location` child.

### XML example — PitStop-lite

Input payload:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PreflightLog>
  <Issues>
    <Issue level="HIGH" page="2">
      <Description>Image resolution below 300 dpi</Description>
      <Location><Box>72 72 216 216</Box></Location>
    </Issue>
  </Issues>
</PreflightLog>
```

Mapping config:

```json
{
  "format": "xml",
  "item_selector": "Issues/Issue",
  "fields": {
    "severity": "@level",
    "message": "Description",
    "page": "@page",
    "bbox": "Location/Box"
  },
  "severity_map": {
    "high": "error",
    "medium": "warning",
    "low": "advisory",
    "info": "advisory"
  },
  "default_severity": "warning",
  "source_tool": "Acme Preflight 2.1"
}
```

## JSON selectors

JSON selectors use dotted paths with `[*]` to expand arrays.

- **Object paths** — `severity`, `loc.page`.
- **Array expansion** — `results[*].issues[*]` inside `item_selector` expands every issue across all results.
- **Array indexing** — `bbox[0]`, `bbox[1]` work if your bbox isn't a plain 4-element array.

### JSON example

Input payload:

```json
{
  "results": [{
    "issues": [
      {
        "sev": "HIGH",
        "text": "Font not embedded",
        "loc": { "page": 1 }
      }
    ]
  }]
}
```

Mapping config:

```json
{
  "format": "json",
  "item_selector": "results[*].issues[*]",
  "fields": {
    "severity": "sev",
    "message": "text",
    "page": "loc.page"
  },
  "severity_map": {
    "high": "error",
    "medium": "warning",
    "low": "advisory"
  },
  "default_severity": "warning",
  "source_tool": "Acme Preflight (JSON)"
}
```

## BBox formats

The bbox selector returns a string; the parser accepts any of:

- Space-separated: `"72 72 216 216"`.
- Comma-separated: `"72,72,216,216"`.
- Four-element JSON array (when the JSON parser emits an array): `[72, 72, 216, 216]`.

All are treated as `[x0, y0, x1, y1]` in PDF points, lower-left origin. Invalid bboxes are silently dropped and the finding still renders — just without a highlight box in the viewer.

## Severity mapping

Severity tokens from your tool pass through two stages:

1. **Exact lookup** — if `severity_map` (case-insensitive) has your token, we use the mapped value.
2. **Fuzzy fallback** — we recognise common synonyms (`error`/`fail`/`fatal`/`critical` → `error`; `warn`/`warning`/`caution` → `warning`; `info`/`notice`/`advisory` → `advisory`).
3. **Default** — if both miss, `default_severity` is used.

Set an explicit `severity_map` whenever your tool emits tokens outside the common English vocabulary (e.g., `SEV1`/`SEV2`/`SEV3`, `KRITISCH`, numeric codes).

## CRUD API

All endpoints require `Authorization: Bearer <key>` and the `branding:manage` permission.

### List

```bash
curl https://api.lintpdf.com/api/v1/tenant/import-mappings \
  -H "Authorization: Bearer lpdf_live_..."
```

Response:

```json
{
  "mappings": [
    {
      "id": "a12b3c4d-...",
      "name": "Acme PitStop-lite",
      "description": "In-house XML export from Acme Preflight 2.1",
      "format": "xml",
      "config": { "format": "xml", "item_selector": "Issues/Issue", "fields": { "...": "..." } },
      "sample_payload": "<PreflightLog>...</PreflightLog>",
      "sample_mime": "application/xml",
      "is_active": true,
      "created_at": "2026-04-12T14:30:00Z",
      "updated_at": "2026-04-12T14:30:00Z"
    }
  ]
}
```

### Create

```bash
curl -X POST https://api.lintpdf.com/api/v1/tenant/import-mappings \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d @my-mapping.json
```

Request body:

```json
{
  "name": "Acme PitStop-lite",
  "description": "In-house XML",
  "format": "xml",
  "config": {
    "format": "xml",
    "item_selector": "Issues/Issue",
    "fields": { "message": "Description", "severity": "@level", "page": "@page" },
    "severity_map": { "high": "error", "medium": "warning" },
    "default_severity": "warning",
    "source_tool": "Acme Preflight"
  },
  "sample_payload": "<PreflightLog>...</PreflightLog>",
  "sample_mime": "application/xml",
  "is_active": true
}
```

Response: `201 Created` with the full mapping row including its new UUID. `422` if `config` is syntactically invalid.

### Get / Update / Delete

```bash
# GET one
curl https://api.lintpdf.com/api/v1/tenant/import-mappings/a12b3c4d-... \
  -H "Authorization: Bearer lpdf_live_..."

# PUT (replace; all fields required)
curl -X PUT https://api.lintpdf.com/api/v1/tenant/import-mappings/a12b3c4d-... \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d @updated.json

# DELETE (soft-delete — sets is_active=false, preserves history)
curl -X DELETE https://api.lintpdf.com/api/v1/tenant/import-mappings/a12b3c4d-... \
  -H "Authorization: Bearer lpdf_live_..."
```

Soft-delete means past jobs that referenced this mapping keep their audit trail. You can reactivate a mapping by `PUT`ing with `is_active: true`.

### Preview

Dry-run the mapping against a saved sample (or an override payload) without persisting anything:

```bash
curl -X POST https://api.lintpdf.com/api/v1/tenant/import-mappings/a12b3c4d-.../preview \
  -H "Authorization: Bearer lpdf_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "config": { "format": "xml", "item_selector": "...", "fields": {"...": "..."} },
    "sample_payload": "<PreflightLog>...</PreflightLog>"
  }'
```

Response:

```json
{
  "ok": true,
  "findings_count": 5,
  "sample_findings": [
    { "severity": "error", "message": "Image resolution 144 dpi ...", "page_num": 2, "bbox": [72, 72, 216, 216], "inspection_id": "custom-acme", "object_id": null, "object_type": null, "category": null }
  ],
  "error": null
}
```

When the preview fails the response keeps HTTP 200 so the UI can render inline feedback — check `ok` and `error`:

```json
{ "ok": false, "findings_count": 0, "sample_findings": [], "error": "item_selector 'Issues/Issue' matched 0 elements" }
```

## Submitting with a mapping

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@acme-export.xml \
  -F preflight_source=external \
  -F mapping_id=a12b3c4d-...
```

Rules:

- `mapping_id` and `external_format` are mutually exclusive. Using a mapping implicitly means "custom" format; you'll get `422` if you send both.
- The mapping must be active (`is_active=true`) and owned by the tenant whose API key you're using. `403` otherwise; `422` if inactive.
- The resulting job's `external_format` is `"custom"` and `imported_source_metadata.mapping_id` records the mapping's UUID for audit.

## Tenant isolation

Every mapping is strictly scoped to the tenant that created it. Foreign mappings return `403` at every endpoint (GET, PUT, DELETE, preview, submit). Soft-deleted mappings are excluded from list and detail responses unless you've re-activated them.

## Drag-and-drop in the editor

Two DnD surfaces in the editor:

1. **Sample payload drop zone** — drop a `.xml` or `.json` file (under 5 MB) onto the sample area to load its contents, auto-fill the MIME type, and switch the format selector accordingly.
2. **Field row reordering** — grab the row handle on any mapping field to reorder. Row order is cosmetic only; mapping execution is field-name-based.

## Related

- [Preflight Modes](/docs/preflight-modes)
- [External Preflight Imports](/docs/external-imports)
- [LintPDF Native Import Schema](/docs/import-schema)
- [Importing from Enfocus PitStop](/docs/imports/vendors#enfocus-pitstop)
- [Importing from callas pdfToolbox](/docs/imports/vendors#callas-pdftoolbox)
- [Importing from Adobe Acrobat Preflight](/docs/imports/vendors#adobe-acrobat-preflight)
