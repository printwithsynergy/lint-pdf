# ISO 32000-2:2020 Chapter 7: Syntax - Complete Index

## Extraction Details

- **Source**: ISO_32000-2:2020 (PDF 2.0 specification, sponsored by PDF Association)
- **Original Pages**: 20-141 (from 1020-page specification)
- **Extracted Content**: 291 KB, 8,155 lines
- **File**: iso32000-2-ch7-syntax.md

## Purpose

This extraction provides the complete, authoritative specification for PDF file syntax and object model. It is essential for building PDF preflight engines, validators, parsers, and processors that need to understand:

1. How PDF files are structured at the byte and object level
2. What valid PDF object types exist and their properties
3. How PDF files store and reference objects
4. How PDF documents are organized hierarchically
5. What data structures and compression formats are valid

## Chapter Structure Overview

### Section 7.1: General (Page 20)
High-level overview of PDF syntax as four interconnected parts:
- Objects (basic data types)
- File structure (how objects are stored and accessed)
- Document structure (semantic organization)
- Content streams (page drawing instructions)

### Section 7.2: Lexical Conventions (Pages 21-23)
Fundamental rules for tokenizing and parsing PDF:
- **7.2.1 General**: Bytes, tokens, and syntactic entities
- **7.2.2 Representation**: Token formation rules
- **7.2.3 Character set**: Delimiters, whitespace characters (Table 1)
- **7.2.4 Comments**: Comment syntax rules

### Section 7.3: Objects (Pages 24-33)
Detailed specifications for all 9 PDF object types:

#### 7.3.1 General
Overview of object system and type model.

#### 7.3.2 Boolean Objects
- Keywords: `true` and `false`
- Used for boolean flags and properties

#### 7.3.3 Numeric Objects
- **Integer objects**: Decimal digits with optional sign
  - Implementation-specified range centered at 0
- **Real objects**: Floating-point numbers with limited range/precision
  - Decimal digits with optional sign, with PERIOD (.) decimal point

#### 7.3.4 String Objects (3 subsections)
- **7.3.4.1 Literal strings**: Parentheses delimited `(string)`, escape sequences
- **7.3.4.2 Hexadecimal strings**: Angle-bracket delimited `<hexdigits>`, even number of digits
- **7.3.4.3 String encoding**: PDFDocEncoding, UTF-8, UTF-16BE character sets

#### 7.3.5 Name Objects
- Prefixed with SOLIDUS character `/`
- Atomic symbols uniquely defined by character sequence
- Escape sequences for special characters (e.g., `#20` for space)
- Case-sensitive, no length limit (spec recommends max 127 characters)

#### 7.3.6 Array Objects
- Square bracket delimited `[obj1 obj2 ...]`
- Ordered collection of objects
- Can contain any object type including nested arrays
- Objects implicitly numbered starting at 0

#### 7.3.7 Dictionary Objects
- Double angle-bracket delimited `<< key1 value1 key2 value2 >>`
- Associative arrays with name keys
- Values can be any object type
- Unordered (no guaranteed order)
- Common dictionaries: Stream dict, Page dict, Catalog dict, Font dict, etc.

#### 7.3.8 Stream Objects (2 subsections)
- **7.3.8.1 General**:
  - Dictionary (stream dict) followed by binary data
  - Bracketed by `stream` and `endstream` keywords
  - Stream dictionary contains `/Length`, `/Filter`, and optional decode parameters
  - Can be empty (zero-length data)
  
- **7.3.8.2 Stream Characteristics**:
  - Filter chains for decompression (multiple filters applied in sequence)
  - Stream data integrity considerations
  - Length specification (required)
  - Filter parameters for decode operations

#### 7.3.9 Null Object
- Single keyword `null`
- Type and value unique to null object
- Explicitly different from zero, empty string, or false

#### 7.3.10 Indirect Objects
- Labeled with: `<object_number> <generation_number> obj` ... `endobj`
- **Object number**: Positive integer, unique within file (but not necessarily sequential)
- **Generation number**: Non-negative integer (0 in new files, non-zero after updates)
- **Object reference**: `<n> <m> R` where n=object number, m=generation number
- Used for cross-referencing and establishing object relationships
- Can be updated through incremental updates (generation number incremented)

### Section 7.4: Filters (Pages 34-52)
Stream compression and encoding formats:

