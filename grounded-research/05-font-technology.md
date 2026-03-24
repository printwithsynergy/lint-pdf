# 05: Font Technology

**Research Deliverable** — Grounded Preflight Engine | Based on ISO 32000-2:2020 Chapter 9

---

## Font Organization (§9.2)

Per §9.2.1, fonts are organized as font dictionaries identifying the font program and containing supplementary information.

**Font Types (Table 108, §9.2.1):**

| Subtype | Glyph Technology | Embedding | Encoding |
|---------|------------------|-----------|----------|
| Type1 | Type 1 outlines | FontFile | SimpleFont or custom |
| TrueType | TrueType outlines | FontFile2 | SimpleFont or custom |
| Type0 | Composite (composite fonts) | N/A | CMap required |
| CIDFont | (not a font dict subtype; component of Type0) | FontFile or FontFile3 | CMap |
| Type3 | Custom glyph procedures | N/A (defined in FontDescriptor) | Custom |

**Glyph Technologies:**
- **Type 1**: PostScript-based outline format
- **TrueType**: Quadratic curves, common in Windows
- **CFF** (Compact Font Format): Type 1 in compact form, used in OpenType fonts
- **OpenType**: Container format holding either TrueType or CFF glyph technology

---

## Simple Fonts (Type1, TrueType, Type3)

### Font Dictionary Structure (§9.5, Table 109)

| Entry | Type | Required | Purpose |
|-------|------|----------|---------|
| Type | name | YES | /Font |
| Subtype | name | YES | /Type1, /TrueType, or /Type3 |
| BaseFont | name | YES | Font name (e.g., /Helvetica, /F1) |
| FirstChar | integer | NO | First character code in Widths array |
| LastChar | integer | NO | Last character code in Widths array |
| Widths | array | NO | Array of glyph widths for FirstChar..LastChar |
| FontDescriptor | dict (indirect) | NO (except Type3) | Font properties (not for base 14 fonts) |
| Encoding | name/dict | NO | Character code to glyph name mapping |
| ToUnicode | stream (indirect) | NO | Character code to Unicode CMap |

### Type1 Fonts (§9.5.2)

**FontDescriptor Entries (Table 116, §9.8.3):**
- `Type`: FontDescriptor (name)
- `FontName`: PostScript font name (e.g., Helvetica-Bold)
- `Flags`: bit flags for font properties
- `FontBBox`: [llx lly urx ury] bounding box
- `ItalicAngle`: slant angle in degrees (0 = upright)
- `Ascent`: height above baseline
- `Descent`: depth below baseline (negative)
- `CapHeight`: height of capital letters
- `StemV`: stem vertical thickness
- `FontFile`: stream containing PostScript Type 1 font program

**Embedding Detection (§9.5.2):**
- FontFile present ⟹ font embedded
- FontFile absent ⟹ font external (system font)

**Preflight Checks:**
- Type = /Font, Subtype = /Type1
- BaseFont is name
- FontDescriptor (if present): valid dictionary
- FontFile (if present): stream with valid PostScript syntax
- Encoding (if present): valid encoding dictionary or Adobe standard encoding name
- ToUnicode (if present): valid CMap

### TrueType Fonts (§9.5.3)

**FontDescriptor Entry:**
- `FontFile2`: stream containing TrueType font program (SFNT wrapper)

**SFNT Structure:**
Binary font format with tables (head, hhea, hmtx, glyf, loca, etc.).

**Preflight Checks:**
- FontDescriptor /FontFile2 stream present
- SFNT header validation (first 4 bytes: 0x00010000 or 0x74727565)
- Font tables present: head, hhea, hmtx, loca, glyf
- Glyph count matches expectedGlyph count

### Type3 Fonts (§9.6.4)

**Custom Glyph Definitions**

Font program defined in stream (not external file).

**FontDescriptor Entries:**
- `FontBBox`: required
- `FontFamily`, `FontName`: optional
- No FontFile (glyph procedures inline)

**Glyph Procedures (§9.6.4):**
- `d0`: no-op glyph (metrics only)
- `d1`: glyph with painted content

**Preflight Checks:**
- CharProcs dictionary present
- All referenced character codes have procedures in CharProcs
- Procedures use d0 or d1 operators correctly

---

## Composite Fonts (Type0, §9.7)

**Purpose:**
Multi-byte character codes for CJK and other large character sets.

### Type0 Font Dictionary (Table 113, §9.7.2)

| Entry | Type | Required | Purpose |
|-------|------|----------|---------|
| Type | name | YES | /Font |
| Subtype | name | YES | /Type0 |
| BaseFont | name | YES | Font name |
| DescendantFonts | array | YES | [CIDFont_ref] — single element |
| Encoding | name/stream | YES | Name or CMap stream |
| ToUnicode | stream (indirect) | NO | CMap: multi-byte to Unicode |

### CIDFont Dictionary (Table 114, §9.7.5)

CIDFont is component of Type0 (not standalone font dictionary).

| Entry | Type | Required | Purpose |
|-------|------|----------|---------|
| Type | name | YES | /Font |
| Subtype | name | YES | /CIDFontType0 or /CIDFontType2 |
| BaseFont | name | YES | Font name |
| CIDSystemInfo | dict | YES | Registry, Ordering, Supplement |
| FontDescriptor | dict (indirect) | YES | Font properties |
| DW | integer | NO | Default width for CID (default 1000) |
| W | array | NO | Width array for specific CIDs |

