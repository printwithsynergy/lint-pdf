# 02: PDF Object Model & Document Structure

**Research Deliverable** — Grounded Preflight Engine | Based on ISO 32000-2:2020 Chapter 7

---

## Nine Basic Object Types

Per §7.3.1, PDF defines nine basic object types. All are direct objects except streams and indirect objects, which must follow indirect object syntax (n m obj ... endobj):

### 1. Boolean Objects (§7.3.2)
- Keywords: `true`, `false`
- Preflight: Validate syntax in graphics state, dictionary values
- Use: Graphics state flags (overprint, etc.)

### 2. Numeric Objects (§7.3.3)
- Integer: signed decimal digits (no radix notation, no exponents)
- Real: decimal digits with PERIOD, optional sign
- Preflight: Validate ranges (coordinates, opacity, scales)
- Examples: `123`, `-98`, `34.5`, `-.002`

### 3. String Objects (§7.3.4)
**Two representations:**
- **Literal strings:** parentheses with escape sequences (§7.3.4.2) — backslash escapes \n, \r, \t, \b, \f, (, ), \
- **Hexadecimal strings:** angle brackets <> with hex pairs (§7.3.4.3) — odd-length padded with 0

Encoding (§7.9.2):
- PDFDocEncoding (standard) or UTF-16BE for special chars
- String contents in streams/dictionaries interpreted per context

Preflight: Validate parentheses balance in literal strings, valid hex in hex strings

### 4. Name Objects (§7.3.5)
- Syntax: forward slash + name sequence (e.g., `/Type`, `/Font`)
- No spaces; delimited by whitespace or special chars
- Preflight: Validate name syntax, check dictionary key names against spec

### 5. Array Objects (§7.3.6)
- Delimited by `[` and `]`
- Elements can be any object type (direct or indirect references)
- Preflight: Validate array lengths (e.g., color space arrays, transformation matrices)

### 6. Dictionary Objects (§7.3.7)
- Delimited by `<<` and `>>`
- Key-value pairs: name key + any object value
- Indirect references common for complex values
- Preflight: Validate required keys, validate value types per key specs

### 7. Stream Objects (§7.3.8)
**Requirements per §7.3.8:**
- Must be indirect objects
- Dictionary + `stream` keyword + binary data + `endstream`
- Dictionary contains:
  - `Length`: integer (stream data byte count, required)
  - `Filter`: array or name identifying decompression filter(s)
  - `DecodeParms`: array or dictionary of filter parameters

**Filters (§7.4):**
- `ASCIIHexDecode` (§7.4.2): Hex representation
- `ASCII85Decode` (§7.4.3): Abbreviated base-85
- `LZWDecode` / `FlateDecode` (§7.4.4): Compression
- `RunLengthDecode` (§7.4.5): Run-length encoding
- `CCITTFaxDecode` (§7.4.6): CCITT Group 3/4 fax
- `JBIG2Decode` (§7.4.7): JBIG2 image compression
- `DCTDecode` (§7.4.8): JPEG/DCT compression
- `JPXDecode` (§7.4.9): JPEG 2000 compression

Preflight: Validate Filter entries exist, test decompression, verify Length accuracy

### 8. Null Object (§7.3.9)
- Keyword: `null`
- Effect: Equivalent to omitting dictionary entry (per §7.3.9)
- Preflight: Acceptable in dictionaries; validate interpretation

### 9. Indirect Objects (§7.3.10)
- Syntax: `n m obj ... endobj` where n=object number, m=generation
- Reference syntax: `n m R` (reference to object n, generation m)
- Xref/xref stream must index all indirect objects
- Preflight: Validate all references resolve to actual objects, no circular references (except page tree parent)

---

## Indirect Object Rules

Per §7.3.10 and §7.5.3:

**Object Numbering:**
- Objects numbered starting at 0
- Each object has unique number
- Generation number tracks modifications (incremental updates)

**Reference Resolution:**
1. Locate object in xref table/stream
2. Seek to byte offset
3. Read `n m obj` header
4. Parse object data
5. Read `endobj` terminator

**Preflight Checks:**
- All n m R references have n, m in xref
- Object number matches xref entry
- Generation number matches if xref has multiple versions
- No undefined object references

---

## Document Catalog (§7.7.2)

**Root of Document Hierarchy**

Located via `/Root` entry in trailer (§7.5.5). Must be indirect reference.

**Catalog Dictionary (Table 29, §7.7.2)**

