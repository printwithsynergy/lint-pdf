---
title: "PDF Data Requirements"
description: "Exhaustive reference of every piece of PDF data the engine needs to run 100% of its checks — CPU, GPU, and AI tiers."
group: "Reference"
order: 6
---

# PDF data requirements

This document is the authoritative reference for what raw PDF data the engine must have access to in order to run its full suite of checks — covering all `LPDF_*` deterministic checks, all `AI_*` GPU and LLM checks, and all conformance validators (PDF/X, PDF/A, PDF/UA).

Companion documents:
- **[preflight-capability-map.md](preflight-capability-map.md)** — what checks exist and which analyzer emits them
- **[plugin-api.md](plugin-api.md)** — how analyzers receive data through `AnalyzerContext`
- **[integrations.md](integrations.md)** — external import formats (PitStop, callas, Acrobat); those parsers translate third-party reports and do not re-read the PDF itself

---

## Data flow overview

> **Architecture note (codex-authoritative ingestion, landed 2026-05):**
> The engine migrated from direct pikepdf parsing to a Codex-backed extraction path.
> `semantic/builder.py` and `semantic/interpreter.py` have been removed.
> `SemanticDocument` and `SemanticPage` are now populated from the Codex JSON payload
> via `codex_adapter.extract_semantic_document_via_codex()`.
> **Content stream events are always an empty list `[]` in the current path.**
> Section 8 documents the event schema as the legacy analyzer contract; the fields
> are no longer populated at runtime.

```
PDF file bytes
    │
    ▼
codex-pdf HTTP service  (or in-process codex_pdf.render fallback)
    │   extracts: page boxes, fonts, images, color spaces,
    │   annotations, output intents, XMP presence, analysis signals
    ▼
Codex JSON payload  (dict)
    │
    ▼  codex_adapter.extract_semantic_document_via_codex()
SemanticDocument + [] (empty events)
    │
    ▼
        AnalyzerContext
        ├── document       (SemanticDocument — from Codex JSON)
        ├── events         (always [] — content stream not re-interpreted)
        ├── pdf_bytes      (raw bytes, set on document._pdf_bytes)
        ├── capabilities   (page_images, text_regions — pull-based, cached)
        ├── services       (GPU client, LLM, renderer, metering, cost_cap, …)
        └── config         (per-plugin config + tenant ai_config)
               │
    ┌──────────┼───────────────┐
    ▼          ▼               ▼
CPU analyzers  GPU analyzers   EXTERNAL_AI analyzers
(LPDF_*)       (AI_IMG_*,      (AI_REG_*, AI_WCAG_*,
               AI_BARCODE_*)   AI_EU1169_*, …)
```

---

## Data layer summary

| Layer | Contents | Required by tier |
|---|---|---|
| **Codex JSON payload** | Primary extraction source — page boxes, fonts, images, color spaces, annotations, output intents, XMP flag, analysis signals | All tiers (upstream of SemanticDocument) |
| `SemanticDocument` | Normalised document structure hydrated from Codex JSON | CPU · GPU · EXTERNAL_AI |
| `ContentStreamEvents` | **Always `[]` in current path.** Event schema documented in §8 as legacy contract; no longer populated at runtime | — |
| `pdf_bytes` | Raw file bytes (set on `document._pdf_bytes`) | CPU (file size, barcode heuristics) · GPU (zxing decode) |
| `page_images` capability | Rasterized PNG/JPEG per page at configurable DPI | GPU · EXTERNAL_AI |
| `text_regions` capability | OCR-detected text bounding boxes | GPU · EXTERNAL_AI |
| External reference PDFs | Prior-version files pulled from tenant storage | EXTERNAL_AI (version diff, color consistency) |
| Tenant config | Brand palette, regulatory region, AI config, entitlements, historical quality data | CPU (configurable thresholds) · EXTERNAL_AI |

---

## 1. Document-level data

Populated once at ingest into `SemanticDocument`. All CPU, GPU, and AI analyzers receive this.

| Field | PDF source | Consumed by |
|---|---|---|
| `version` | File header (`%PDF-1.x` / `2.0`) | `DocumentAnalyzer`, `StandardsComplianceAnalyzer` |
| `is_encrypted` | Trailer `/Encrypt` dictionary | `DocumentAnalyzer`, `StructureAnalyzer` |
| `is_linearized` | First ≤1 024 bytes — presence of `/Linearized` hint stream in the first cross-reference section; `pikepdf.Pdf.is_linearized` exposes this natively | `DocumentAnalyzer`; Compile **rewrite** producer (verifies linearization mutation landed — Codex 1.5 §4.1) |
| `page_count` | Page tree root `/Count` | `DocumentAnalyzer` |
| `file_size` | Byte length of raw file | `DocumentAnalyzer` (via `ctx.pdf_bytes`) |
| `info_dict` | Trailer `/Info` — standard keys: Title, Author, Subject, Keywords, Creator, Producer, CreationDate, ModDate, Trapped | `MetadataAnalyzer`, `MetadataAuditAnalyzer` |
| `info_dict.custom` | Trailer `/Info` — all non-standard keys not in the set above; each emitted as `(name, str(value))` | `MetadataAnalyzer`; Compile **rewrite** producer round-trips lineage breadcrumbs here (e.g. `CustomCompileLineageID`, `CustomCompileProducer`, `CustomCompileVersion`, `CustomCompilePlanSHA`) — Codex 1.5 §4.2 |
| `metadata_stream` | Codex `xmp.present` flag — populated as `b"<xmp-present/>"` sentinel when XMP is present, `None` otherwise. Raw XMP bytes are no longer surfaced. | `MetadataAnalyzer`, `MetadataAuditAnalyzer` |
| `catalog` | Now `{"codex_analysis": <analysis_dict>}` — Codex per-document analysis signals. Raw PDF catalog dictionary entries (`/ViewerPreferences`, `/Lang`, `/MarkInfo`, etc.) are no longer directly accessible; analyzers that need them must read from `codex_analysis`. | `MetadataAnalyzer`, `StructureAnalyzer`, `AccessibilityAnalyzer` |
| `catalog[/ViewerPreferences]` | Via Codex `codex_analysis` — viewer preferences as parsed by Codex | `MetadataAnalyzer` |
| `catalog[/Lang]` | Via Codex `codex_analysis` — document language string | `MetadataAnalyzer` |
| `catalog[/MarkInfo]` | Via Codex `codex_analysis` — marked PDF flags | `AccessibilityAnalyzer` |
| `catalog[/StructTreeRoot]` | Via Codex `codex_analysis` — tagged-PDF structure tree presence | `AccessibilityAnalyzer`, `StructureAnalyzer` |
| `catalog[/AcroForm]` | Via Codex `codex_analysis.has_acroform` boolean | `StructureAnalyzer`, `DocumentAnalyzer` |
| `catalog[/OCProperties]` | Via Codex `codex_analysis.has_oc_properties` boolean | `StructureAnalyzer` |
| `catalog[/OpenAction]` | Via Codex `codex_analysis.has_open_action` boolean | `DocumentAnalyzer` |
| `catalog[/Outlines]` | Via Codex `codex_analysis` | `StructureAnalyzer` |
| `catalog[/NeedsRendering]` | Via Codex `codex_analysis` | `DocumentAnalyzer` |
| `output_intents` | Codex `output_intents` array — each entry: `subtype`, `output_condition_identifier`, `profile_id`. DestOutputProfile ICC stream is referenced by ID, not embedded. | `IccProfileAnalyzer`, `ColorAnalyzer`, `GamutAnalyzer` |
| `trailer` | Always `{}` in the Codex path — raw trailer is not re-exposed. Trailer ID presence is surfaced via `codex_analysis.trailer_id_present`. | `DocumentAnalyzer` |
| `dieline_result` | Always `None` in the Codex path — dieline detection moved to Codex's analysis layer. | `DielineIso19593Analyzer`, `DielinePerfIndicatorAnalyzer`, `PackagingAnalyzer` |

