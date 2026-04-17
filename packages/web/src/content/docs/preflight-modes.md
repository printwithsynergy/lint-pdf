---
title: "Preflight Modes"
description: "Three ways to submit a PDF — engine, external, minimal — and when to pick each."
section: "preflight"
order: 20
---

# Preflight Modes

Every PDF you submit to LintPDF runs in one of three modes. Pick the right mode on submission with the `preflight_source` form field on `POST /api/v1/jobs`.

| Mode | `preflight_source` | What runs | Findings source | Typical latency |
|---|---|---|---|---|
| Engine (default) | `engine` | Full 500+ analyzer pipeline | LintPDF engine | 3–45 s depending on file |
| External | `external` | No analyzers — imports findings from your existing preflight tool | Your tool (PitStop, callas, Acrobat, or custom) | <3 s |
| Minimal | `minimal` | Viewer-only extraction (pages, geometry, metadata) | No findings | <2 s |

All three modes produce a job you can open in the interactive viewer. Engine mode populates every capability; external and minimal modes start with a subset and can fill in specific capabilities on demand. See [Viewer Capabilities & On-Demand Fill-In](/docs/viewer-capabilities) for the mechanics.

## Engine mode — the default

Engine mode runs the full LintPDF preflight pipeline: font embedding, color spaces, image resolution, transparency, page geometry, PDF/X and PDF/A conformance, barcode grading, overprint — every one of the 500+ checks referenced in the [Checks Reference](/docs/checks). Pick engine mode when LintPDF is your preflight engine of record.

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F profile_id=lintpdf-default
# preflight_source=engine is implicit
```

## External mode — bring your own preflight

External mode accepts a PDF **plus** a preflight report you already produced with Enfocus PitStop, callas pdfToolbox, Adobe Acrobat Preflight, or a proprietary tool. LintPDF parses your report into canonical findings and renders them in the viewer and reports exactly as if our engine had produced them — so your operators keep their familiar preflight tool upstream and your stakeholders get LintPDF's interactive viewer, branded PDF output, and share links downstream.

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F external_report=@pitstop-report.xml \
  -F preflight_source=external \
  -F external_format=pitstop_xml
```

Supported built-in formats: `pitstop_xml`, `callas_json`, `callas_xml`, `acrobat_xml`, `lintpdf_json`. Omit `external_format` to let auto-detection pick. If your tool emits a proprietary shape, see [Custom Import Mappings](/docs/custom-mappings) — a tenant-defined mapping teaches LintPDF how to read it without us shipping a new parser.

Full walkthrough: [External Preflight Imports](/docs/external-imports).

## Minimal mode — viewer only

Minimal mode runs nothing. You submit a PDF, we extract page count, page geometry (media/crop/trim/bleed boxes, rotation), and document metadata, and that's it — the viewer opens immediately with page navigation, zoom, and download. Pick minimal when:

- You want to share a PDF with a stakeholder and let **them** choose which tools to invoke.
- You're embedding the viewer and need a fast open on files that will be reviewed manually.
- You don't have preflight findings but still want branded, anonymized, or tokenized sharing.

```bash
curl -X POST https://api.lintpdf.com/api/v1/jobs \
  -H "Authorization: Bearer lpdf_live_..." \
  -F file=@brochure.pdf \
  -F preflight_source=minimal
```

On the resulting job the viewer surfaces the five fillable capabilities (separations, TAC, fonts, images — and findings via a full engine run) as **Load** buttons. One click runs the single analyzer that fills that capability, keeping the one-click cost under a full engine run. See [Viewer Capabilities](/docs/viewer-capabilities).

## Cost and counting

Every job counts as one "file processed" against your plan regardless of mode. Capability fill-in runs (requested from the viewer) are counted separately, one per analyzer invocation — typically cheaper than a full engine run. See [Pricing](/pricing) for plan limits and overage rates.

## Plan-level gating

Some plans restrict which `preflight_source` values a tenant may submit. The Viewer tier, for example, is sized around minimal / external workflows only and forbids engine submissions. The restriction is enforced at the submit route — attempts return `403 plan_upgrade_required` with a structured envelope that dashboards render as an inline upgrade CTA.

| Plan | `engine` | `external` | `minimal` | Capability fill-in | Report downloads | Annotations |
|---|---|---|---|---|---|---|
| Free | ✓ | ✓ | ✓ | ✓ | JSON only | ✓ |
| Viewer | ✗ | ✓ | ✓ | ✗ | ✗ (viewer link only) | ✗ |
| Starter / Growth / Scale / Enterprise | ✓ | ✓ | ✓ | ✓ | PDF / JSON / XML (+ annotated PDF on Scale+) | ✓ |

## Picking a mode

- **Your shop runs PitStop / callas / Acrobat today** → external mode, feed us the native report.
- **Your shop runs a proprietary preflight tool** → external mode with a [custom mapping](/docs/custom-mappings).
- **You're building an approval workflow and want the viewer without findings up front** → minimal mode + on-demand capability fill-in.
- **Everything else** → engine mode.

## Related

- [External Preflight Imports](/docs/external-imports)
- [LintPDF Native Import Schema](/docs/import-schema)
- [Custom Import Mappings](/docs/custom-mappings)
- [Viewer-Only Submissions](/docs/viewer-only-mode)
- [Viewer Capabilities & On-Demand Fill-In](/docs/viewer-capabilities)