| Key | Type | Required | Purpose |
|-----|------|----------|---------|
| Type | name | YES | Must be `/Catalog` |
| Version | name | NO | PDF version (e.g., `/1.4`). Overrides header if present |
| Pages | dict (indirect ref) | YES | Root of page tree (§7.7.3) |
| PageLabels | number tree | NO | Page label dictionaries |
| Names | dict | NO | Named destinations, embedded files |
| Dests | dict | NO | Named destinations (legacy) |
| ViewerPreferences | dict | NO | Display preferences |
| PageMode | name | NO | `UseNone`, `UseOutlines`, `UseThumbs`, `UseOC` |
| PageLayout | name | NO | `SinglePage`, `OneColumn`, `TwoColumnLeft`, etc. |
| Outlines | dict (indirect ref) | NO | Document outline (bookmarks) |
| Threads | array | NO | Article threads |
| OpenAction | array/dict | NO | Initial view action |
| AA | dict | NO | Document-level actions |
| URI | dict | NO | URI base for document |
| AcroForm | dict | NO | Interactive form field resources |
| Metadata | stream (indirect ref) | NO | Document metadata (XMP) |
| StructTreeRoot | dict (indirect ref) | NO | Tagged PDF structure tree |
| MarkInfo | dict | NO | Tagged PDF mark information |
| Lang | string | NO | Document language (e.g., "en-US") |
| SpiderInfo | dict | NO | Web capture information |
| OutputIntents | array | NO | Output intent specifications |
| PieceInfo | dict | NO | Piece dictionary for incremental updates |
| Permissions | dict | NO | Permission restrictions (legacy) |
| Legal | dict | NO | Legal notices |
| Requirements | array | NO | Required PDF features |
| Collection | dict | NO | Collection schema (PDF 1.7) |
| Needs | dict | NO | File attachment annotation schema |
| AF | array | NO | Associated files (PDF 2.0) |
| DPartRoot | dict | NO | Distributed parameters root |

**Preflight Checks (§7.7.2):**
- Type must be `/Catalog`
- Pages entry must be indirect reference to page tree
- Version (if present) must be name, not number (e.g., `/1.4` not `1.4`)
- Verify all indirect references in optional entries exist in xref
- For tagged PDF: StructTreeRoot must have valid structure elements

---

## Page Tree (§7.7.3)

**Intermediate Structure:**
Hierarchical tree of page dictionaries. Root is referenced from Catalog `/Pages`. Enables efficient page lookup without loading all pages.

**Page Tree Node Dictionary (Table 30, §7.7.3)**

**Intermediate Nodes (Type=/Pages):**
| Key | Type | Required | Purpose |
|-----|------|----------|---------|
| Type | name | YES | Must be `/Pages` |
| Parent | dict (indirect ref) | YES (except root) | Parent node |
| Kids | array | YES | Array of page dictionaries or intermediate nodes |
| Count | integer | YES | Total number of leaf pages under this node |

**Leaf Nodes (Type=/Page):** See next section

**Page Tree Rules (§7.7.3):**
- Root Pages node (from Catalog) has Count = total pages in document
- Each intermediate node Count = sum of Kids node Counts
- Kids array contains indirect references to child nodes
- Tree depth helps balance page access

**Preflight Checks (§7.7.3):**
- Root Pages node referenced from Catalog
- All nodes have Type=/Pages or Type=/Page
- Count values consistent with Kids array lengths
- No circular references (parent loops)
- All indirect references valid

---

## Page Objects (§7.7.4)

**Leaf Level of Page Tree**

Each page is a dictionary with page-specific attributes and content stream.

**Page Dictionary (Table 31, §7.7.4)**

| Key | Type | Required | Purpose |
|-----|------|----------|---------|
| Type | name | YES | Must be `/Page` |
| Parent | dict (indirect ref) | YES | Parent page tree node |
| MediaBox | rectangle | YES | Default page size (lower-left + upper-right) |
| CropBox | rectangle | NO | Visible page region (default = MediaBox) |
| BleedBox | rectangle | NO | Intended clipping region for printing |
| TrimBox | rectangle | NO | Intended page dimensions after trimming |
| ArtBox | rectangle | NO | Intended extent of page's live area |
| Contents | stream/array | NO | Page content stream(s) |
| Resources | dict | NO | Resource dictionaries (fonts, images, etc.) |
| Rotate | integer | NO | Page rotation: 0, 90, 180, 270 degrees |
| Group | dict | NO | Transparency group attributes |
| Annots | array | NO | Annotation dictionaries |
| Dur | number | NO | Duration for presentation mode |
| Transition | dict | NO | Page transition effect |
| Thumb | stream | NO | Thumbnail image |
| B | array | NO | Beads for articles |
| StructParents | integer | NO | Structure parent tree entry (tagged PDF) |
| Tabs | name | NO | Tab order preference |
| UserUnit | number | NO | User space unit scale (≥0, default 1.0) |

**Five Box Types (§7.7.4, Table 31):**

All boxes are arrays: [lower_left_x, lower_left_y, upper_right_x, upper_right_y]

1. **MediaBox** (required): Page physical dimensions
2. **CropBox** (optional, default=MediaBox): Visible page area
3. **BleedBox** (optional, default=CropBox): Clipping region for printing
4. **TrimBox** (optional, default=CropBox): Trimmed page size
5. **ArtBox** (optional, default=CropBox): Live content area