---

## 2. Per-page data

Populated per page into `SemanticPage` with all resource inheritance resolved. Pages are 1-indexed.

### Page boxes (all in PDF user-space points, 1/72 inch, lower-left origin)

| Box | PDF key | Required | Consumed by |
|---|---|---|---|
| `media_box` | `/MediaBox` | Yes — must exist | All geometry checks, `PageGeometryAnalyzer` |
| `crop_box` | `/CropBox` | No (defaults to MediaBox) | `PageGeometryAnalyzer` |
| `bleed_box` | `/BleedBox` | No | `PageGeometryAnalyzer`, `PackagingAnalyzer` |
| `trim_box` | `/TrimBox` | No | `PageGeometryAnalyzer`, `PackagingAnalyzer`, `SealZoneKeepoutAnalyzer` |
| `art_box` | `/ArtBox` | No | `PageGeometryAnalyzer` |

### Page attributes

| Field | PDF source | Consumed by |
|---|---|---|
| `rotate` | Codex `pages[i].rotation` (0 / 90 / 180 / 270) | `PageGeometryAnalyzer`, all spatial analyzers |
| `user_unit` | Always `1.0` in the Codex path — Codex normalises coordinates to 1/72 in points | All geometry checks |
| `resources` | `{"codex_analysis": <page_analysis_dict>}` — Codex per-page analysis signals. Raw `/Resources` dictionary is not re-exposed. | Analyzers that consume Codex analysis signals |
| `content_stream` | Always `b""` in the Codex path — page content stream is not re-exposed | (no longer consumed) |
| `transparency_group` | Always `None` in the Codex path — transparency group detection moved to Codex analysis | `TransparencyAnalyzer` |

### Resolved resource collections (per page)

| Collection | Type | Consumed by |
|---|---|---|
| `fonts` | `dict[name, PdfFont]` | `FontAnalyzer`, `TextMetricsAnalyzer`, `LegibilityCompositeAnalyzer`, all text events |
| `images` | `list[PdfImage]` | `ImageAnalyzer`, `IccProfileAnalyzer`, GPU image analyzers |
| `color_spaces` | `dict[name, PdfColorSpace]` | `ColorAnalyzer`, `SpotColorAnalyzer`, `IccProfileAnalyzer`, `GamutAnalyzer`, EPM analyzers |
| `annotations` | `list[PdfAnnotation]` | `AnnotationAnalyzer` |

---

## 3. Font data (`PdfFont`)

One `PdfFont` object per font resource on each page. All fields are required by `FontAnalyzer`; subsets are consumed by text-metric and regulatory analyzers.

| Field | PDF source | Notes |
|---|---|---|
| `name` | Resource key (e.g. `F1`) | Identifies font within the page resource dict |
| `base_font` | `/BaseFont` entry | PostScript name; may include 6-char subset prefix (`ABCDEF+`) |
| `font_type` | `/Subtype` | One of: `Type1`, `TrueType`, `Type0`, `Type3`, `CIDFontType0`, `CIDFontType2` |
| `embedded` | Codex embedding status — string enum: `"full"` (fully embedded), `"subset"` (subset-embedded), `"referenced"` (not embedded, referenced by name). **No longer a bool.** | Required for embedding checks |
| `subset` | Subset prefix pattern in `base_font` | 6 uppercase chars + `+` |
| `missing_glyphs_detected` | `bool` — Codex detected missing glyph entries in the font's cmap or width table | `FontAnalyzer` |
| `encoding` | `/Encoding` | `WinAnsiEncoding`, `Identity-H`, `MacRomanEncoding`, etc. |
| `font_descriptor` | `/FontDescriptor` dictionary | Flags, FontBBox, ItalicAngle, Ascent, Descent, CapHeight, XHeight, StemV, StemH, MissingWidth |
| `has_to_unicode` | `/ToUnicode` CMap stream presence | Required for text-extraction / accessibility checks |
| `cid_system_info` | `/CIDSystemInfo` | Registry, Ordering, Supplement — CID fonts only |

**Consumed by:** `FontAnalyzer` (`LPDF_FONT_*`), `TextMetricsAnalyzer`, `LegibilityCompositeAnalyzer`, `PlaceholderTextAnalyzer`, AI pharma/regulatory analyzers (`AI_PHARMA_*`, `AI_FDA_*`).

---

## 4. Image data (`PdfImage`)

One `PdfImage` object per image XObject or inline image on each page. All fields are now sourced from the Codex JSON `images[]` array. Placement geometry (effective DPI) is pre-computed by Codex — the old `ImagePlacedEvent.ctm` path no longer applies.

| Field | Codex JSON source | Notes |
|---|---|---|
| `name` | `images[i].name` | Resource key or `inline_N` |
| `width` | `images[i].width_px` | Pixel columns |
| `height` | `images[i].height_px` | Pixel rows |
| `bits_per_component` | `images[i].bits_per_component` | 1, 2, 4, 8, or 16 |
| `color_space` | `images[i].color_space_id` → resolved `PdfColorSpace` | Full `PdfColorSpace` object |
| `filters` | `images[i].filters` (ordered) | `FlateDecode`, `DCTDecode`, `JBIG2Decode`, `CCITTFaxDecode`, `JPXDecode`, `RunLengthDecode`, `LZWDecode` |
| `has_soft_mask` | `images[i].has_soft_mask` | Transparency |
| `has_hard_mask` | `images[i].has_hard_mask` | Hard clipping mask |
| `interpolate` | `images[i].interpolate` | Bilinear upscaling enabled |
| `intent` | `images[i].rendering_intent` | Per-image rendering intent override |
| `inline` | `images[i].inline` | Inline image vs XObject |
| `has_opi` | `images[i].has_opi` | OPI proxy; low-res placeholder |
| `effective_resolution_dpi` | `images[i].effective_resolution_dpi` → `{x_dpi, y_dpi}` | **Pre-computed by Codex** using placement CTM. Replaces the old `ImagePlacedEvent.ctm` + manual DPI arithmetic. Required for all `LPDF_IMG_*` DPI checks. |

