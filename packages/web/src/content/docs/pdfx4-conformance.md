---
title: PDF/X-4 conformance suite
description: Full ISO 15930-7:2010 conformance suite — 91 PDFX4-* checks mapped to spec clauses.
---

# PDF/X-4 conformance suite

LintPDF ships a dedicated conformance validator for **ISO 15930-7:2010 (PDF/X-4)** that runs alongside the engine's 500+ generic preflight checks. When a profile's `conformance` field is set to `pdfx4`, every page of the submitted document is checked against the 91 rules below; each violation is emitted as a finding with check ID `PDFX4-NNN` and a citation to the relevant ISO clause.

PDF/X-4 (ISO 15930-7) is the modern conformance level for printing PDFs that contain live transparency. Unlike PDF/X-1a (which forces flattening) and PDF/X-3 (which is colour-managed but transparency-free), PDF/X-4 lets the RIP handle transparency, soft masks, and ICC-tagged colour at output time — but only if the file is structured correctly.

## How to enable it

Submit a job against a profile that opts into PDF/X-4 conformance:

```json
{
  "profile_id": "pdfx4-conforming",
  "conformance": "pdfx4"
}
```

The engine's 500+ generic checks still run — the PDF/X-4 suite is additive. Findings carry both the generic LPDF findings (e.g. `LPDF_FONT_004` for non-embedded fonts) and the conformance-specific findings (e.g. `PDFX4-036` for the same violation under ISO 15930-7 §6.3) so an operator can see both perspectives in the same report.

## Severity defaults

| Severity | Count | Examples |
|----------|------:|----------|
| Error | 39 | Encryption (`PDFX4-063`), non-embedded fonts (`PDFX4-036`), missing OutputIntent (`PDFX4-016`) |
| Warning | 18 | LZW image compression (`PDFX4-079`), invalid Trapped value (`PDFX4-012`), CropBox outside MediaBox (`PDFX4-055`) |
| Advisory | 34 | Linearized PDF (`PDFX4-004`), GTS_PDFXConformance missing (`PDFX4-007`), DeviceN colorant (`PDFX4-033`) |

Override per-check severity at the profile level via the `severity_overrides` block.

## Rules by clause

### File structure (ISO 15930-7 §6.1, ISO 32000-2 §7.5)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-001` | Error | PDF version below 1.6 |
| `PDFX4-002` | Error | %PDF header version not detected |
| `PDFX4-003` | Advisory | Binary marker missing from PDF header |
| `PDFX4-004` | Advisory | Linearized PDF detected |
| `PDFX4-080` | Error | Stream decompression failures |
| `PDFX4-081` | Error | Broken object references |
| `PDFX4-082` | Error | Cross-reference table errors |
| `PDFX4-083` | Warning | Trailer /ID array missing |
| `PDFX4-084` | Advisory | Incremental updates detected |

### XMP metadata (§6.7)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-005` | Error | XMP metadata stream missing |
| `PDFX4-006` | Error | GTS_PDFXVersion not declared / not 'PDF/X-4' |
| `PDFX4-007` | Advisory | GTS_PDFXConformance not declared |
| `PDFX4-008` | Warning | XMP pdf:PDFVersion does not match PDF header |
| `PDFX4-009` | Warning | xmp:CreateDate missing |
| `PDFX4-010` | Warning | xmp:ModifyDate missing |
| `PDFX4-011` | Warning | dc:title missing |
| `PDFX4-012` | Warning | pdf:Trapped value not in {True, False, Unknown} |
| `PDFX4-013` | Advisory | Info /Title disagrees with XMP dc:title |
| `PDFX4-014` | Advisory | Info /CreationDate disagrees with XMP xmp:CreateDate |
| `PDFX4-015` | Advisory | Info /ModDate disagrees with XMP xmp:ModifyDate |

### Output intent (§6.2.3)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-016` | Error | No OutputIntent present |
| `PDFX4-017` | Error | No OutputIntent with /S = /GTS_PDFX |
| `PDFX4-018` | Error | OutputIntent /OutputConditionIdentifier missing |
| `PDFX4-019` | Error | ICC profile not embedded and condition not registered |
| `PDFX4-020` | Warning | ICC profile version below 2.0 |
| `PDFX4-021` | Warning | ICC profile class not output (prtr) or display (mntr) |
| `PDFX4-022` | Warning | ICC color space not CMYK / RGB / Gray / Lab |
| `PDFX4-023` | Warning | More than one /GTS_PDFX OutputIntent |
| `PDFX4-024` | Advisory | /RegistryName missing for registered condition |
| `PDFX4-025` | Advisory | /Info string missing |