#### 7.4.1 General
- Filter chains (multiple filters applied sequentially)
- Decode parameters dictionary
- Standard filters for compression and encoding

#### 7.4.2 ASCIIHexDecode
- Encodes binary data as hexadecimal ASCII characters
- Includes EOD marker (optional `~>`)
- Useful for transporting binary in ASCII-only channels

#### 7.4.3 ASCII85Decode
- Also called Base85 encoding
- More compact than hex (4 bytes → 5 ASCII characters)
- EOD marker: `~>`
- Common in PostScript and PDF

#### 7.4.4 LZWDecode and FlateDecode Filters (4 subsections)
- **7.4.4.1 Overview**: Dictionary-based compression techniques
- **7.4.4.2 LZWDecode**: LZW compression algorithm (also used in TIFF)
  - Lempel-Ziv-Welch algorithm specification
  - Decoder initialization and operation
  
- **7.4.4.3 FlateDecode**: DEFLATE algorithm (RFC 1951)
  - RFC 1951 (DEFLATE), RFC 1950 (zlib), RFC 1952 (gzip) compatible
  - Most common compression in PDF
  - Predictor functions for improved compression
  - Multiple predictor types (0-15)
  
- **7.4.4.4 Flate Decompression**: Detailed decompression algorithm

#### 7.4.5 RunLengthDecode
- Simple run-length encoding
- Good for images with large color regions
- Format: `<count> <byte>` pairs

#### 7.4.6 CCITTFaxDecode
- Fax compression (ITU T.4 and T.6)
- Black-and-white image compression
- Group 3 and Group 4 encodings
- K parameter specifies group type

#### 7.4.7 JBIG2Decode
- Black-and-white image compression (JBIG2 standard)
- High compression for document scans
- Global and segment-specific data
- Decoder parameters

#### 7.4.8 DCTDecode
- JPEG compression (ISO/IEC 10918, DCT = Discrete Cosine Transform)
- For color and grayscale images
- Default color transform handling

#### 7.4.9 JPXDecode
- JPEG 2000 compression (ISO/IEC 15444)
- More advanced than JPEG
- Wavelet-based compression

#### 7.4.10 Crypt Filter
- Filter for encryption/decryption
- Applied transparently to encrypted streams

### Section 7.5: File Structure (Pages 53-95)
How PDF files are physically organized on disk/in memory:

#### 7.5.1 General
Four-part structure:
1. **Header**: `%PDF-1.x` version identifier
2. **Body**: Indirect objects
3. **Cross-reference section**: Object location table
4. **Trailer**: Metadata and root object reference

#### 7.5.2 File Header
- `%PDF-1.0` through `%PDF-2.0`
- First line of file (may have offset, binary comment after)
- Sets PDF version for processor conformance
- EOL marker after version string

#### 7.5.3 File Body
- Sequence of indirect objects
- Each object: `<n> <m> obj ... endobj`
- Objects can appear in any order
- Object cross-reference handled by xref table/stream

#### 7.5.4 Cross-Reference Table
- Traditional xref format (may be deprecated in future versions)
- Syntax: `xref`, followed by subsections
- Each subsection: starting object number, count, then entries
- Entry format: 20-byte lines with byte offset, generation number, keyword (n/f)
- Byte offset: Starting position of indirect object in file
- Generation number: Object generation (0 for new objects)
- Keyword: 'n' (in use) or 'f' (free/deleted)
- Supports multiple subsections for incremental updates

#### 7.5.5 File Trailer
- Dictionary containing metadata for entire file
- **Required entries**:
  - `/Size`: One plus highest object number used
  - `/Root`: Reference to document catalog
  
- **Optional entries**:
  - `/Encrypt`: Reference to encryption dictionary
  - `/Info`: Reference to document information dictionary
  - `/ID`: Unique file identifier (array of 2 strings)
  - `/Prev`: Reference to previous xref (for incremental updates)
  - `/XRefStm`: Byte offset of xref stream (for hybrid-reference files)

#### 7.5.6 Incremental Updates
- Appending new objects to existing PDF file
- Original xref table preserved
- New xref table added pointing to both old and new objects
- Trailer `/Prev` entry chains to previous trailer
- Generation numbers incremented for updated objects
- Used for: annotations, signatures, form data, document changes
- Preserves original content while adding/modifying objects