**Consumed by:** `ImageAnalyzer` (`LPDF_IMG_*`), `IccProfileAnalyzer` (`LPDF_ICC_*`), `EpmTierCAnalyzer`, GPU image-quality analyzer, NSFW detector, logo detection.

---

## 5. Color space data (`PdfColorSpace`)

One `PdfColorSpace` per named color space on each page. All fields are now sourced from the Codex JSON `color_spaces[]` array.

| Field | Codex JSON source | Notes |
|---|---|---|
| `cs_type` | `color_spaces[i].family` | `DeviceRGB`, `DeviceCMYK`, `DeviceGray`, `ICCBased`, `CalRGB`, `CalGray`, `Lab`, `Indexed`, `Separation`, `DeviceN`, `NChannel`, `Pattern` |
| `components` | `color_spaces[i].canonical.components` | Number of color components |
| `colorant_names` | `color_spaces[i].spot_colorants[*].name` | Spot color names; central for ink inventory |
| `icc_profile_ref` | `color_spaces[i].profile_id` | References ICC profile by Codex ID |
| `alternate` | `color_spaces[i].alternate` | Alternate color space (for `Separation`, `DeviceN`, `ICCBased`) |
| `base_space` | `color_spaces[i].base_space` | Base space for `Indexed` |

### Spot colorant enrichment (`spot_colorants[]`)

For `Separation` and `DeviceN` color spaces, Codex populates each colorant entry with resolved color authority data (Codex 1.5+):

| Field | Notes |
|---|---|
| `name` | Colorant name (e.g. `PANTONE 485 C`) |
| `lab` | CIE Lab `[L*, a*, b*]` — authoritative |
| `cmyk` | CMYK `[C, M, Y, K]` tint values |
| `rgb` | sRGB `[R, G, B]` display values |
| `pantone_name` | Matched Pantone name, or `null` |
| `neutral_density` | CIE-derived ND value `[0.05–2.50]`, or `null` (Codex 1.5 §2.1) |
| `neutral_density_source` | `"measured"` / `"computed_from_lab"` / `"estimated"` / `null` (Codex 1.5 §2.1) |

### ECG / CMYKOGV requirements (`LPDF_ECG_*`)

`EcgAnalyzer` (18 check IDs `LPDF_ECG_001`–`018`) additionally requires:

- `DeviceN` color spaces with Orange / Violet / Green colorant names in addition to CMYK — checked against FOGRA55 gamut boundary
- 7-channel TAC sum across all CMYKOGV colorants
- ECG ICC output intent profile (version ≥ 4, CMYKOGV color space type)
- Per-colorant Lab values from `spot_colorants[]` for ΔE-2000 gamut boundary checks

**Consumed by:** `ColorAnalyzer` (`LPDF_COLOR_*`), `SpotColorAnalyzer` (`LPDF_SPOT_*`), `IccProfileAnalyzer` (`LPDF_ICC_*`), `GamutAnalyzer`, `InkCoverageAnalyzer` (`LPDF_INK_*`), `DuplicateProcessSpotAnalyzer`, `SpotNameSimilarityAnalyzer`, `SoloSpotVerifyAnalyzer`, `AdvancedColorAnalyzer` (`LPDF_ADV_*`), `ColorInventoryAuditAnalyzer`, `EpmAnalyzer` / `EpmTierA/B/CAnalyzer`, **`EcgAnalyzer` (`LPDF_ECG_*`)** (new).

---

## 6. ICC profile data

Extracted from `ICCBased` color space streams and from Output Intent `DestOutputProfile` streams.

| Data point | Source |
|---|---|
| Raw profile bytes | ICC stream contents |
| Color space type within profile | Profile header byte (tag `0x636f6c72`) — RGB, CMYK, Gray, Lab |
| Profile Connection Space (PCS) | Profile header — XYZ or Lab |
| Rendering intent tag | Profile header byte 67 — perceptual, relative colorimetric, saturation, absolute colorimetric |
| Profile version | Header bytes 8–11 |

**Consumed by:** `IccProfileAnalyzer` (`LPDF_ICC_*`), `ColorAnalyzer`, `GamutAnalyzer`.

---

## 7. Annotation data (`PdfAnnotation`)

One `PdfAnnotation` per annotation on each page.

| Field | PDF source |
|---|---|
| `subtype` | `/Subtype` — Text, Link, FreeText, Stamp, Sound, Movie, Widget, 3D, FileAttachment, Watermark, TrapNet, Screen, Redact |
| `rect` | `/Rect` — bounding box in page user space |
| `flags` | `/F` integer bit field — bit 1 Invisible, bit 2 Hidden, bit 3 Print, bit 7 Locked, etc. |
| `contents` | `/Contents` text string |
| `page_num` | Resolved from page association |

**Consumed by:** `AnnotationAnalyzer` (`LPDF_ANNOT_*`).

---

## 8. Content stream events

> **Status: legacy schema — events are always `[]` in the current Codex-backed path.**
> `semantic/interpreter.py` was removed when the engine migrated to codex-authoritative
> ingestion. The `events` parameter is passed to analyzers and conformance validators
> for API compatibility but is never populated. Analyzer logic that previously relied on
> events (path painting, color changes, overprint state, text rendering) now reads
> equivalent data from `SemanticDocument` fields derived from the Codex JSON payload.
> This section is retained as a schema reference for the legacy analyzer protocol and
> for OSS hosts that may re-introduce direct interpretation.

The content stream interpreter walks each page's content stream and emits typed, frozen-dataclass events. CPU analyzers consume `ctx.events` directly; they never re-parse PDF operators.

Every event carries `operator: str`, `page_num: int`, `operator_index: int`.

### TextRenderedEvent (`Tj`, `TJ`, `'`, `"`)

| Field | Meaning |
|---|---|
| `font_name` | Active font resource key |
| `font_size` | Active font size in text space |
| `ctm` | Current transformation matrix (6-element tuple) |
| `text_matrix` | Tm matrix at text origin |
| `color_space` | Non-stroking color space name |
| `color_values` | Non-stroking color component values |
| `opacity` | Non-stroking alpha (ca from ExtGState) |
| `rendering_mode` | 0 fill · 1 stroke · 2 fill+stroke · 3 invisible · 4 fill+clip · … |
| `rendering_intent` | Active rendering intent |
| `bbox` | Approximate bounding box in page user space |