**Encoding CMap (§9.7.2):**
Maps multi-byte character codes to CID (Character Identifier).

Formats:
- Adobe standard CMap name: /Identity-H, /Identity-V (1:1 CID mapping)
- Custom CMap stream: defines arbitrary code-to-CID mapping

**ToUnicode CMap (§9.7.6):**
Maps character codes (input) to Unicode codepoints (output) for text extraction.

**Preflight Checks:**
- Type = /Font, Subtype = /Type0
- DescendantFonts: array with single CIDFont reference
- Encoding: valid CMap name or stream
- CIDFont has valid CIDSystemInfo dictionary
- FontDescriptor present with FontFile (Type 0 CID) or FontFile3 (Type 2 CID)
- ToUnicode (if present): valid CMap with identity mapping or custom range

---

## Font Embedding Detection (§9.2, §9.8.3)

**Embedding Status:**

| Font Type | FontFile | Embedded |
|-----------|----------|----------|
| Type1 | present | YES |
| Type1 | absent | NO (external system font) |
| TrueType | FontFile2 present | YES |
| TrueType | FontFile2 absent | NO |
| Type0 | FontFile/FontFile3 in CIDFont | YES |
| Type0 | FontFile/FontFile3 absent | NO |
| Type3 | (always embedded, inline) | YES |

**Preflight Detection:**
```
if FontDescriptor:
  if Type1: FontFile present?
  if TrueType: FontFile2 present?
  if Type0/CIDFont: FontFile or FontFile3 present?
else:
  embedded = FALSE (external/base 14 font)
```

**Base 14 Fonts (§9.5.2):**
14 standard PostScript fonts built into PDF readers: Times-Roman, Helvetica, Courier, Symbol, ZapfDingbats, etc.

---

## Subsetting Detection (§9.8.4)

**Subset Indicator:**
Font name prefix: `+XXXXX+FontName` where XXXXX = 6-character hash.

Example: `+F12345+Helvetica-Bold`

**Preflight:**
```
if BaseFont name starts with "+XXXXX+":
  subset = TRUE
else:
  subset = FALSE
```

**Why Important:**
Subsetted fonts contain only glyphs used in document. Smaller file size but less re-usable across documents.

---

## Encoding & Mapping (§9.5.4, §9.7.2)

**Simple Font Encoding (Type1, TrueType):**
Maps character codes (0–255 for simple fonts) to glyph names.

Types:
- **Built-in encoding**: StandardEncoding, WinAnsiEncoding, MacRomanEncoding
- **Custom Encoding dictionary**: sparse differences from base encoding

**Composite Font Encoding (Type0):**
CMap maps multi-byte sequences to CID. CIDFont maps CID to glyph.

**ToUnicode CMap (§9.7.6):**
Maps character codes to Unicode for text extraction.

**Preflight Checks:**
- Encoding (if present): valid encoding name or dictionary
- ToUnicode (if present): valid CMap stream with proper structure
- CMap syntax: valid beginbfchar/endbfchar and beginbfrange/endbfrange sections

---

## Font Operators (§9.3, Table 103)

| Operator | Operands | Purpose |
|----------|----------|---------|
| `Tf` | font size | Set current font + size (required before Tj) |

**Text Rendering (§9.4):**
After Tf sets font, text showing operators (Tj, TJ) use current font to render glyphs.

---

## Font Validation Checklist

**Required Checks:**
1. Type = /Font
2. Subtype in [/Type0, /Type1, /TrueType, /Type3]
3. BaseFont is name
4. FontDescriptor valid (if Subtype != Type3 or for base 14)
5. Character widths (FirstChar, LastChar, Widths array) consistent
6. Encoding (if present) valid
7. ToUnicode (if present) valid CMap
8. For embedded fonts: FontFile/FontFile2/FontFile3 present and streams decompress
9. For Type0: DescendantFonts contains valid CIDFont
10. For Type0: CIDFont has valid CIDSystemInfo

---

## Table References

| Table | Section | Content |
|-------|---------|---------|
| Table 108 | 9.2 | Font types |
| Table 109 | 9.5 | Font dictionary entries |
| Table 113 | 9.7.2 | Type0 font entries |
| Table 114 | 9.7.5 | CIDFont entries |
| Table 116 | 9.8.3 | FontDescriptor entries |

---

## Feed to AI

Use this research to design LintPDF's **Font Technology Validator Module**:

1. **Font Type Router**: Identify Type0, Type1, TrueType, Type3 fonts
2. **Simple Font Parser**: Validate Type1/TrueType dictionaries per §9.5
3. **Composite Font Handler**: Parse Type0/CIDFont per §9.7
4. **FontDescriptor Validator**: Check Font properties, embedding status
5. **Embedding Detector**: Verify FontFile/FontFile2/FontFile3 presence
6. **Subsetting Identifier**: Detect +XXXXX+ prefix in BaseFont
7. **Encoding Analyzer**: Validate Encoding dictionary or standard encoding name
8. **ToUnicode Parser**: Decompress and validate CMap structure
9. **Width Array Validator**: Verify FirstChar, LastChar, Widths consistency
10. **FontFile Validator**: Decompress embedded font streams, validate headers

Generate violation reports citing §9.x.y sections and Table numbers.

---

**Specification Version:** ISO 32000-2:2020 Chapter 9
**Date Generated:** 2026-03-11
