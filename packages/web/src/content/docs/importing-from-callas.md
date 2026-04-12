---
title: "Importing from callas pdfToolbox"
description: "Feed callas pdfToolbox preflight reports (JSON or XML) into LintPDF's viewer and reports."
section: "preflight"
order: 27
---

# Importing from callas pdfToolbox

callas pdfToolbox Server and Desktop can emit preflight reports in either JSON or XML. LintPDF parses both variants directly. Submit the PDF alongside the callas report and the findings render in the viewer, reports, and share links with their original severity, page, and geometry intact.

## Export from pdfToolbox

### Desktop

1. Run preflight against your profile.
2. In the results pane, **Reports → Save report as JSON** (or **XML**).
3. Both formats carry the same data — pick whichever your downstream tooling already handles. JSON is slightly smaller.

### Server (CLI / hot folder)

```bash
pdfToolbox --profile=Sheetfed.kfpx \
  --report-json=report.json \
  brochure.pdf
```

For XML, substitute `--report-xml=report.xml`. Ensure the profile emits geometry — in pdfToolbox Server's Web UI, check **Report Options → Include object geometry**.

## Submission

### JSON variant

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@callas-report.json \
  -F preflight_source=external \
  -F external_format=callas_json \
  -F profile_id=lintpdf-default
```

### XML variant

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@callas-report.xml \
  -F preflight_source=external \
  -F external_format=callas_xml \
  -F profile_id=lintpdf-default
```

Or omit `external_format` for auto-detect. LintPDF recognises callas JSON by its top-level `profile`/`hits` keys and callas XML by its `<Report>` root element.

## What we map (both variants)

| callas field | LintPDF field | Notes |
|---|---|---|
| `hits[].severity` / `<Hit severity="...">` | `severity` | Maps `Error`/`Warning`/`Info` to `error`/`warning`/`advisory`. |
| `hits[].message` / `<Hit><Message>` | `message` | Full text. |
| `hits[].page` / `<Hit><Page>` | `page_num` | 1-indexed. |
| `hits[].geometry.bbox` / `<Hit><Geometry>` | `bbox` | `[x0, y0, x1, y1]` PDF points. |
| `hits[].checkId` / `<Hit id="...">` | `inspection_id` | Preserved as `callas:<id>`. |
| `hits[].object` / `<Hit><Object>` | `object_id` + `object_type` | Resource + classifier. |
| `hits[].category` | `category` | Grouping. |
| `profile` / `<Profile>` | `source.profile` | Profile name. |
| `version` / `<PdfToolboxVersion>` | `source.version` | Build string. |

## Severity normalization

callas uses consistent English severity tokens (`Error`, `Warning`, `Info`); LintPDF's fuzzy normalizer handles them directly without needing a custom severity map. Non-English exports — typical on German or Japanese profiles — need a [custom mapping](/docs/custom-mappings) with an explicit `severity_map`.

## Known limitations

- **Fixups**: pdfToolbox reports that include fixups (auto-corrections applied) are parsed, but only the reported hits are surfaced. LintPDF does not modify the PDF; see our [detection-only philosophy](/about).
- **Profile-specific categories**: callas' category taxonomy varies by profile. We preserve the category string verbatim; if you're rolling up findings across multiple callas profiles, expect vocabulary drift.

## Sample payloads

- JSON: [`docs/examples/callas-report.json`](https://github.com/thinkneverland/lint-pdf/blob/main/docs/examples/callas-report.json)
- XML: [`docs/examples/callas-report.xml`](https://github.com/thinkneverland/lint-pdf/blob/main/docs/examples/callas-report.xml)

## Related

- [External Preflight Imports](/docs/external-imports)
- [Custom Import Mappings](/docs/custom-mappings)
- [Importing from Enfocus PitStop](/docs/importing-from-pitstop)
- [Importing from Adobe Acrobat Preflight](/docs/importing-from-acrobat)