**Consumed by:** `FontAnalyzer`, `TextMetricsAnalyzer`, `LegibilityCompositeAnalyzer`, `PlaceholderTextAnalyzer`, `HairlineAnalyzer` (rendering_mode=1 text stroke), `LegalCopyMinSizeAnalyzer`, `SealZoneKeepoutAnalyzer`, `DimensionCalloutAnalyzer`, AI regulatory analyzers.

### PathPaintingEvent (`S`, `s`, `f`, `F`, `f*`, `B`, `B*`, `b`, `b*`, `n`)

| Field | Meaning |
|---|---|
| `fill` | Path is filled |
| `stroke` | Path is stroked |
| `even_odd` | Even-odd fill rule (vs. non-zero winding) |
| `fill_color_space` | Fill color space name |
| `fill_color_values` | Fill color component tuple |
| `stroke_color_space` | Stroke color space name |
| `stroke_color_values` | Stroke color component tuple |
| `line_width` | Stroke line width in user space |
| `line_cap` | 0 butt · 1 round · 2 projecting square |
| `line_join` | 0 miter · 1 round · 2 bevel |
| `dash_pattern` | Dash array + phase |
| `point_count` | Number of path control points |
| `bbox` | Bounding box of the path in page user space |

**Consumed by:** `HairlineAnalyzer` (`LPDF_STROKE_*`), `OverprintAnalyzer` (`LPDF_OVER_*`), `ColorAnalyzer`, `InkCoverageAnalyzer`, `BarcodeAnalyzer` (`LPDF_BARCODE_*`), `DielineIso19593Analyzer`, `DielinePerfIndicatorAnalyzer`, `CuttingOverprintAnalyzer`, `DimensionCalloutAnalyzer`, `PageGeometryExtraAnalyzer`, `EpmAnalyzer`.

### ImagePlacedEvent (`Do` on image XObject or inline image)

| Field | Meaning |
|---|---|
| `image_name` | XObject resource key |
| `ctm` | Transformation matrix at placement (used for effective DPI) |
| `pixel_width`, `pixel_height` | Image pixel dimensions |
| `bits_per_component` | Bits per channel |
| `color_space` | Image color space name |
| `filters` | Compression filter chain |
| `has_soft_mask` | SMask transparency present |
| `is_inline` | Inline image vs XObject |
| `has_opi` | OPI proxy dictionary present |
| `has_alternate` | Alternate image present |

**Consumed by:** `ImageAnalyzer`, `IccProfileAnalyzer`, `TransparencyAnalyzer`, `PageGeometryAuditAnalyzer`.

### ColorChangedEvent (`sc`, `scn`, `SC`, `SCN`, `rg`, `RG`, `k`, `K`, `g`, `G`)

| Field | Meaning |
|---|---|
| `stroking` | True = stroking color space changed; False = non-stroking |
| `color_space` | New color space name |
| `color_values` | New color component values |

**Consumed by:** `ColorAnalyzer`, `SpotColorAnalyzer`, `DuplicateProcessSpotAnalyzer`, `SoloSpotVerifyAnalyzer`, `ColorInventoryAuditAnalyzer`, `InkCoverageAnalyzer`, `GamutAnalyzer`, `EpmAnalyzer` / EPM tier analyzers.

### OpacityChangedEvent (`gs` with ExtGState `/ca` or `/CA`)

| Field | Meaning |
|---|---|
| `stroking_alpha` | New stroking alpha (CA) |
| `non_stroking_alpha` | New non-stroking alpha (ca) |
| `blend_mode` | Blend mode name (Normal, Multiply, Screen, Overlay, …) |

**Consumed by:** `TransparencyAnalyzer` (`LPDF_TRANS_*`), `OverprintAnalyzer`.

### OverprintChangedEvent (`gs` with ExtGState `/OP`, `/op`, `/OPM`)

| Field | Meaning |
|---|---|
| `overprint_stroking` | Stroking overprint flag |
| `overprint_non_stroking` | Non-stroking overprint flag |
| `overprint_mode` | OPM 0 (ignore zero components) or 1 (composite zero) |

**Consumed by:** `OverprintAnalyzer` (`LPDF_OVER_*`), `CuttingOverprintAnalyzer`, `ColorAnalyzer`.

### FormXObjectEnteredEvent (`Do` on form XObject)

| Field | Meaning |
|---|---|
| `form_name` | XObject resource key |
| `form_matrix` | `/Matrix` of the form XObject |
| `ctm` | CTM at the `Do` call site |
| `nesting_depth` | Recursion depth (1 = top-level) |

**Consumed by:** `TransparencyAnalyzer` (blend space inheritance through nested forms), `OverprintAnalyzer`.

### LineStyleChangedEvent (`J`, `j`, `d`, `M`, `ri`)

| Field | Meaning |
|---|---|
| `line_cap` | New line cap style |
| `line_join` | New line join style |
| `dash_pattern` | New dash array + phase |
| `miter_limit` | New miter limit |
| `rendering_intent` | New rendering intent (`ri` operator) |

**Consumed by:** `HairlineAnalyzer`, `OverprintAnalyzer`.

### PrepressStateChangedEvent (`gs` with halftone / transfer / BG-UCR entries)

| Field | Meaning |
|---|---|
| `has_halftone` | ExtGState sets a halftone dictionary |
| `has_transfer_function` | ExtGState sets a transfer function |
| `has_bg_ucr` | ExtGState sets black-generation or undercolor-removal functions |

**Consumed by:** `PrepressAnalyzer` (`LPDF_PREPRESS_*`).

### ClippingPathSetEvent (`W`, `W*`)

| Field | Meaning |
|---|---|
| `even_odd` | Even-odd clipping rule used |

**Consumed by:** Geometry analyzers that track clipping regions.

---

## 9. Document structure and security data

From the document catalog and trailer, consumed by structural analyzers.

| Data | PDF source | Consumed by |
|---|---|---|
| Encryption algorithm | `/Encrypt` — `/Filter`, `/V`, `/Length`, `/P` permissions | `DocumentAnalyzer`, `StructureAnalyzer` |
| User/owner password hashes | `/Encrypt` — `/U`, `/O` | `DocumentAnalyzer` |
| Form fields | `/AcroForm` — field type, name, value, actions | `StructureAnalyzer`, `DocumentAnalyzer` |
| JavaScript actions | `/AA`, `/OpenAction`, `/JS` entries | `DocumentAnalyzer` (`LPDF_DOC_*`) |
| OCG layer names | `/OCProperties[/OCGs]` — `/Name` per group | `StructureAnalyzer` |
| OCG default visibility | `/OCProperties[/D][/ON]`, `/OFF` | `StructureAnalyzer` |
| OCG locked layers | `/OCProperties[/D][/Locked]` | `StructureAnalyzer` |
| Marked PDF flags | `/MarkInfo[/Marked]`, `/UserProperties`, `/Suspects` | `AccessibilityAnalyzer` |
| Structure tree | `/StructTreeRoot` and child elements | `AccessibilityAnalyzer` |
| Document language | `/Lang` string | `MetadataAnalyzer` |
| Bookmarks/outlines | `/Outlines` root | `StructureAnalyzer` |