#### 7.5.7 Object Streams (PDF 1.5+)
- Stream object containing sequence of indirect objects
- Purpose: More compact storage through stream compression filters
- **Cannot contain**:
  - Stream objects
  - Objects with generation number ≠ 0
  - Encryption dictionary
  - Length entry objects (circular reference prevention)
- **Object stream dictionary entries**:
  - `/Type`: (Required) ObjStm
  - `/N`: (Required) Number of objects
  - `/First`: (Required) Byte offset of first uncompressed object
  - `/Extends`: (Optional) Reference to parent object stream
- **Data format**: 
  - Pairs of integers: (object_number, byte_offset) for each contained object
  - Followed by actual object data
- Objects inside stream referenced like normal: `<n> 0 R`

#### 7.5.8 Cross-Reference Streams (PDF 1.5+)
- Binary alternative to xref tables
- Stream object containing cross-reference data
- **Advantages**:
  - More compact representation
  - Can reference objects in object streams
  - Allows future entry type extensions
  - Can be compressed with filters
  
- **7.5.8.1 General**: Overview and advantages
  
- **7.5.8.2 Cross-Reference Stream Dictionary**:
  - `/Type`: (Required) XRef
  - `/Size`: (Required) One plus max object number
  - `/Root`: (Required in trailer) Document catalog
  - `/Encrypt`: (If encrypted) Encryption dictionary
  - `/Info`: (Optional) Document info dictionary
  - `/ID`: (Required in all files) Unique identifier
  - `/Prev`: (For incremental updates) Previous xref reference
  - `/Index`: (Optional) Array of object number ranges
  - `/W`: (Required) Array of column widths [w1 w2 w3]
    - w1: Bytes for subsection type (0-2)
    - w2: Bytes for field 1 (byte offset or object number)
    - w3: Bytes for field 2 (generation number or object stream index)
  - `/DecodeParms`: (Optional) Filter decode parameters
  - `/Filter`: (Optional) Compression filter (commonly FlateDecode)
  - `/Length`: (Required) Stream data length
  
- **7.5.8.3 Cross-Reference Stream Data**:
  - Binary data with 3 columns per entry
  - Entry types (first column):
    - Type 0: Free objects (next free object number, generation)
    - Type 1: Uncompressed object (byte offset in file, generation)
    - Type 2: Compressed object (object stream number, index in stream)
  - Entries for all objects: free and in-use
  - Can be compressed with stream filters
  - Multiple subsections supported
  
- **7.5.8.4 Compatibility**:
  - Applications not supporting compressed object references can still read files
  - Linearization compatibility considerations
  - Hybrid-reference files support both xref table and xref stream

### Section 7.6: Encryption (Pages 71-95)
Document security and content protection:

#### 7.6.1 General
- Document-level encryption for content protection
- Multiple security handlers (standard and public-key)
- User and owner passwords
- Encryption permissions (print, copy, modify, etc.)

#### 7.6.2 Application of Encryption
- Applied at file level
- Encryption dictionary specifies algorithm and parameters
- Crypt filters specify which streams/objects are encrypted
- Default: All streams encrypted except metadata stream

#### 7.6.3 General Encryption Algorithm
- Encryption dictionary specification
- 40-bit and 256-bit encryption support
- Algorithm version (R2, R3, R4, R5, R6)

#### 7.6.4 Standard Security Handler
- Password-based encryption
- Owner password: Controls document permissions (print, copy, etc.)
- User password: Controls access to encrypted content
- Encryption key derived from password

#### 7.6.5 Public-Key Security Handlers
- Certificate-based encryption
- X.509 certificates for recipient identification
- CMS (Cryptographic Message Syntax) based

#### 7.6.6 Crypt Filters
- Specify which objects/streams are encrypted
- Can use different encryption algorithms for different content
- Identity filter: No encryption applied
- Specific filter references in stream dictionaries

#### 7.6.7 Unencrypted Wrapper Document
- Document containing encrypted content as embedded files
- Outer document not encrypted (viewable in all readers)
- Inner documents encrypted with different passwords

### Section 7.7: Document Structure (Pages 96-109)
Semantic organization of PDF documents:

#### 7.7.1 General
- Hierarchical structure: Catalog → Page Tree → Pages
- Pages accessed through tree structure (memory efficient)
- Resources: Fonts, images, color spaces, patterns, etc.

