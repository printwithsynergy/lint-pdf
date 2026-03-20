# 06: Images in PDF

**Research Deliverable** — Grounded Preflight Engine | Based on ISO 32000-2:2020 Chapter 8

---

## Image Objects (§8.9, §8.2)

**Two Forms:**
1. **Image XObject** (§8.9): External object dictionary in Resources /XObject
2. **Inline Image** (§8.9.7): BI...ID...EI syntax in content stream

---

## Image XObject Dictionary (§8.9.5, Table 87)

**Standard Image Entries:**

| Entry | Type | Required | Purpose |
|-------|------|----------|---------|
| Type | name | YES | /XObject |
| Subtype | name | YES | /Image |
| Width | integer | YES | Image width in pixels |
| Height | integer | YES | Image height in pixels |
| ColorSpace | name/array | YES | Color space (DeviceGray, DeviceRGB, etc.) |
| BitsPerComponent | integer | YES | 1, 2, 4, 8, or 16 bits/pixel per component |
| Intent | name | NO | Rendering intent |
| Decode | array | NO | [in1_min in1_max ... out_min out_max] color mapping |
| ImageMask | boolean | NO | If true: stencil mask (1-bit) |
| Mask | stream/array | NO | Soft mask or color transparency |
| SMask | stream | NO | Soft mask XObject (PDF 1.4+) |
| Interpolate | boolean | NO | Smooth image during scaling (default false) |
| Intent | name | NO | Rendering intent (AbsoluteColorimetric, etc.) |
| Filter | name/array | NO | Compression filter(s) |
| DecodeParms | dict/array | NO | Filter parameters |
| Matte | array | NO | Color associated with soft mask |

**Image Data Size Calculation:**
```
ImageDataSize = (Width × Height × BitsPerComponent × NumComponents) ÷ 8 bytes
```

Where NumComponents depends on ColorSpace:
- DeviceGray, CalGray: 1
- DeviceRGB, CalRGB, Lab: 3
- DeviceCMYK: 4
- Indexed: 1 (values are indices)
- Separation, DeviceN: N components

---

## Effective Resolution (DPI) Calculation (§8.9)

**Formula:**
```
EffectiveDPI = (1 / √(|CTM_scaling|)) × 72 DPI
```

Where CTM (Current Transformation Matrix) element from content stream determines scaling.

**Step-by-step:**
1. Extract image Width, Height (pixels)
2. Track CTM from `cm` operators in content stream
3. Calculate CTM determinant: det = a×d - b×c
4. CTM scale factor = √(det)
5. EffectiveDPI = 72 / CTM_scale

**Example:**
- Image: 100 × 100 pixels
- CTM applied: 0.5 × 0.5 scale (inserted via cm operator)
- CTM determinant = 0.25, √0.25 = 0.5
- EffectiveDPI = 72 / 0.5 = 144 DPI

**Printing Implications:**
- DPI < 150: Low resolution, visible pixelation
- DPI 150–300: Acceptable for print
- DPI > 300: High quality (may be overkill)

**Preflight Checks:**
- Extract Width × Height from image dictionary
- Track CTM accumulation through content stream
- Calculate effective DPI at point of image rendering
- Warn if DPI << 150 for print documents
- Report DPI < 72 as critical issue

---

## Compression Filters (§7.4)

All filters can compress image data:

| Filter | Type | Use | Decompression |
|--------|------|-----|-----------------|
| FlateDecode | Lossless ZIP | Most common | RFC 1951 (deflate) |
| ASCIIHexDecode | Text representation | Debugging | ASCII hex → binary |
| ASCII85Decode | Text representation | Debugging | Base-85 → binary |
| LZWDecode | Lossless LZW | Legacy | LZW algorithm |
| RunLengthDecode | Run-length encoding | Bilevel | RLE algorithm |
| CCITTFaxDecode | Group 3/4 fax | Bilevel | CCITT Fax |
| JBIG2Decode | JBIG2 compression | Bilevel | JBIG2 decoder |
| DCTDecode | JPEG | Photographic | JPEG decoder |
| JPXDecode | JPEG 2000 | Advanced | JPEG 2000 decoder |

**Preflight Checks:**
- Filter entry present (name or array of names)
- Filter names valid (from above list)
- DecodeParms (if present): dictionary or array of dictionaries, one per filter
- Filter chains allowed: multiple filters applied left-to-right

**DCTDecode (JPEG) Special Notes (§7.4.8):**
- Contains embedded JPEG data (JFIF or EXIF headers)
- Loss ​y compression: decoded pixel values may differ from original
- Common for photographs

**JPXDecode (JPEG 2000) Special Notes (§7.4.9):**
- Modern compression, better quality than DCT
- Requires JPEG 2000 decoder (less common)

---

## Soft Masking (SMask, §8.9.6)

**Soft Mask Dictionary:**
```
/SMask stream_reference
```

