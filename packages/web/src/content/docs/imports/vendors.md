---
title: "Importing from PitStop, callas & Acrobat"
description: "Feed vendor preflight reports straight into LintPDF — one page, three vendors, same flow."
section: "imports"
order: 3
---

# Importing from PitStop, callas & Acrobat

Enfocus PitStop, callas pdfToolbox, and Adobe Acrobat all emit preflight reports LintPDF parses natively. Submit the PDF alongside the vendor report and the findings show up in the viewer, reports, and share links with severity, page numbers, and geometry intact.

The three flows are almost identical — this page covers all of them in one place.

## Enfocus PitStop

PitStop Server and PitStop Pro emit XML reports.

### Export from PitStop

**PitStop Pro (Acrobat plugin):**

1. Run preflight against your profile.
2. With the results panel open, choose **Reports → Save as XML…**.
3. LintPDF accepts the PitStop XML schema — no transformation needed.

**PitStop Server (hot folder / CLI):**

Configure the hot folder's reporting action to emit XML:
- **Report type:** XML
- **Report placement:** success and error folders
- **Include geometry:** yes (gives LintPDF the bounding boxes)

CLI users can pipe PitStop Server's stdout XML directly.

### Submit

```sh
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@pitstop-report.xml \
  -F preflight_source=external \
  -F external_format=pitstop_xml \
  -F profile_id=lintpdf-default
```

Or omit `external_format` and let auto-detect pick it.

### Mapping

| PitStop element | LintPDF field | Notes |
|---|---|---|
| `<Error>` / `<Warning>` / `<Info>` / `<Hit>` | One finding per element | All four element types are recognised. |
| `<CheckID>` | `inspection_id` | Preserved as `pitstop:<check-id>`. |
| `<Description>` | `message` | Text content. |
| `<Page>` | `page_num` | 1-indexed. |
| `<BBox>` | `bbox` | Space- or comma-separated `x0 y0 x1 y1` in PDF points. |
| `<Category>` | `category` | Grouping. |
| Element name | `severity` | `Error`→`error`, `Warning`→`warning`, `Info`/`Hit`→`advisory`. |
| `<Object>` | `object_id` / `object_type` | PDF resource name + classifier. |
| Header `<Profile>` | `source.profile` | Which PitStop profile ran. |
| Header `<PitStopVersion>` | `source.version` | PitStop build. |

### PitStop limitations

- **Groups** — nested `<Group>` elements are flattened into individual findings; the group label is preserved as `category`.
- **Hit vs Error taxonomy** — `<Hit>` maps to `advisory` by default; override with a [custom mapping](./schema-and-mappings) if your shop uses Hits for blocking issues.
- **Non-standard units** — LintPDF assumes PDF points. If bboxes look wildly misaligned, validate the profile's unit setting.

A trimmed but realistic sample: [`/examples/pitstop-report.xml`](https://lintpdf.com/examples/pitstop-report.xml).

## callas pdfToolbox

pdfToolbox Server and Desktop emit reports in **both JSON and XML** — pick whichever your downstream tooling already handles.

### Export from pdfToolbox

**Desktop:**

1. Run preflight.
2. In the results pane, **Reports → Save report as JSON** (or XML).

**Server (CLI / hot folder):**

```sh
pdfToolbox --profile=Sheetfed.kfpx \
  --report-json=report.json \
  brochure.pdf
```

For XML, substitute `--report-xml=report.xml`. Ensure the profile emits geometry — in pdfToolbox Server's Web UI, check **Report Options → Include object geometry**.

### Submit

**JSON variant:**

```sh
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@callas-report.json \
  -F preflight_source=external \
  -F external_format=callas_json \
  -F profile_id=lintpdf-default
```

**XML variant:** swap `@callas-report.json` for `@callas-report.xml` and `callas_json` for `callas_xml`. Or omit `external_format` for auto-detect (recognises JSON by its top-level `profile`/`hits` keys and XML by its `<Report>` root).

### Mapping (both variants)

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

### callas limitations

- **Fixups** — reports that include fixups (auto-corrections applied) are parsed, but only the reported hits surface. LintPDF doesn't modify the PDF; see our [detection-only philosophy](/about).
- **Profile-specific categories** — callas' category taxonomy varies by profile. The category string is preserved verbatim; expect vocabulary drift if you roll up across multiple profiles.
- **Non-English severity tokens** — German / Japanese profiles need a [custom mapping](./schema-and-mappings) with an explicit `severity_map`.

Samples: [`/examples/callas-report.json`](https://lintpdf.com/examples/callas-report.json), [`/examples/callas-report.xml`](https://lintpdf.com/examples/callas-report.xml).

## Adobe Acrobat Preflight

Acrobat Pro's Preflight panel exports XML via its native schema.

### Export from Acrobat

1. Open **Tools → Print Production → Preflight**.
2. Run the profile against your PDF.
3. In the results pane, **Report → Create XML Report…** (button label varies slightly between versions).
4. Save to disk. LintPDF accepts the native Acrobat Preflight XML schema.

For scripted batches, drive Acrobat via Action Wizard or JavaScript — `preflight.execute({ nIndex: profileIndex, bForceReport: true, cOutputPath: "report.xml" })`.

### Submit

```sh
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@acrobat-preflight.xml \
  -F preflight_source=external \
  -F external_format=acrobat_xml \
  -F profile_id=lintpdf-default
```

Or omit `external_format` for auto-detect.

### Mapping

Acrobat's XML uses `<Problem>` elements inside a `<Summary>` document.

| Acrobat element | LintPDF field | Notes |
|---|---|---|
| `<Problem severity="...">` | `severity` | `Error`/`Warning`/`Info` mapped to `error`/`warning`/`advisory`. |
| `<Problem><Description>` | `message` | Full text including dynamic tokens resolved by Acrobat. |
| `<Problem><Page>` | `page_num` | 1-indexed. |
| `<Problem><BBox>` | `bbox` | PDF points. |
| `<Problem><CheckID>` | `inspection_id` | Preserved as `acrobat:<check-id>`. |
| `<Summary><ProfileName>` | `source.profile` | The profile that ran. |
| `<Summary><AcrobatVersion>` | `source.version` | Acrobat build. |

### Acrobat limitations

- **Pinned problems** — Acrobat's "pinned" concept (attaching a comment to a finding) has no LintPDF equivalent. Pinned metadata is preserved in the finding's `details` block but isn't rendered differently.
- **Custom check scripts** — profiles that include JavaScript rule scripts emit findings with the script-defined `CheckID`. Preserved verbatim; disambiguate with a category prefix in Acrobat if they collide.
- **DC vs 2017/2020** — Acrobat versions pre-2017 emit a different, less structured XML. Use a [custom mapping](./schema-and-mappings) keyed to `//Finding` (or whatever your version's root element is).

Sample: [`/examples/acrobat-report.xml`](https://lintpdf.com/examples/acrobat-report.xml).

## Custom mappings for anything exotic

If your vendor or profile variant isn't covered by the three built-in parsers — a renamed element, a non-English severity token, an exotic nested structure — build a [Custom import mapping](./schema-and-mappings). Point `item_selector` at `//Hit` / `//Error` / `//Problem` as appropriate and map each `<CheckID>` / `<Description>` / `<Page>` / `<BBox>` element explicitly.

## Related

- [External preflight imports](./overview) — the umbrella flow
- [LintPDF native import schema](./schema-and-mappings#schema) — for custom upstream tooling
- [Custom import mappings](./schema-and-mappings#mappings) — vendor variants and non-English exports