**Rotation (§7.7.4):**
- 0: portrait (normal)
- 90: rotated 90° clockwise
- 180: upside-down
- 270: rotated 90° counter-clockwise

**Preflight Checks (§7.7.4):**
- Type must be `/Page`
- Parent must reference valid page tree node
- MediaBox required and valid rectangle [x1 y1 x2 y2] with x1 < x2, y1 < y2
- CropBox <= MediaBox (if present)
- BleedBox <= CropBox (if present)
- TrimBox <= CropBox (if present)
- ArtBox <= CropBox (if present)
- Rotate in [0, 90, 180, 270]
- UserUnit > 0 (if present)
- Contents (if present) is stream or array of streams
- Resources (if present) is dictionary with Font, XObject, ColorSpace, etc.

---

## Resource Inheritance (§7.8.2–7.8.3)

**Resource Dictionary Structure (§7.8.3, Table 32–48)**

Resources can appear at:
- Page level (Page /Resources entry)
- Form XObject level (Form /Resources entry)
- Content stream level (via gs operator + ExtGState)

**Standard Resource Types:**
- `Font`: Dictionary of font dictionaries
- `XObject`: Dictionary of external objects (images, forms)
- `ColorSpace`: Dictionary of color space definitions
- `Pattern`: Dictionary of pattern definitions
- `Shading`: Dictionary of shading definitions
- `ExtGState`: Dictionary of graphics state parameter dictionaries
- `Properties`: Dictionary of marked-content properties

**Inheritance Rule (§7.8.2):**
When a content stream references a resource by name (e.g., `/F1` for a font), the viewer searches:
1. Current content stream's /Resources (if defined)
2. Parent Form XObject's /Resources (if applicable)
3. Page's /Resources

First match is used. If not found, behavior is undefined (error or substitution).

**Preflight Checks:**
- Verify all resource names in content stream are defined in Resources
- Font /F1, /F2, etc. must exist in Resources /Font
- Image /Im1, /Im2, etc. must exist in Resources /XObject
- ColorSpace /CS1, /CS2, etc. must exist in Resources /ColorSpace
- Check inheritance chain for Form XObjects

---

## Graphics State Parameter Dictionary (§8.4.5)

Referenced via `gs` operator in content streams. Contains graphics state parameters that cannot be set directly.

**Common Entries (Table 51, §8.4.5):**
- `LW` (line width)
- `LC` (line cap style)
- `LJ` (line join style)
- `ML` (miter limit)
- `D` (dash pattern)
- `RI` (rendering intent)
- `OP` (overprint for stroking)
- `op` (overprint for non-stroking)
- `OPM` (overprint mode: 0 or 1)
- `Font` ([font_dictionary, size])
- `BG` / `BG2` (black generation functions)
- `UCR` / `UCR2` (undercolor removal functions)
- `TR` / `TR2` (transfer functions)
- `HT` (halftone dictionary)
- `FL` (flatness tolerance)
- `SM` (smoothness tolerance)
- `SA` (stroke adjustment)
- `BM` (blend mode)
- `SMask` (soft mask dictionary)
- `CA` (stroking alpha, 0.0–1.0)
- `ca` (non-stroking alpha, 0.0–1.0)
- `AIS` (alpha is shape)
- `TK` (text knockout)

**Preflight Checks:**
- /Type must be `/ExtGState`
- Font entry (if present): valid font reference + size
- CA/ca values in range [0.0, 1.0]
- BM value in valid blend mode list (16 modes + Compatible)
- SMask (if present): valid soft mask dictionary

---

## Table References

| Table | Section | Content |
|-------|---------|---------|
| Table 29 | 7.7.2 | Catalog dictionary entries |
| Table 30 | 7.7.3 | Page tree intermediate node entries |
| Table 31 | 7.7.4 | Page object entries |
| Table 32–48 | 7.8.3 | Resource dictionaries (Font, XObject, ColorSpace, Pattern, Shading, ExtGState, Properties) |
| Table 50 | 8.2 | Operator categories |
| Table 51 | 8.4.5 | Graphics state parameter dictionary entries |

---

## Feed to AI

Use this research to design LintPDF's **Object Model Validator Module**:

1. **Object Type Checker**: Validate all nine object types per §7.3.1–7.3.10
2. **Indirect Reference Resolver**: Resolve all n m R references, validate xref entries
3. **Catalog Validator**: Verify Root object is Catalog, check all required/optional entries vs Table 29
4. **Page Tree Walker**: Traverse tree structure, validate node types, check Count consistency
5. **Page Box Validator**: Check MediaBox, CropBox, BleedBox, TrimBox, ArtBox relationships
6. **Resource Locator**: Find Font, XObject, ColorSpace, etc. via inheritance chain
7. **Parameter Dictionary Checker**: Validate ExtGState entries per Table 51–52

Generate violation reports citing specific Table numbers and §7.7.x clause references. Build unified object graph with resolved references for downstream modules.

---

**Specification Version:** ISO 32000-2:2020 Chapter 7
**Date Generated:** 2026-03-11
