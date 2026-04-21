---
title: "Importing from Enfocus PitStop"
description: "Feed Enfocus PitStop preflight reports into LintPDF's viewer and reports."
section: "preflight"
order: 26
---

# Importing from Enfocus PitStop

Enfocus PitStop Server and PitStop Pro emit XML reports that LintPDF parses directly. Submit the PDF and the PitStop XML together; the findings show up in the viewer, reports, and share links with page numbers and bounding boxes intact.

## Export from PitStop

### PitStop Pro (Acrobat plugin)

1. Run preflight against your profile.
2. With the preflight results panel open, choose **Reports → Save as XML…**.
3. LintPDF accepts the PitStop XML schema; no transformation needed.

### PitStop Server (hot folder / command line)

Configure your hot folder's reporting action to emit XML. In the Hot Folder configuration:

- **Report type**: XML
- **Report placement**: success and error folders
- **Include geometry**: yes (this gives LintPDF the bounding boxes)

CLI users can pipe PitStop Server's stdout XML directly.

## Submission

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@pitstop-report.xml \
  -F preflight_source=external \
  -F external_format=pitstop_xml \
  -F profile_id=lintpdf-default
```

Or let auto-detect pick:

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@pitstop-report.xml \
  -F preflight_source=external \
  -F profile_id=lintpdf-default
```

## What we map

| PitStop element | LintPDF field | Notes |
|---|---|---|
| `<Error>` / `<Warning>` / `<Info>` / `<Hit>` | One finding per element | All four element types are recognised. |
| `<CheckID>` | `inspection_id` | Preserved as `pitstop:<check-id>` so repeated findings collate across jobs. |
| `<Description>` | `message` | Text content. |
| `<Page>` | `page_num` | 1-indexed. |
| `<BBox>` | `bbox` | Space- or comma-separated `x0 y0 x1 y1` in PDF points. |
| `<Category>` (if present) | `category` | Grouping. |
| Element name | `severity` | `Error` → `error`, `Warning` → `warning`, `Info` / `Hit` → `advisory`. |
| `<Object>` | `object_id` / `object_type` | PDF resource name + classifier. |
| Header `<Profile>` | `source.profile` | Which PitStop profile ran. |
| Header `<PitStopVersion>` | `source.version` | PitStop build. |

## Known limitations

- **PitStop groups**: nested `<Group>` elements are flattened into individual findings. The group label is preserved as `category`.
- **Hit vs Error taxonomy**: `<Hit>` elements map to `advisory` by default because PitStop itself makes no strong severity promise on Hits. Override with a custom mapping if your shop uses Hits for blocking issues.
- **Geometry in non-standard units**: PitStop occasionally emits bboxes in millimeters in exotic profiles; LintPDF assumes PDF points. If geometry appears wildly misaligned in the viewer, validate the profile's unit setting.

## Customizing the mapping

If your PitStop export is highly customized — renamed elements, non-English severity tokens, extra nested structure — and the built-in parser doesn't cover it, build a [Custom Import Mapping](/docs/custom-mappings). Point `item_selector` at `//Hit` or `//Error` as appropriate and map each `<CheckID>`, `<Description>`, `<Page>`, `<BBox>` element explicitly.

## Sample payload

A trimmed but realistic PitStop XML report is available at [`/examples/pitstop-report.xml`](https://lintpdf.com/examples/pitstop-report.xml).

## Related

- [External Preflight Imports](/docs/external-imports)
- [Custom Import Mappings](/docs/custom-mappings)
- [Importing from callas pdfToolbox](/docs/importing-from-callas)
- [Importing from Adobe Acrobat Preflight](/docs/importing-from-acrobat)