Stream contains mask image with same dimensions as main image.

**Mask Image Entries (Table 90, §8.9.6.5):**
- Type: XObject
- Subtype: Image
- Width/Height: must match parent image
- ColorSpace: DeviceGray (typically)
- BitsPerComponent: 1–8
- (Image data interpreted as opacity: 0=transparent, 255=opaque)

**Matte Entry:**
Optional array of color values "matted" with mask:
```
/Matte [R G B]  (for RGB image)
```

Affects compositing at mask edges (blending).

**Preflight Checks:**
- SMask (if present): stream with Type=XObject, Subtype=Image
- SMask Width/Height: must equal parent image Width/Height
- SMask ColorSpace: typically DeviceGray (1 component)
- Matte (if present): array length = number of components in parent ColorSpace

---

## Stencil Masking (ImageMask, §8.9.6.2)

**Binary Mask:**
```
/ImageMask true
/BitsPerComponent 1
```

1-bit image where:
- 0 = do not paint (transparent)
- 1 = paint current fill color

Used for creating shaped fills.

**Preflight Checks:**
- ImageMask = true ⟹ BitsPerComponent must be 1
- ColorSpace must be absent (stencil has no color space)
- Current fill color set before rendering stencil

---

## Inline Images (§8.9.7, BI...ID...EI)

**Syntax:**
```
BI
  /W width
  /H height
  /CS colorspace
  /BPC bitspercomponent
  /F filter (optional)
ID
  [image data]
EI
```

**Inline Image Parameters (abbreviated):**
- /W: /Width
- /H: /Height
- /CS: /ColorSpace
- /BPC: /BitsPerComponent
- /F: /Filter
- /IM: /Intent
- /I: /Intent (alternate short form)
- /DP: /DecodeParms

**Preflight Checks:**
- W, H: positive integers
- CS: valid color space name
- BPC: 1, 2, 4, 8, or 16
- Data size: (W × H × BPC × NumComponents) ÷ 8 bytes
- ID immediately followed by newline/whitespace before binary data
- EI properly terminated (preceded by whitespace)

---

## Image Quality Concerns

**Resolution (DPI):**
- Preflight: Calculate effective DPI per above
- Flag images with DPI < 72 (critical)
- Flag images with DPI < 150 (warning for print)

**Compression:**
- Lossy (JPEG/DCT): Quality loss, visible artifacts
- Lossless (PNG-style filters): No loss, larger file size

**Color Space:**
- RGB in CMYK document: color space mismatch (conversion needed)
- Indexed palette: ensure palette supplied

**Mask Complexity:**
- Soft masks increase rendering time
- Multiple masks compound complexity

---

## Preflight Validation Checklist

**For Each Image XObject:**
1. Type = /XObject, Subtype = /Image
2. Width, Height: positive integers
3. ColorSpace: valid name or array
4. BitsPerComponent: 1, 2, 4, 8, or 16
5. Data size: verify stream length matches calculated size
6. Filter (if present): valid filter name(s)
7. DecodeParms (if present): valid dictionary/array
8. ImageMask (if true): BitsPerComponent must be 1, no ColorSpace
9. SMask (if present): valid soft mask image
10. Matte (if present): array length correct
11. Decode array (if present): valid ranges
12. Intent (if present): valid rendering intent

**For Each Image Use:**
1. Track CTM at point of image rendering (Do operator)
2. Calculate effective DPI
3. Report if DPI outside acceptable range
4. Verify image dimensions in pixels (not scaled via CTM)

---

## Table References

| Table | Section | Content |
|-------|---------|---------|
| Table 87 | 8.9.5 | Image XObject dictionary entries |
| Table 88 | 8.9.5 | Inline image abbreviations |
| Table 89 | 8.9.6 | Image mask entries |
| Table 90 | 8.9.6.5 | Soft mask (SMask) image entries |

---

## Feed to AI

Use this research to design Grounded's **Image Analyzer Module**:

1. **Image Extractor**: Find all /XObject Type=/Image entries in Resources
2. **Image Dictionary Parser**: Validate all entries per Table 87
3. **Data Size Calculator**: Compute expected byte size, verify against stream length
4. **CTM Tracker**: Accumulate transformation matrices from cm operators
5. **DPI Calculator**: Compute effective resolution using CTM scaling
6. **Filter Decompressor**: Decompress image data using Filter + DecodeParms
7. **Mask Handler**: Validate ImageMask (1-bit) and SMask (soft mask)
8. **Inline Image Parser**: Parse BI...ID...EI blocks, validate abbreviations
9. **Quality Checker**: Flag low-DPI images, mismatched color spaces
10. **Inline Image Data Extractor**: Locate and validate image data between ID and EI

Generate violation reports citing §8.9.x sections, Table numbers, and DPI calculations.

---

**Specification Version:** ISO 32000-2:2020 Chapter 8
**Date Generated:** 2026-03-11