#### 7.7.2 Document Catalog Dictionary
- **Root object of document object hierarchy**
- Located via `/Root` entry in file trailer
- Contains references to all major document components

**Complete Table 29 entries:**
- `/Type`: (Required) Catalog
- `/Version`: (Optional) PDF version for this document
- `/Extensions`: (Optional) Extensions dictionary (7.12)
- `/Pages`: (Required) Reference to page tree root
- `/PageLabels`: (Optional) Page labeling rules
- `/PageLayout`: (Optional) How pages displayed when opened
- `/PageMode`: (Optional) Document outline/thumbnails visibility on open
- `/Name`: (Optional) Name dictionary for named destinations
- `/Dests`: (Optional) Named destinations
- `/OpenAction`: (Optional) Action to perform when document opens
- `/AA`: (Optional) Additional actions triggered by events
- `/URI`: (Optional) Web links base URL
- `/AcroForm`: (Optional) Interactive form properties
- `/Metadata`: (Optional) Document metadata stream (XMP)
- `/StructTreeRoot`: (Optional) Structure tree for accessibility
- `/MarkInfo`: (Optional) Marked content properties
- `/Lang`: (Optional) Natural language identifier
- `/SpiderInfo`: (Optional) Web Capture information
- `/OutputIntents`: (Optional) Output intent specifications
- `/PieceInfo`: (Optional) Application-specific data
- `/OCProperties`: (Optional) Optional content properties
- `/Permissions`: (Optional) Document permission information
- `/UserUnit`: (Optional) Default user space unit size
- `/Assoc`: (Optional) Associated files
- `/Encrypt`: NOTE: Set in trailer, not catalog
- `/Outlines`: (Optional) Document outline (bookmarks)
- `/Threads`: (Optional) Article threads
- `/ViewerPreferences`: (Optional) Display preferences

#### 7.7.3 Page Tree (4 subsections)

##### 7.7.3.1 General
- Tree structure with intermediate nodes and leaf nodes
- **Page tree nodes**: Intermediate nodes with `/Kids` and `/Count`
- **Page objects**: Leaf nodes with actual page content/properties
- **Benefits**: Allows readers to open large documents efficiently
- **Balanced trees**: Optimization recommended by PDF spec

##### 7.7.3.2 Page Tree Nodes
Dictionary describing intermediate page tree structure.

**Table 30 - Required entries:**
- `/Type`: (Required) Pages
- `/Parent`: (Required except root; not in root) Reference to parent node
- `/Kids`: (Required) Array of references to child pages/nodes
- `/Count`: (Required) Number of leaf page nodes in subtree

**Table 31 - Optional entries:**
- `/MediaBox`: (Optional) Default media box for all pages
- `/CropBox`: (Optional) Default crop box
- `/BleedBox`: (Optional) Default bleed box
- `/TrimBox`: (Optional) Default trim box
- `/ArtBox`: (Optional) Default art box
- `/Rotate`: (Optional) Default page rotation (0, 90, 180, 270)
- `/Resources`: (Optional) Default resource dictionary
- `/TabOrder`: (Optional) Tab order for annotations
- `/Thumb`: (Optional) Reference to thumbnail image
- `/Annots`: (Optional) Array of annotations (not inherited)
- `/B`: (Optional) Background color (not inherited)
- `/StructParents`: (Optional) Structure parent tree reference
- `/Contents`: (Optional) Content stream references
- `/Duration`: (Optional) Display duration for presentations
- `/Trans`: (Optional) Page transition specification
- `/AA`: (Optional) Additional actions
- `/UserUnit`: (Optional) User space unit scaling
- `/VP`: (Optional) Viewport definitions

##### 7.7.3.3 Page Objects
Dictionary describing individual page properties.