---

## 10. Barcode-specific data

Barcodes are detected and evaluated through two parallel paths.

### CPU path — path geometry heuristics

Reads `PathPaintingEvent` stream for bar/space patterns. No raw bytes or images needed.

Data required:
- `stroke_color_space`, `stroke_color_values` — dark element color
- `fill_color_space`, `fill_color_values` — fill color
- `line_width` — bar width proxy
- `bbox` — quiet zone extent
- `point_count` — linear vs 2D pattern classification
- `dieline_result` (pre-computed) — dieline spatial context

**Emits:** `LPDF_BARCODE_001`–`013`, `019`–`031` (1D candidate detection + grading), `LPDF_BARCODE_014`–`018` (2D fill-grid heuristics).

### GPU / AI path — visual decoding

Data required:
- Rendered page image at ≥ 300 DPI (`ctx.capabilities.page_images`)
- Raw PDF bytes (`ctx.pdf_bytes`) for zxing-cpp direct stream decode

**Consumed by:** `barcode_content`, `barcode_decode`, `barcode_dimensions`, `barcode_content_qr_match`, `pharma_serialization`, `qr_human_readable`, `qr_validation`.

---

## 11. Rasterized page images (GPU and AI analyzers)

Delivered through `ctx.capabilities.page_images.get_page_image(page_num, dpi)`. The orchestrator renders once per (page, DPI) pair and shares the result across all consumers.

| DPI | Use |
|---|---|
| 72 | Thumbnail, document classification |
| 150 | WCAG contrast checking |
| 300 | Barcode decode, OCR, logo detection, regulatory symbol detection |
| 600 | Hairline-level spatial inspection |

Format: PNG (lossless) or JPEG (configurable quality). Coordinate space: top-left origin, pixels.

**Consumed by:** `image_quality`, `nsfw_detection`, `logo_detection`, `barcode_*`, `regulatory_symbols`, `symbol_detection`, `safe_zone_violations`, `wcag_contrast`, `banding_detection`, `color_cast_detection`, `text_as_outlines`, `auto_preflight_profile`, `file_classification`, all regulatory compliance AI analyzers (`AI_EU1169_*`, `AI_FDA_*`, `AI_PHARMA_*`, `AI_GHS_*`, `AI_COSM_*`, etc.).

### OCR text regions

Delivered through `ctx.capabilities.text_regions.get_text_regions(page_num, dpi)`. Bounding boxes of detected text blocks, derived from GPU outline detection. Used when text is rendered as outlines (no `TextRenderedEvent` emitted).

**Consumed by:** `text_as_outlines`, `SealZoneKeepoutAnalyzer`, outlined-text font-size heuristics.

---

## 12. Raw PDF bytes (`ctx.pdf_bytes`)

The full file as a `bytes` object. Lazy-loaded by the orchestrator only when at least one active analyzer declares `requires_bytes = True` in its manifest.

**Required by:**
- `DocumentAnalyzer` — file size
- `BarcodeAnalyzer` — zxing-cpp direct decode path
- AI barcode analyzers (`barcode_decode`) — zxing-cpp stream decode
- Any analyzer that needs to re-parse or verify byte-level structure

---

## 13. External reference files (AI analyzers)

Some AI analyzers pull prior-version PDFs from tenant storage to detect regressions or validate consistency. These are not part of the submitted PDF.

| Analyzer | What it fetches |
|---|---|
| `file_comparison/version_diff.py` | Prior-version PDF bytes via `ctx.services.storage.download()` |
| `color_analysis/cross_document_consistency.py` | Reference PDF rasters from storage |

---

## 14. Tenant and configuration data

Not from the PDF file itself, but required context injected into `AnalyzerContext`.

| Context field | Contents | Consumed by |
|---|---|---|
| `ctx.config["ai_config"]` | Brand palette, regulatory target region, profile-level thresholds, custom ICC profiles, target market, TAC limit, EPM mode | All configurable CPU checks; all AI analyzers |
| `ctx.tenant_id` | Tenant identifier — scopes all SaaS service calls | All metered / cost-capped checks |
| `ctx.services.tenants` | Entitlements, AI config resolution, historical quality data | `submission_quality_spc` (SPC trend analysis), entitlement-gated analyzers |
| `ctx.services.cost_cap` | Per-tenant AI credit enforcement | All `EXTERNAL_AI` analyzers |
| `ctx.services.metering` | Usage recording | All `EXTERNAL_AI` analyzers |

---

## 15. Conformance validator data requirements

Conformance checks (`LPDF_PDFX_*`, `LPDF_PDFA_*`, `LPDF_UA_*`) consume a subset of the same `SemanticDocument` data plus the full PDF byte stream passed to veraPDF.

| Check family | Additional data beyond SemanticDocument |
|---|---|
| PDF/X-1a, X-3, X-4 | `output_intents` (required); `is_encrypted` (must be false); `catalog[/OutputIntents]` |
| PDF/A-1b, 2b, 3b | `metadata_stream` (XMP); font embedding; color space ICC tagging |
| PDF/UA-1 | `catalog[/MarkInfo][/Marked]`; `catalog[/StructTreeRoot]`; `catalog[/Lang]`; `has_to_unicode` on all fonts |
| veraPDF sidecar | Raw PDF bytes forwarded to the veraPDF HTTP sidecar via `ctx.services.verapdf_client` |

---

## 16. Producer-suite contract additions (Codex 1.5)

Codex 1.5 lands a coordinated minor bump aggregating three additive section bumps and the server-side polish required to support the **CompilePDF** writer suite (`compile-pdf`, `compile-pdf-marketing`).

The deliverables in this section are **purely additive** — Lint's analyzers continue to operate against Codex without code changes when the bump rolls out. The new fields, functions, and endpoints below are consumed by Compile's rewrite / marks / impose / trap producers; Lint sees them in extract output and on `/v1/contract.section_schema_versions` but doesn't require them.

**Authority**: APPR-2026-05-09-32 / 33 / 34 in `~/synergy-agents/approvals.md` (full 14-deliverable scope, endpoint shapes proposed-as-shipped, 2-replica staging in 1 Railway plant).