### Color (§6.2.4)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-026` | Warning | CalGray color space prohibited |
| `PDFX4-027` | Warning | CalRGB color space prohibited |
| `PDFX4-028` | Warning | DeviceRGB without RGB OutputIntent / DefaultRGB |
| `PDFX4-029` | Advisory | DeviceCMYK without CMYK OutputIntent / DefaultCMYK |
| `PDFX4-030` | Advisory | DeviceGray without Gray OutputIntent / DefaultGray |
| `PDFX4-031` | Warning | ICCBased component count not 1, 3, or 4 |
| `PDFX4-032` | Warning | Separation alternate spaces inconsistent |
| `PDFX4-033` | Advisory | DeviceN color space detected |
| `PDFX4-034` | Advisory | Lab color space used |
| `PDFX4-035` | Warning | Invalid rendering intent |

### Fonts (§6.3)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-036` | Error | Font not embedded |
| `PDFX4-037` | Error | TrueType font program missing |
| `PDFX4-038` | Error | Type3 font missing /CharProcs |
| `PDFX4-039` | Warning | CIDFontType2 missing /CIDToGIDMap |
| `PDFX4-040` | Error | Font has external file reference |
| `PDFX4-041` | Warning | Font missing /FontDescriptor |
| `PDFX4-042` | Error | Empty font program |

### Transparency (§6.2.5)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-043` | Advisory | Transparency used (informational) |
| `PDFX4-044` | Warning | Transparency group /CS conflicts with OutputIntent |
| `PDFX4-046` | Error | Non-standard blend mode |
| `PDFX4-047` | Advisory | Soft mask color space present |
| `PDFX4-048` | Advisory | Isolated knockout transparency group |

### Page geometry (§6.2.1)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-049` | Error | MediaBox missing |
| `PDFX4-050` | Error | TrimBox or ArtBox required |
| `PDFX4-051` | Warning | TrimBox and ArtBox both present (different) |
| `PDFX4-052` | Warning | BleedBox extends outside CropBox/MediaBox |
| `PDFX4-053` | Warning | TrimBox extends outside BleedBox |
| `PDFX4-054` | Error | Page box has zero or negative dimensions |
| `PDFX4-055` | Warning | CropBox extends outside MediaBox |
| `PDFX4-056` | Warning | ArtBox extends outside container box |

### Annotations (§6.4)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-057` | Error | Sound annotation prohibited |
| `PDFX4-058` | Error | Movie annotation prohibited |
| `PDFX4-059` | Error | 3D annotation prohibited |
| `PDFX4-060` | Error | RichMedia / Screen annotation prohibited |
| `PDFX4-061` | Advisory | PrinterMark not set to print |
| `PDFX4-062` | Advisory | TrapNet annotation present |

### Security (§6.2.2)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-063` | Error | Document is encrypted |
| `PDFX4-064` | Error | Trailer /Encrypt dictionary present |
| `PDFX4-065` | Error | Permission restrictions set |

### Optional content / OCGs (§6.5)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-066` | Warning | OCProperties /D (default config) missing |
| `PDFX4-067` | Warning | OCG default /BaseState not 'ON' |
| `PDFX4-068` | Advisory | OCG layers default to OFF |
| `PDFX4-069` | Warning | OCProperties /OCGs array empty |
| `PDFX4-070` | Warning | OCG /AS auto-state triggers present |

### Restricted features (§6.2.7, §6.2.8)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-071` | Error | JavaScript detected |
| `PDFX4-072` | Error | Launch action present |
| `PDFX4-073` | Error | Embedded files present |
| `PDFX4-074` | Error | XFA forms detected |
| `PDFX4-075` | Error | Transfer function present |
| `PDFX4-076` | Advisory | Custom halftone dictionary |
| `PDFX4-077` | Error | PostScript XObject present |
| `PDFX4-078` | Error | XObject references external stream |

### Images (§6.6)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-079` | Warning | LZW image compression deprecated |
| `PDFX4-085` | Advisory | RGB image without RGB OutputIntent |
| `PDFX4-086` | Advisory | Inline image exceeds 4KB recommended max |
| `PDFX4-087` | Advisory | JPEG2000 (JPX) image |

### Resources (§7.8.3)

| Check | Severity | Description |
|-------|----------|-------------|
| `PDFX4-088` | Error | XObject references null object |
| `PDFX4-089` | Error | Font references null object |
| `PDFX4-090` | Error | ColorSpace references null object |
| `PDFX4-091` | Error | ExtGState references null object |
| `PDFX4-092` | Advisory | Page has content but no resources |

## Notes

- The catalog generator (`packages/engine/scripts/export_check_catalog.py`) groups every `PDFX4-*` check under category `pdfx4` so the Rules editor renders them as one block.
- The suite does not replace the existing PDF/X-1a / PDF/X-3 / PDF/A validators — it sits alongside them. A profile asks for one conformance level at a time via the `conformance` enum.
- Some PDF/X-4 rules (e.g. `PDFX4-050` TrimBox required) cannot fire on a parsed PDF because the SemanticModelBuilder fills missing boxes from the inheritance chain per ISO 32000-2. The unit tests in `tests/conformance/pdfx4/` cover the analyzer logic directly; binary fixtures cover the rules that survive the builder.