**Properties (inherited from parent if not specified):**
- `/Type`: (Required) Page
- `/Parent`: (Required) Reference to parent page tree node
- `/MediaBox`: (Required) Physical page dimensions [llx lly urx ury]
- `/CropBox`: (Optional, default=MediaBox) Visible page area
- `/BleedBox`: (Optional, default=CropBox) Production-related boundary
- `/TrimBox`: (Optional, default=CropBox) Trim marks boundary  
- `/ArtBox`: (Optional, default=CropBox) Meaningful content boundary
- `/Rotate`: (Optional, default=0) Page rotation: 0, 90, 180, 270 degrees
- `/Resources`: (Required) Resource dictionary for page content
- `/Contents`: (Optional) Content stream(s) describing page
- `/Thumb`: (Optional) Reference to page thumbnail image
- `/B`: (Optional) Background color for transparency
- `/Dur`: (Optional) Duration for presentations (seconds)
- `/Trans`: (Optional) Page transition effect
- `/Annots`: (Optional) Array of annotations on page
- `/AA`: (Optional) Additional actions (JavaScript, etc.)
- `/Metadata`: (Optional) Metadata stream (XMP) for page
- `/StructParents`: (Optional) Structure parent tree reference
- `/UserUnit`: (Optional) User space unit scaling factor
- `/TabOrder`: (Optional) Tab order for annotations
- `/PresSteps`: (Optional) Presentation steps

**Important**: Multiple inheritance
- Properties not specified in Page object inherited from ancestors
- Inheritance path: specific Page → immediate Parent → ancestor nodes → Page tree root

##### 7.7.3.4 Inherited Page Properties
- Specification of property inheritance mechanism
- Properties inherit from parent page tree nodes
- Child pages override inherited values
- Default values applied at leaf nodes if not specified anywhere
- Allows efficient specification of common properties

#### 7.7.4 Name Dictionary
- Maps names to page tree nodes or other objects
- Used for accessing pages by name (e.g., chapter references)
- Alternative to numeric page indexing

### Section 7.8: Content Streams and Resources (Pages 110-113)

#### 7.8.1 General
- Content streams: Instructions for rendering pages
- Resources: Objects referenced by content streams (fonts, images, etc.)

#### 7.8.2 Content Streams
- Stream objects containing sequence of graphical operators
- PDF operators and operands for drawing
- **Operator categories**:
  - Text operators (text positioning, font selection)
  - Path operators (line drawing, shape definition)
  - Painting operators (filling, stroking, clipping)
  - Graphics state operators (color, line width, etc.)
  - Color operators (color space selection)
  - Shade/pattern operators
- Single or multiple streams per page (usually combined)
- Described in detail in Chapter 8 (Graphics) and beyond

#### 7.8.3 Resource Dictionaries
- Maps resource names to actual resource objects
- **Resource categories**:
  - `/Font`: Font dictionaries by name
  - `/XObject`: External objects (images, forms, etc.)
  - `/ColorSpace`: Color space definitions
  - `/Pattern`: Pattern definitions
  - `/Shading`: Shading definitions
  - `/ProcSet`: PostScript procedure sets (deprecated)
  - `/Properties`: Marked content properties
  - `/ExtGState`: Extended graphics state dictionaries
- Referenced in content streams by name (e.g., `Tf` operator: `/F1 12 Tf`)
- Inherited from parent page tree nodes if not specified

### Section 7.9: Common Data Structures (Pages 114-121)

#### 7.9.1 General
- Data structures built from basic objects
- Widely used throughout PDF specification

#### 7.9.2 String Object Types (4 subsections)
- **7.9.2.1 Text strings**: Strings interpreted as text with character encoding
  - PDFDocEncoding (default)
  - UTF-8 (marked with BOM)
  - UTF-16BE (marked with BOM)
  
- **7.9.2.2 Binary strings**: Arbitrary byte sequences
  - May contain null bytes (0x00)
  - Treated as opaque data
  - 7.9.2.2.1 PDFDocEncoding: 8-bit character set, ISO Latin 1 extended
  - 7.9.2.2.2 UTF-16BE: Unicode encoding, big-endian
  
- **7.9.2.3 Literal strings**: Parentheses syntax `(string)`
  - Escape sequences: `\\`, `\n`, `\t`, etc.
  - Octal escape: `\ddd`
  - Balanced parentheses within string
  
- **7.9.2.4 Hexadecimal strings**: Angle bracket syntax `<hexdigits>`
  - Pairs of hex digits
  - Odd number of digits: pad with zero

#### 7.9.3 Text Streams
- Strings interpreted as text sequences
- Character encoding specified (PDFDocEncoding or Unicode)
- Used for document title, author, subject, etc.