**Companion docs**: full design rationale lives in `compile-pdf`'s
`COMPILE-DESIGN-SPEC.md` (1955 lines) and `COMPILE-CODEX-PREREQUISITES.md`
(comprehensive engineering brief). This section integrates the Compile
deliverables into the Lint reference so the Codex 1.5 work session has
a single document to drive against.

### 16.1 Color section (`COLOR_SCHEMA_VERSION` 1.0.0 → 1.1.0)

#### 16.1.1 `CodexSpotColorant` neutral-density fields

**File**: `src/codex_pdf/models/v1.py`

Two new fields on the existing dataclass:

```python
neutral_density: float | None = None
"""CIE-derived ND value. None when unknown.
Range: typically [0.05, 2.50]. Process black ~1.70; cyan ~0.55;
pastel spots ~0.10–0.30."""

neutral_density_source: Literal["measured", "computed_from_lab", "estimated", None] = None
"""How `neutral_density` was derived:
- "measured"          — published Pantone Color Manager export or
                         authoritative measurement
- "computed_from_lab" — derived via -log10(Y/100) where Y is the
                         CIE-XYZ luminance from the entry's Lab.
                         Accuracy ±20%.
- "estimated"         — heuristic when neither Pantone nor Lab
                         is reliable (rare)
- None                — `neutral_density` is None; consumer falls
                         back to its own table or computed math."""
```

**Consumed by**: Compile's **trap** producer for spread/choke decisions per CompilePDF design spec §5.2. Lint analyzers ignore the new fields.

#### 16.1.2 `load_inkbook()` payload extension

**File**: `src/codex_pdf/color/__init__.py` (verify path during implementation)

Every entry in the returned `pantone[]` and `curated[]` arrays gains the two ND fields above. Existing keys (`name`, `lab`, `cmyk`, `rgb`, `pantone_name`) are preserved verbatim.

```json
{
  "schema_version": "1.1.0",
  "manifest": { /* unchanged */ },
  "pantone": [
    {
      "name": "PANTONE 485 C",
      "lab": [...], "cmyk": [...], "rgb": [...],
      "pantone_name": "PANTONE 485 C",
      "neutral_density": 1.18,
      "neutral_density_source": "measured"
    }
  ],
  "curated": [
    {
      "name": "DeviceCMYK Black",
      "lab": [...], "cmyk": [0.0, 0.0, 0.0, 1.0], "rgb": [...],
      "pantone_name": null,
      "neutral_density": 1.70,
      "neutral_density_source": "measured"
    }
  ]
}
```

#### 16.1.3 New endpoint: `POST /v1/color/neutral-density`

**File**: `src/codex_pdf/api/main.py`

Request body — exactly one of these three forms (mutually exclusive):

```json
{ "name": "PANTONE 485 C" }
```
```json
{ "lab": [55, 80, 70] }
```
```json
{ "cmyk": [0.05, 0.95, 0.95, 0.0] }
```

Response body:

```json
{
  "schema_version": "1.1.0",
  "neutral_density": 1.18,
  "source": "measured"
}
```

**Resolution order** (server-side):

1. If `name` provided → look up in `load_pantone_reference()` → curated catalogue → return measured/published ND if available.
2. If `lab` provided → compute ND via `-log10(Y/100)` from Lab→XYZ. Return `source: "computed_from_lab"`.
3. If `cmyk` provided → derive Lab via the curated CMYK→Lab transform (already in `codex_pdf.color`), then compute ND from Lab. Return `source: "computed_from_lab"`.

**Errors**:
- 400 if more than one of `{name, lab, cmyk}` present
- 400 if `name` is unrecognized AND no Lab fallback derivable
- 422 if Lab values are out of valid range

#### 16.1.4 Pantone catalog ND population

**File**: `codex_pdf/color/data/pantone_reference.json`

Enrich entries with `neutral_density` values where Pantone Color Manager publishes them. Where not published, leave `neutral_density: null` so consumers fall back to computed-from-Lab or to their own tenant ND tables.

Acceptable to ship Codex 1.5.0 with partial population (e.g., Formula Guide Coated only) provided the schema is in place; subsequent point releases enrich.

#### 16.1.5 Color tests

- Unit: `CodexSpotColorant` accepts both legacy (no ND) and new (with ND) shapes; serialization round-trips both
- Unit: `POST /v1/color/neutral-density` for each of the three input forms, including resolution-order edge cases
- Contract: `GET /v1/color/inkbook` returns bumped `schema_version: "1.1.0"` and includes the new fields where data is available
- Backward-compat: existing `POST /v1/color/{resolve,match-pantone}` endpoints continue to behave identically; bumped `schema_version` shows on their responses too

### 16.2 Geom section (`GEOM_SCHEMA_VERSION` 1.0.0 → 1.1.0)

#### 16.2.1 `polygon_offset()` function

**File**: `src/codex_pdf/geom/path.py`

```python
def polygon_offset(
    path: Path,
    distance: float,
    *,
    join_type: Literal["round", "miter", "bevel"] = "round",
    end_type: Literal["closed-polygon", "open-square", "open-round", "open-butt"] = "closed-polygon",
    miter_limit: float = 4.0,
) -> Path:
    """Inflate (positive distance) or deflate (negative distance) a
    closed polygon path.

    Backed by Clipper2 ``InflatePaths`` via pyclipr. Requires the
    ``[geom]`` extra; raises ``NotImplementedError`` if pyclipr is
    not available — there is **no axis-aligned fallback** because
    offset on rectangles is not the common case for trap.

    Distance in PDF user space units (typically points)."""
```

**Consumed by**: Compile's **trap** producer for spread/choke geometry per CompilePDF spec §5.5. `polygon_intersect/union/difference` (already in 1.4.x) are insufficient — they don't grow/shrink by a distance.

#### 16.2.2 New endpoint: `POST /v1/geom/offset`

**File**: `src/codex_pdf/api/main.py`

Request body:

```json
{
  "path": { /* existing Path.to_json() shape */ },
  "distance_pt": 0.144,
  "join_type": "round",
  "miter_limit": 4.0,
  "end_type": "closed-polygon"
}
```

Response body:

```json
{
  "schema_version": "1.1.0",
  "path": { /* offset Path.to_json() shape */ }
}
```

**Errors**:
- 400 if `path` cannot be parsed
- 422 if `distance_pt` is not finite or exceeds `±100` pt
- 501 with `Code: pyclipr_not_installed` if the `[geom]` extra is missing on the server

#### 16.2.3 `TileGrid` extensions

**File**: `src/codex_pdf/geom/tile.py`

Six additive fields on the existing dataclass:

```python
cell_rotation: float = 0.0
"""Uniform per-cell rotation in degrees (0/90/180/270). Default 0.
Applied around the cell's center."""

cell_rotation_pattern: list[float] | None = None
"""Per-cell cyclic rotation list. Cycles if shorter than total
cell count. Takes precedence over `cell_rotation` when set."""

flip_per_row: Literal["none", "horizontal", "vertical", "alternating-h", "alternating-v"] = "none"
"""- "none"          — no flipping
- "horizontal"      — every row h-flipped
- "vertical"        — every row v-flipped
- "alternating-h"   — rows 1, 3, 5, … h-flipped (work-and-turn)
- "alternating-v"   — rows 1, 3, 5, … v-flipped (work-and-tumble)
The row-numbering convention (rows 1, 3, 5, … as the flipped set)
is press-floor-validated; CompilePDF gate 3-B locks the convention
before scaffolding."""

flip_pattern: list[Literal["none", "h", "v"]] | None = None
"""Per-row cyclic flip list. Takes precedence over `flip_per_row`."""

bleed_handling: Literal["overlap", "added-per-cell"] = "added-per-cell"
"""- "added-per-cell" (default) — each cell carries its own bleed
                                    envelope; cells positioned
                                    `gutter + 2*bleed` apart between
                                    trim-box edges
- "overlap"                    — cells share bleed; positioned
                                    `cell_width + gutter` apart
                                    (continuous patterns)"""

bleed: float = 0.0
"""Uniform bleed distance in PDF user space units (points)."""
```

#### 16.2.4 `CellPlacement` dataclass

**File**: `src/codex_pdf/geom/tile.py`

```python
@dataclass
class CellPlacement:
    box: Box
    """Cell position on the sheet."""

    rotation: float
    """Applied rotation 0/90/180/270."""

    flip_h: bool
    flip_v: bool

    row: int
    col: int

    # Box-compatibility forwarding (so existing consumers reading
    # `result.cells[i].x0` etc. keep working):
    @property
    def x0(self) -> float: return self.box.x0
    @property
    def y0(self) -> float: return self.box.y0
    @property
    def x1(self) -> float: return self.box.x1
    @property
    def y1(self) -> float: return self.box.y1
```

#### 16.2.5 `TileResult.cells` shape change

**Before** (1.0.0): `cells: list[Box]`
**After** (1.1.0): `cells: list[CellPlacement]`

`CellPlacement` MUST forward `.x0/.y0/.x1/.y1` plus `.area()` / `.contains()` etc. to its inner `box` so existing consumers reading `result.cells[i]` as a Box continue to work without edits. This is a true additive change — existing code paths see no behavioral difference; new code accesses `.rotation` / `.flip_h` / `.flip_v` / `.row` / `.col` for the new fields.

#### 16.2.6 `tile_grid()` honors the new knobs

**File**: `src/codex_pdf/geom/tile.py`

`tile_grid(grid: TileGrid)` MUST:
- Compute cell positions honoring `bleed_handling` (`added-per-cell` = trim-edge gap of `gutter + 2*bleed`; `overlap` = trim-edge gap of `gutter`)
- Apply per-cell rotation from `cell_rotation` (uniform) or `cell_rotation_pattern` (cyclic; takes precedence)
- Apply per-row flips from `flip_per_row` or `flip_pattern` (cyclic; takes precedence)
- Populate `CellPlacement.{rotation, flip_h, flip_v, row, col}` for every emitted cell

#### 16.2.7 `POST /v1/geom/tile` response shape change

Additive fields on each cell:

```json
{
  "schema_version": "1.1.0",
  "rows": 4, "cols": 2, "used": 0.78, "waste": 0.22,
  "cells": [
    {
      "x0": 36, "y0": 36, "x1": 296, "y1": 432,
      "rotation": 0, "flip_h": false, "flip_v": false,
      "row": 0, "col": 0
    }
  ]
}
```

Existing consumers that destructure `cells[i]` as a Box continue working (the `x0/y0/x1/y1` keys are still present at the top level of each cell entry).

#### 16.2.8 Geom tests

- Unit: `polygon_offset` round/miter/bevel join types on a known rectangular fixture; verify monotonicity (positive distance grows, negative shrinks)
- Unit: `polygon_offset` raises `NotImplementedError` when pyclipr unavailable
- Unit: `tile_grid` with `cell_rotation = 90`, with `flip_per_row = "alternating-h"`, with `bleed_handling = "overlap"` — one fixture per knob
- Unit: `CellPlacement.x0` / `.y0` / `.x1` / `.y1` forward correctly
- Contract: existing `TileResult.cells[i].x0` access pattern keeps working; new `.rotation` / `.flip_h` / `.flip_v` are populated
- HTTP: `POST /v1/geom/offset` for each join type; 501 path when `[geom]` extra missing
- HTTP: `POST /v1/geom/tile` returns the additive fields

### 16.3 Top-level `codex-document` schema (1.0.0 → 1.1.0)

Both fields are already documented in §1 (`Document-level data`) of this reference:

- `is_linearized` — see §1 row "is_linearized"; consumed by Compile **rewrite** verifier per CompilePDF spec §2.3
- `info_dict.custom` — see §1 row "info_dict.custom"; consumed by Compile **rewrite** for lineage breadcrumb round-trip per CompilePDF spec §1.7b

This sub-section exists only to anchor the codex-document section bump alongside its sibling color and geom bumps; the actual data-shape requirements for both fields are listed once, in §1.

### 16.4 Server-side cross-cutting (no schema bump)

These two land independent of the section bumps; they support multi-instance operation and cross-service tracing.

#### 16.4.1 `instance_id` field on `HealthResponse`

**File**: `src/codex_pdf/api/main.py`

```python
class HealthResponse(BaseModel):
    status: str
    version: str
    ghostscript: bool
    cache_backend: str
    instance_id: str    # ← new
```

Resolution:

```python
def _resolve_instance_id() -> str:
    explicit = os.environ.get("CODEX_INSTANCE_ID", "").strip()
    if explicit:
        return explicit
    return socket.gethostname() or "unknown"

INSTANCE_ID = _resolve_instance_id()
```

Wire into the `/healthz` and `/v1/healthz` handlers.

**Consumed by**: all consumers (Lint, Compile, marketing sites) for multi-instance rollout visibility — the codex client SDK already supports plant affinity routing, but operators need per-replica identity on healthchecks to drain stragglers cleanly.

#### 16.4.2 FastAPI request-id middleware

**File**: `src/codex_pdf/api/middleware.py` (NEW — currently absent)

```python
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Codex-Request-Id") or secrets.token_hex(8)
        request.state.request_id = request_id
        # bind to structlog context vars for correlated logging
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            instance_id=INSTANCE_ID,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["X-Codex-Request-Id"] = request_id
        response.headers["X-Codex-Instance-Id"] = INSTANCE_ID
        return response
```

Mount via `app.add_middleware(RequestIdMiddleware)` in `main.py`.

