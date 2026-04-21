---
title: "LintPDF Native Import Schema"
description: "Canonical JSON schema for submitting third-party preflight findings to LintPDF."
section: "preflight"
order: 22
---

# LintPDF Native Import Schema (v1)

The LintPDF native import schema is the canonical JSON shape that any preflight tool can emit to hand findings to LintPDF without us shipping a per-vendor parser. If you control the tool on the upstream side — your own in-house preflight service, a custom script, a proprietary SaaS — emit this shape and submit with `external_format=lintpdf_json`. No translation layer, no custom mapping to maintain.

The authoritative JSON Schema (2020-12) is published at:

- **Machine-readable**: [`import-schema.json`](https://lintpdf.com/schema/import-schema.json)
- **`$id`**: `https://lintpdf.com/schemas/import/v1.json`

This page is the human-readable companion. Field definitions are authoritative in the JSON Schema file — when the two differ, the schema file wins.

## Minimum-viable payload

The only required field is `findings`. Everything else is optional metadata that enriches the viewer and reports.

```json
{
  "findings": [
    {
      "severity": "error",
      "message": "Image resolution 144 dpi is below the 300 dpi threshold",
      "page_num": 2
    }
  ]
}
```

Submit:

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@minimal.json \
  -F preflight_source=external \
  -F external_format=lintpdf_json
```

## Full-fidelity payload

```json
{
  "schema_version": "1",
  "source": {
    "tool": "Acme Preflight",
    "version": "3.2.1",
    "profile": "PDF/X-4 Sheetfed"
  },
  "capabilities": {
    "findings": true,
    "separations": false,
    "tac": false,
    "fonts": true,
    "images": true,
    "layers": false
  },
  "findings": [
    {
      "inspection_id": "img-lowres",
      "severity": "error",
      "message": "Image resolution 144 dpi is below the 300 dpi threshold",
      "page_num": 2,
      "bbox": [72, 72, 216, 216],
      "object_id": "Im42",
      "object_type": "image",
      "category": "images",
      "iso_clause": null,
      "details": {
        "resolution_dpi": 144,
        "threshold_dpi": 300,
        "color_space": "DeviceCMYK"
      }
    },
    {
      "inspection_id": "font-noembed",
      "severity": "warning",
      "message": "Font Helvetica-Bold is not embedded",
      "page_num": 1,
      "object_id": "Helvetica-Bold",
      "object_type": "font",
      "category": "fonts"
    }
  ]
}
```

## Field reference

### Top level

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | No | Currently always `"1"`. Reserved for future versions. |
| `source` | object | No | Provenance — tool name, version, profile. Surfaced in the viewer empty-state. |
| `capabilities` | object | No | Boolean flags that gate viewer tools. Unknown keys are ignored. |
| `findings` | array | **Yes** | One or more finding objects (see below). Empty array means "clean". |

### `source`

Free-form metadata. Stored verbatim on the job and rendered in the viewer's findings panel and report header.

| Field | Type | Description |
|---|---|---|
| `tool` | string | Human-readable producer name. Example: `"Enfocus PitStop"`. |
| `version` | string | Tool version string. Example: `"2024.1"`. |
| `profile` | string | Preflight profile the tool ran. Example: `"PDF/X-4"`. |

Additional string/number/boolean fields are preserved and shown verbatim.

### `capabilities`

Each flag declares whether your report authoritatively enumerates that capability. Flags set to `false` become **Load** affordances in the viewer — a single click fills them via a targeted analyzer run (except `layers`, which is not fillable on demand).

| Flag | Fillable on demand | What it covers |
|---|---|---|
| `findings` | Yes (triggers a full engine pass) | The finding enumeration. Almost always `true` on imports. |
| `separations` | Yes (spot-color analyzer) | Spot/process ink channels. |
| `tac` | Yes (ink-coverage analyzer) | Total-area-coverage heatmap. |
| `fonts` | Yes (font analyzer) | Embedded fonts + subsetting state. |
| `images` | Yes (image analyzer) | Image resolution + color-space inventory. |
| `layers` | **No** | PDF optional-content groups (OCGs). If your report doesn't enumerate them, the viewer hides the layers panel. |

Unknown keys are ignored — safe to include tool-specific flags.

### `findings[]`

Each entry is a single finding. `severity` and `message` are required; everything else is optional.

| Field | Type | Required | Description |
|---|---|---|---|
| `severity` | `"error"` \| `"warning"` \| `"advisory"` | Yes | Canonical severity. Map from your tool's severity taxonomy before emitting. |
| `message` | string | Yes | Human-readable description rendered in the findings panel and report. |
| `page_num` | int | No | 1-indexed page number. Omit for document-level findings. |
| `bbox` | `[x0, y0, x1, y1]` | No | PDF points, lower-left origin. Drives viewer highlight boxes. |
| `inspection_id` | string | No | Stable identifier for the check. Used to collate recurring findings across jobs. |
| `object_id` | string | No | Resource name of the target object. Example: `"Im42"` for an image, `"Helvetica-Bold"` for a font. |
| `object_type` | `"image"` \| `"text"` \| `"path"` \| `"font"` \| `"page"` \| `"document"` | No | Classifier for what the finding targets. |
| `category` | string | No | Grouping key. Examples: `"color"`, `"fonts"`, `"images"`, `"geometry"`. |
| `iso_clause` | string | No | ISO standard reference when applicable. Example: `"PDF/X-4:2010 6.2.2"`. |
| `details` | object | No | Free-form key/value metadata rendered in the finding detail panel. |

## Validation

The published schema validates with any [draft 2020-12 validator](https://json-schema.org/draft/2020-12/schema). A common local check:

```bash
npx ajv-cli validate \
  -s docs/import-schema.json \
  -d your-report.json \
  --spec=draft2020
```

Validation failures at submit time return `422 Unprocessable Entity` with a parser error message pointing at the offending field.

## Versioning

The `$id` is versioned in the URL (`import/v1.json`). Breaking changes will publish a new `v2` schema with a different `$id`. The `schema_version` top-level field will gain `"2"` as an allowed value at that time; until then, submit with `schema_version: "1"` or omit entirely.

## Related

- [Preflight Modes](/docs/preflight-modes)
- [External Preflight Imports](/docs/external-imports)
- [Custom Import Mappings](/docs/custom-mappings) — for proprietary shapes that don't emit this schema.
- [Viewer Capabilities & On-Demand Fill-In](/docs/viewer-capabilities)