#### 7.9.4 Dates
- Format: `D:YYYYMMDDHHmmSSOHH'mm'`
- Example: `D:20220315143022-07'00'` (3:30:22 PM, March 15, 2022, PDT)
- Components:
  - YYYY: Year (4 digits, e.g., 2022)
  - MM: Month (01-12)
  - DD: Day (01-31)
  - HH: Hours (00-23)
  - mm: Minutes (00-59)
  - SS: Seconds (00-59)
  - OH'mm': Offset from UTC (sign, hours, minutes)
- Used for creation date, modification date, event timestamps

#### 7.9.5 Rectangles
- Array of 4 numbers: `[llx lly urx ury]`
- llx, lly: Lower-left corner x, y coordinates
- urx, ury: Upper-right corner x, y coordinates
- Used for: MediaBox, CropBox, page boundaries, annotation regions
- Units: User space units (default 1/72 inch)
- Can have: llx > urx or lly > ury (still defines rectangle)

#### 7.9.6 Name Trees
- Dictionary-like structure mapping string keys to values
- Keys are strings (not names), ordered
- More efficient lookup than dictionaries for large key sets
- Structure:
  - Root dictionary with `/Kids` (leaf nodes) or `/Nums`/`/Limits`
  - Intermediate nodes organize ranges
  - Leaf nodes contain actual mappings
- Used for: named destinations, embedded files, etc.

#### 7.9.7 Number Trees
- Similar to name trees but with integer keys
- Integer keys are ordered
- Used for: page labels, structure tree, etc.

### Section 7.10: Functions (Pages 123-131)
Mathematical function objects:
- Type 0: Sampled functions (interpolated lookup tables)
- Type 2: Exponential functions (polynomial)
- Type 3: Stitching functions (piecewise)
- Type 4: Postscript functions (PostScript language)
- Used for: shading, halftoning, color mapping, etc.

### Section 7.11: File Specifications (Pages 132-140)
File reference objects:
- Cross-platform file path references
- Embedded file stream references
- Used for: file attachments, external resources, etc.

### Section 7.12: Extensions Dictionary (Page 141)
- Identifies developer-defined extensions in PDF file
- Allows forward compatibility
- Extension versions and compatibility information

## Quick Reference: File Structure Variants

### 1. Traditional PDF (7.5.4 + 7.5.5)
```
%PDF-1.4
... objects ...
xref
0 5
0000000000 65535 f
0000000009 00000 n
... 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
123456
%%EOF
```

### 2. PDF with Incremental Updates (7.5.6)
```
... (original PDF content) ...
xref
0 1
0000000000 65535 f
... (new/modified objects) ...
xref
1 3
0000123456 00000 n
...
trailer
<< /Size 5 /Root 1 0 R /Prev 98765 >>
startxref
456789
%%EOF
```

### 3. PDF with Object Streams (7.5.7)
```
%PDF-1.5
... 
5 0 obj
<< /Type /ObjStm /N 2 /First 20 >>
stream
1 0 2 50
obj1_data obj2_data
endstream
endobj
...
```

### 4. PDF with Cross-Reference Streams (7.5.8)
```
%PDF-1.5
... objects ...
12 0 obj
<< /Type /XRef /Size 5 /Root 1 0 R /W [1 3 0] >>
stream
... binary xref data ...
endstream
endobj
startxref
456789
%%EOF
```

### 5. Hybrid-Reference PDF (7.5.4 + 7.5.8)
```
%PDF-1.5
... objects ...
xref
0 5
... xref table ...
xref
5 3
... more objects ...
12 0 obj
<< /Type /XRef /Size 8 /Root 1 0 R /XRefStm 456789 >>
stream
... binary xref data ...
endstream
endobj
startxref
456789
%%EOF
```

## Critical Definitions for Preflight Engine

### Object Types to Validate (7.3)
- Boolean: `true`, `false`
- Integer: `-127` to `2147483647` (typical range)
- Real: `-3.14159`, `2.0`, `.5` (with optional sign and decimal)
- String: `(literal)` or `<48656C6C6F>`
- Name: `/Type`, `/Pages`, `/MediaBox`
- Array: `[1 2.5 true (str) /Name]`
- Dictionary: `<< /Key value >> `
- Stream: `stream data endstream`
- Null: `null`
- Indirect: `1 0 R`, `5 2 R`