**Rationale**: the client SDK already generates / sends `X-Codex-Request-Id` per request (`http_client.py:213`). Today the server ignores it; lint→codex chains lose the ID at the server boundary. This closes the loop so a single `request_id` queries from upstream (lint, compile, marketing) all the way through to Codex's logs and metrics.

#### 16.4.3 Cross-cutting tests

- Unit: `/healthz` returns `instance_id` populated from env or hostname
- Unit: middleware echoes `X-Codex-Request-Id` from the incoming request when supplied
- Unit: middleware generates a fresh request_id when none supplied
- Unit: `X-Codex-Instance-Id` always present in response headers
- Integration: deploy 2 replicas behind a load balancer; verify `instance_id` differs across replicas; verify request_id flows end-to-end through structured log capture

### 16.5 Section bumps and version coordination

| Section | From | To | Source of bump |
|---|---|---|---|
| `COLOR_SCHEMA_VERSION` | `1.0.0` | `1.1.0` | §16.1 ND fields + endpoint |
| `GEOM_SCHEMA_VERSION` | `1.0.0` | `1.1.0` | §16.2 polygon_offset + TileGrid extensions + CellPlacement |
| top-level `codex-document` | `1.0.0` | `1.1.0` | §1 (is_linearized + info_dict.custom) anchored here as §16.3 |
| `codex_pdf.version.VERSION` | `1.4.2` | `1.5.0` | Coordinated minor bump |
| npm `@printwithsynergy/codex-client` | `1.4.2` | `1.5.0` | Mirrors Python wheel version; adds `geomOffset` and `colorNeutralDensity` methods |

`/v1/contract.section_schema_versions` MUST report the bumped versions verbatim. Existing client-side contract guards (`http_client.py:435-476`) consume this map to auto-route traffic during partial rollouts.

### 16.6 Optimal PR sequence

For the executing Codex agent — each PR runs the existing CI (ruff + mypy + pytest + `scripts/produce_surface_audit.py`); all must pass before merge.

| PR | Scope | Unblocks |
|---|---|---|
| 1 | §16.4.1 + §16.4.2 — `instance_id` + request-id middleware (no schema bump) | Compile chassis /healthz parity; multi-instance Codex operation for Lint and all consumers |
| 2 | §16.3 — top-level `codex-document` 1.1.0 (`is_linearized` + `info_dict.custom`) | Compile **rewrite** post-condition verify (§2.3 of CompilePDF spec) |
| 3 | §16.2.3–16.2.7 — geom 1.1.0 TileGrid extensions + CellPlacement | Compile **impose** producer (§4.1) |
| 4 | §16.2.1 + §16.2.2 — `polygon_offset` + `POST /v1/geom/offset` (still geom 1.1.0; can fold into PR 3) | Compile **trap** pure_python engine (§5.5) |
| 5 | §16.1.1 + §16.1.2 + §16.1.3 — color 1.1.0 ND fields + inkbook ND + endpoint | Compile **trap** ND lookup (§5.2) |
| 6 | §16.1.4 — Pantone catalog ND data population | Production-grade trap measurements (can lag schema landing) |
| 7 | Bump `codex_pdf.version.VERSION = "1.5.0"`; publish to PyPI; bump `@printwithsynergy/codex-client@1.5.0`; publish to npm; tag `codex-pdf v1.5.0` | Final 1.5.0 release |

### 16.7 Acceptance criteria

Codex 1.5.0 is "done" when:

- [ ] All deliverables in §16.1, §16.2, §16.3, §16.4 land and pass CI on `main`
- [ ] `codex_pdf.version.VERSION = "1.5.0"` published to PyPI
- [ ] `@printwithsynergy/codex-client@1.5.0` published to npm with new methods (`geomOffset`, `colorNeutralDensity`)
- [ ] `GET /v1/contract.section_schema_versions` reports `{"color": "1.1.0", "geom": "1.1.0", "codex-document": "1.1.0"}` on every live instance
- [ ] `GET /healthz` includes `instance_id` populated from env or hostname
- [ ] `X-Codex-Request-Id` flows end-to-end (incoming request → server log → response header)
- [ ] Two-replica staging deploy in one Railway plant (per APPR-2026-05-09-34) shows: distinct `instance_id` per replica; cache hits across replicas via shared Redis; client contract guard routes correctly during simulated rolling upgrade
- [ ] CHANGELOG entry for `codex-pdf v1.5.0` lists the additive bumps, new endpoints, and operator-visible behavior
- [ ] `scripts/produce_surface_audit.py` green throughout

After all of the above, **Compile** Phase 1 (rewrite engine) can begin its implementation against Codex 1.5.0.

### 16.8 Operating constraints

The Codex agent MUST respect these throughout the 1.5 work:

1. **Read-only invariant**. `produce_surface_audit.py` fails CI on any banned writer signal. None of the deliverables above introduce a write path. The `polygon_offset` function is pure geometry math; it does not write PDF bytes. The single allowlisted save site stays `codex_pdf.render._common.apply_ocg_overrides`.
2. **Additive only** within current major. Every field, method, and endpoint above is *added*. Nothing existing is renamed, removed, or has its semantics changed. Lint analyzers and Loupe viewers continue working without code changes after the bump rolls out.
3. **Section bumps reflect inline on responses**. Every endpoint that includes `schema_version` in its response must report the bumped value: `/v1/color/*` → `1.1.0`, `/v1/geom/*` → `1.1.0`, `/v1/extract` → `1.1.0`.
4. **Multi-instance contract guard auto-routes** during rollout. With APPR-34's 2-replica staging, a partial rollout has one replica at 1.5.0 and one at 1.4.2. Compile (and Lint) clients pin `CODEX_REQUIRED_SECTION_VERSIONS = {"color": "1.1.0", "geom": "1.1.0"}`; the client guard auto-routes to the 1.5.0 replica until both replicas are upgraded. Document this in the deploy runbook so operators know mid-rollout traffic shifts are mechanical, not a bug.
5. **Cache-key invalidation is automatic**. Compile's cache key (per `compile_pdf.cache.compute_cache_key`) includes `color_schema_version`, `geom_schema_version`, and `codex_document_schema_version`. The bumps invalidate Compile's cached outputs cleanly; expect a recompute storm proportional to the cached-job population for affected producers.

---

## Out of scope

The following are explicitly not PDF data requirements — they are handled by separate systems:

- **External import parsers** (`pitstop_xml`, `callas_json`, `callas_xml`, `acrobat_xml`, `lintpdf_json`): These parse third-party preflight report files, not the PDF itself. See [integrations.md](integrations.md).
- **Viewer tile data**: Page tiles rendered for the LoupePDF viewer are produced by the tile-warmer worker after job completion. They are viewer infrastructure, not analyzer input.
- **Webhook payloads**: Outbound event payloads are derived from job results, not PDF content.
