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

```
PDF file bytes
    │
    ▼
pikepdf parser
    │   extracts raw dictionaries, streams, page tree
    ▼
SemanticModel builder          ContentStream interpreter
    │   resolves inheritance,      │   walks operators, emits
    │   normalises fonts/images/   │   typed events per operator
    │   color spaces, page boxes   │
    ▼                              ▼
SemanticDocument            list[ContentStreamEvent]
    │                              │
    └──────────┬────────────────────┘
               ▼
        AnalyzerContext
        ├── document       (SemanticDocument)
        ├── events         (list[ContentStreamEvent])
        ├── pdf_bytes      (raw bytes, lazy-loaded)
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
| `SemanticDocument` | Document structure, pages, fonts, images, color spaces | CPU · GPU · EXTERNAL_AI |
| `ContentStreamEvents` | Interpreted rendering operations (text, path, image, color, overprint, …) | CPU |
| `pdf_bytes` | Raw file bytes | CPU (file size, barcode heuristics) · GPU (zxing decode) |
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
| `metadata_stream` | Catalog `/Metadata` — raw XMP bytes | `MetadataAnalyzer`, `MetadataAuditAnalyzer` |
| `catalog` | Document catalog dictionary | `MetadataAnalyzer`, `StructureAnalyzer`, `AccessibilityAnalyzer` |
| `catalog[/ViewerPreferences]` | Viewer preference dictionary | `MetadataAnalyzer` |
| `catalog[/Lang]` | Document language string | `MetadataAnalyzer` |
| `catalog[/MarkInfo]` | Marked PDF flags (Marked, UserProperties, Suspects) | `AccessibilityAnalyzer` |
| `catalog[/StructTreeRoot]` | Tagged-PDF structure tree root | `AccessibilityAnalyzer`, `StructureAnalyzer` |
| `catalog[/AcroForm]` | Interactive form root dictionary | `StructureAnalyzer`, `DocumentAnalyzer` |
| `catalog[/OCProperties]` | Optional content layer configuration | `StructureAnalyzer` |
| `catalog[/Outlines]` | Bookmark/outline tree root | `StructureAnalyzer` |
| `catalog[/NeedsRendering]` | XFA form render flag | `DocumentAnalyzer` |
| `output_intents` | Catalog `/OutputIntents` array — each entry: OutputCondition, OutputConditionIdentifier, RegistryName, DestOutputProfile (ICC stream) | `IccProfileAnalyzer`, `ColorAnalyzer`, `GamutAnalyzer` |
| `trailer` | Raw PDF trailer dictionary | `DocumentAnalyzer` |
| `dieline_result` | Pre-computed dieline detection result (attached at ingest time) | `DielineIso19593Analyzer`, `DielinePerfIndicatorAnalyzer`, `PackagingAnalyzer` |

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
| `rotate` | `/Rotate` (inherited; 0 / 90 / 180 / 270) | `PageGeometryAnalyzer`, all spatial analyzers |
| `user_unit` | `/UserUnit` (default 1.0 = 1/72 in) | All geometry checks |
| `resources` | `/Resources` dictionary (raw) | Parser base; resolved into typed collections below |
| `content_stream` | Concatenated, decompressed page content stream bytes | Content stream interpreter |
| `transparency_group` | `/Group` dictionary on the page | `TransparencyAnalyzer` |

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
| `embedded` | Font program stream presence (`/FontFile`, `/FontFile2`, `/FontFile3`) | Required for embedding checks |
| `subset` | Subset prefix pattern in `base_font` | 6 uppercase chars + `+` |
| `encoding` | `/Encoding` | `WinAnsiEncoding`, `Identity-H`, `MacRomanEncoding`, etc. |
| `font_descriptor` | `/FontDescriptor` dictionary | Flags, FontBBox, ItalicAngle, Ascent, Descent, CapHeight, XHeight, StemV, StemH, MissingWidth |
| `has_to_unicode` | `/ToUnicode` CMap stream presence | Required for text-extraction / accessibility checks |
| `cid_system_info` | `/CIDSystemInfo` | Registry, Ordering, Supplement — CID fonts only |

**Consumed by:** `FontAnalyzer` (`LPDF_FONT_*`), `TextMetricsAnalyzer`, `LegibilityCompositeAnalyzer`, `PlaceholderTextAnalyzer`, AI pharma/regulatory analyzers (`AI_PHARMA_*`, `AI_FDA_*`).

---

## 4. Image data (`PdfImage`)

One `PdfImage` object per image XObject or inline image on each page. Placement geometry comes from `ImagePlacedEvent` (see section 8).

| Field | PDF source | Notes |
|---|---|---|
| `name` | Resource key or `inline_N` | Identifies image within page resources |
| `width` | `/Width` | Pixel columns |
| `height` | `/Height` | Pixel rows |
| `bits_per_component` | `/BitsPerComponent` | 1, 2, 4, 8, or 16 |
| `color_space` | `/ColorSpace` (resolved) | Full `PdfColorSpace` object |
| `filters` | `/Filter` (ordered) | `FlateDecode`, `DCTDecode`, `JBIG2Decode`, `CCITTFaxDecode`, `JPXDecode`, `RunLengthDecode`, `LZWDecode` |
| `has_soft_mask` | `/SMask` stream presence | Transparency |
| `has_hard_mask` | `/Mask` as stream (not color key) | Hard clipping mask |
| `interpolate` | `/Interpolate` | Bilinear upscaling enabled |
| `intent` | `/Intent` | Per-image rendering intent override |
| `inline` | Inline image (`BI`/`ID`/`EI`) vs XObject | Affects stream re-use |
| `has_opi` | `/OPI` dictionary presence | OPI proxy; low-res placeholder |
| Placement CTM | From `ImagePlacedEvent.ctm` (see §8) | Required for effective DPI calculation |

**Consumed by:** `ImageAnalyzer` (`LPDF_IMG_*`), `IccProfileAnalyzer` (`LPDF_ICC_*`), `EpmTierCAnalyzer`, GPU image-quality analyzer, NSFW detector, logo detection.

---

## 5. Color space data (`PdfColorSpace`)

One `PdfColorSpace` per named color space on each page, plus inline color space objects embedded in image and content stream operators.

| Field | PDF source | Notes |
|---|---|---|
| `cs_type` | Color space name or array type | `DeviceRGB`, `DeviceCMYK`, `DeviceGray`, `ICCBased`, `CalRGB`, `CalGray`, `Lab`, `Indexed`, `Separation`, `DeviceN`, `NChannel`, `Pattern` |
| `components` | Derived from cs_type or profile | Number of color components |
| `colorant_names` | First element of `Separation` or `DeviceN` array | Spot color names; central for ink inventory |
| `icc_profile_ref` | Stream reference inside `ICCBased` array | Resolved to ICC profile bytes |
| `alternate` | Alternate color space (for `Separation`, `DeviceN`, `ICCBased`) | Fallback for rendering |
| `base_space` | Base space for `Indexed` | Underlying full color space |

**Consumed by:** `ColorAnalyzer` (`LPDF_COLOR_*`), `SpotColorAnalyzer` (`LPDF_SPOT_*`), `IccProfileAnalyzer` (`LPDF_ICC_*`), `GamutAnalyzer`, `InkCoverageAnalyzer` (`LPDF_INK_*`), `DuplicateProcessSpotAnalyzer`, `SpotNameSimilarityAnalyzer`, `SoloSpotVerifyAnalyzer`, `AdvancedColorAnalyzer` (`LPDF_ADV_*`), `ColorInventoryAuditAnalyzer`, `EpmAnalyzer` / `EpmTierA/B/CAnalyzer`.

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

## Out of scope

The following are explicitly not PDF data requirements — they are handled by separate systems:

- **External import parsers** (`pitstop_xml`, `callas_json`, `callas_xml`, `acrobat_xml`, `lintpdf_json`): These parse third-party preflight report files, not the PDF itself. See [integrations.md](integrations.md).
- **Viewer tile data**: Page tiles rendered for the LoupePDF viewer are produced by the tile-warmer worker after job completion. They are viewer infrastructure, not analyzer input.
- **Webhook payloads**: Outbound event payloads are derived from job results, not PDF content.