### Compression Types (7.4)
Must support for decompression:
1. **FlateDecode** (DEFLATE, RFC 1951) - Most common
2. **LZWDecode** - Lempel-Ziv-Welch
3. **ASCIIHexDecode** - Hex encoding (not compression)
4. **ASCII85Decode** - Base-85 encoding
5. **RunLengthDecode** - Run-length encoding
6. **CCITTFaxDecode** - Fax compression (T.4, T.6)
7. **JBIG2Decode** - B&W image compression
8. **DCTDecode** - JPEG compression
9. **JPXDecode** - JPEG 2000 compression

### File Structure Rules
- Every PDF starts with: `%PDF-1.0` through `%PDF-2.0`
- Cross-reference follows standard format or stream format (not mixed in same section)
- Trailer must specify `/Size` (one plus max object number)
- Trailer must specify `/Root` (document catalog)
- File ends with `%%EOF` after `startxref` and offset
- Generation numbers increment with updates (typically 0 for new files)

### Document Hierarchy
```
Catalog (7.7.2)
├── /Pages → Page Tree Root (7.7.3.2)
│   ├── /Kids → [Page Tree Node, Page Tree Node, ...]
│   │   ├── /Kids → [Page, Page, Page, ...]  (7.7.3.3)
│   │   │   ├── /MediaBox [llx lly urx ury]
│   │   │   ├── /CropBox (default = MediaBox)
│   │   │   ├── /BleedBox (default = CropBox)
│   │   │   ├── /TrimBox (default = CropBox)
│   │   │   ├── /ArtBox (default = CropBox)
│   │   │   ├── /Contents → Stream(s) (7.8.2)
│   │   │   │   └── Operators + Operands
│   │   │   └── /Resources → Resource Dict (7.8.3)
│   │   │       ├── /Font → {/F1 → Font Object}
│   │   │       ├── /XObject → {/Im1 → Image Object}
│   │   │       ├── /ColorSpace → {...}
│   │   │       └── /ExtGState → {...}
├── /Outlines → Bookmarks
├── /Metadata → XMP Stream
├── /AcroForm → Forms
└── ... (Other entries per Table 29)
```

### Key Properties to Validate

**Page Boxes (inherited, [llx lly urx ury]):**
- `/MediaBox`: Physical paper size (required)
- `/CropBox`: Visible area (default = MediaBox)
- `/BleedBox`: Trim area (default = CropBox)  
- `/TrimBox`: Final size (default = CropBox)
- `/ArtBox`: Content area (default = CropBox)

**Rotation:**
- `/Rotate`: Must be 0, 90, 180, or 270

**Text Encoding:**
- PDFDocEncoding (default, 8-bit)
- UTF-8 (with BOM: EF BB BF)
- UTF-16BE (with BOM: FE FF)

**String Escape Sequences (7.3.4.1):**
- `\\` = backslash
- `\n` = newline (0x0A)
- `\r` = carriage return (0x0D)
- `\t` = tab (0x09)
- `\b` = backspace (0x08)
- `\f` = form feed (0x0C)
- `\(` = left parenthesis
- `\)` = right parenthesis
- `\ddd` = octal (3 digits)

**Name Encoding (7.3.5):**
- `/` prefix not part of name
- Characters 0-31, 127, # must be escaped
- Escape format: `#HH` where HH is 2-digit hex
- Example: `/My Name` → `/My#20Name`

## Usage for PDF Preflight Engine

This extraction is essential for implementing:

1. **PDF Parser**: Tokenize and parse all object types
2. **Validator**: Check conformance to object structure rules
3. **Compressor**: Understand all compression types and filters
4. **Object Manager**: Track object numbering, generation, references
5. **File Structure Analyzer**: Detect file structure variants
6. **Property Inspector**: Validate page boxes, inheritance, content
7. **Encryption Handler**: Support standard and public-key security
8. **Incremental Update Handler**: Process file updates correctly
9. **Accessibility Checker**: Understand document structure requirements
10. **Content Stream Analyzer**: Parse graphics operators (Chapter 8)

All technical details required for comprehensive PDF processing are contained in this extraction.

---

*Extraction Date: March 11, 2026*
*Source: ISO 32000-2:2020 (PDF 2.0) - Sponsored by PDF Association*
*Complete Chapter 7: Syntax from pages 20-141*

