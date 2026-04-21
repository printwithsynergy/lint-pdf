---
title: "Importing from Adobe Acrobat Preflight"
description: "Feed Adobe Acrobat Preflight XML reports into LintPDF's viewer and reports."
section: "preflight"
order: 28
---

# Importing from Adobe Acrobat Preflight

Adobe Acrobat Pro's Preflight panel can export findings to XML. LintPDF's `acrobat_xml` parser reads that XML directly, preserving severity, page number, and bounding box geometry.

## Export from Acrobat

1. Open **Tools → Print Production → Preflight**.
2. Run the profile against your PDF.
3. In the results pane, **Report → Create XML Report…** (the button label varies slightly between Acrobat versions).
4. Save to disk. LintPDF accepts the native Acrobat Preflight XML schema; no transformation required.

For scripted batches, drive Acrobat via Action Wizard or JavaScript — `preflight.execute({ nIndex: profileIndex, bForceReport: true, cOutputPath: "report.xml" })`.

## Submission

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@acrobat-preflight.xml \
  -F preflight_source=external \
  -F external_format=acrobat_xml \
  -F profile_id=lintpdf-default
```

Or auto-detect:

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@acrobat-preflight.xml \
  -F preflight_source=external \
  -F profile_id=lintpdf-default
```

## What we map

Acrobat's XML uses `<Problem>` elements inside a `<Summary>` document. LintPDF's parser:

| Acrobat element | LintPDF field | Notes |
|---|---|---|
| `<Problem severity="...">` | `severity` | `Error` / `Warning` / `Info` mapped to `error` / `warning` / `advisory`. |
| `<Problem><Description>` | `message` | Full text including dynamic tokens resolved by Acrobat. |
| `<Problem><Page>` | `page_num` | 1-indexed. |
| `<Problem><BBox>` | `bbox` | PDF points. |
| `<Problem><CheckID>` | `inspection_id` | Preserved as `acrobat:<check-id>`. |
| `<Summary><ProfileName>` | `source.profile` | The profile that ran. |
| `<Summary><AcrobatVersion>` | `source.version` | Acrobat build. |

## Known limitations

- **Pinned problems**: Acrobat's "pinned" concept (attaching a comment to a finding) doesn't have a LintPDF equivalent. Pinned metadata is preserved in the finding's `details` block but isn't rendered differently.
- **Custom check scripts**: Profiles that include JavaScript rule scripts emit findings with the script-defined `CheckID`. LintPDF preserves those IDs verbatim; if they collide with IDs from another source, disambiguate with a category prefix in Acrobat.
- **Acrobat's `Warnings/Errors` split**: older Acrobat profiles emit two separate XML sections. Both are parsed; findings are interleaved in submission order.

## Acrobat DC vs Pro 2020 and earlier

LintPDF's parser is tested against DC (current), Pro 2020, and Pro 2017 XML outputs. Older Acrobat versions (pre-2017) emit a different, less structured XML — use a [custom mapping](/docs/custom-mappings) for those, keyed to `//Finding` or whatever root element your version emits.

## Sample payload

A trimmed Acrobat Preflight XML report is available at [`/examples/acrobat-report.xml`](https://lintpdf.com/examples/acrobat-report.xml).

## Related

- [External Preflight Imports](/docs/external-imports)
- [Custom Import Mappings](/docs/custom-mappings)
- [Importing from Enfocus PitStop](/docs/importing-from-pitstop)
- [Importing from callas pdfToolbox](/docs/importing-from-callas)
