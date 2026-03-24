# 01: PDF File Structure Variants

**Research Deliverable** — Grounded Preflight Engine | Based on ISO 32000-2:2020 Chapter 7

---

## Overview

PDF files are organized into six distinct file structure variants, each optimizing for different use cases: basic random access, efficient incremental updates, network streaming, and compressed reference storage. Per §7.5.1–7.5.8, all variants must conform to the four-part structure: header, body, cross-reference table/streams, and trailer.

---

## The Six PDF File Structure Variants

### 1. Traditional Cross-Reference Table (§7.5.4)

**Core Structure:**
- Header: `%PDF-1.n` or `%PDF-2.n` (§7.5.2)
- Body: sequence of indirect objects (§7.5.3)
- Cross-reference table: keyword `xref` followed by subsections (§7.5.4)
- Trailer: contains Root, Size entries (§7.5.5)

**Fixed-Width Format (§7.5.4):**
Each xref entry is exactly 20 bytes: 10-digit offset + SPACE + 5-digit generation + SPACE + single flag ('n'/'f') + EOL.

**Preflight Checks:**
- Verify `xref` keyword at line start
- Validate subsection headers (starting_object_number count)
- All offsets point to actual `n m obj` positions
- No comments between xref and trailer (§7.5.4 NOTE 2)
- Free objects form valid chain via generation numbers

---

### 2. Cross-Reference Streams (§7.5.8, PDF 1.5+)

**Core Structure:**
Stream dictionary with Type=XRef containing binary-encoded cross-reference entries.

**Required Entries (§7.5.8):**
- Type: XRef
- Size: highest object number + 1
- W: [type_width, field2_width, field3_width]
- Index: pairs of [start_object_number, count] (optional, default [0, Size])

**Entry Types (§7.5.8.2):**
- Type 0: free object
- Type 1: uncompressed object with byte offset
- Type 2: compressed object in object stream

**Preflight Checks:**
- Validate W array (sum ≤ 8 bytes/entry)
- Decompress stream using Filter entry
- Type 2 entries: validate object stream object numbers
- All entry types consistent with W[0] (type field width)

---

### 3. Object Streams (§7.5.7, PDF 1.5+)

**Purpose:**
Compress multiple objects into single stream. Per §7.5.7, cannot contain stream objects, catalog, pages tree, or encryption dictionary.

**Dictionary Entries (§7.5.7):**
- Type: ObjStm
- N: object count
- First: byte offset to first object definition
- Extends: reference to predecessor stream (optional)

**Preflight Checks:**
- N matches actual object count in stream
- First offset correct (must point to objects, not header)
- Objects not themselves streams
- Object stream object number in xref Type 2 entries must exist

---

### 4. Linearized PDF (Annex F, referenced in §7.5.1)

**Purpose:**
Enable first-page display before full download via hint tables.

**Linearization Dictionary (Annex F):**
- /Linearized: 1
- /O: first page object number
- /E: byte offset to end of first page
- /T: byte offset to main xref
- /L: total file length
- /N: page count

**Preflight Checks:**
- Linearization dictionary as first object
- /E < /T (first page before main xref)
- Hint streams decompress correctly
- Primary xref contains first-page objects only

---

### 5. Incremental Updates (§7.5.6)

**Purpose:**
Append changes without rewriting file (essential for digital signatures).

**Structure:**
New objects + xref section + trailer with /Prev entry pointing to previous trailer.

**Preflight Checks:**
- Prev chain valid (follows all trailers backward)
- Original bytes unchanged
- Size entry consistent across all trailers
- Deleted objects marked 'f' in latest xref

---

### 6. Hybrid-Reference (Object Streams + Xref Streams, PDF 1.5+)

**Purpose:**
Maximum compression via object streams + xref stream indexing.

**Structure:**
- Object streams (§7.5.7) store compressed objects
- Xref stream (§7.5.8) with Type 2 entries
- W array includes 3 elements for Type 2 support

**Preflight Checks:**
- Type 2 entries: object stream exists + valid index within stream
- No object number collisions
- W[0] ≥ 1 (must include type byte)

---

## File Header & Trailer Standards

### Header Validation (§7.5.2)

**Accepted Versions:**
- %PDF-1.0 through %PDF-1.7
- %PDF-2.0

**Preflight Rules:**
- Header at byte 0 (or after binary prefix)
- Followed by EOL (LF, CR, or CRLF)
- If binary data precedes header, comment with 4+ binary characters must follow

### Trailer Dictionary (§7.5.5)

**Mandatory:**
- Size: highest object number + 1
- Root: indirect reference to Catalog

**Optional:**
- Prev: byte offset to previous trailer
- ID: [original_ID, current_ID] for signature validation
- Encrypt: encryption dictionary reference
- XRefStm: xref stream object reference

---

## Table References

| Section | Content |
|---------|---------|
| §7.2.3 | White-space characters |
| §7.3.2–7.3.10 | Object types (Boolean, Numeric, String, Name, Array, Dictionary, Stream, Null, Indirect) |
| §7.3.8 | Stream objects (filtering, decompression) |
| §7.4 | Filters (FlateDecode, ASCIIHexDecode, LZWDecode, RunLengthDecode, CCITTFaxDecode, JBIG2Decode, DCTDecode, JPXDecode) |
| §7.5.1 | General file structure rules |
| §7.5.2 | File header format |
| §7.5.3 | File body (objects) |
| §7.5.4 | Cross-reference table |
| §7.5.5 | File trailer |
| §7.5.6 | Incremental updates |
| §7.5.7 | Object streams |
| §7.5.8 | Cross-reference streams |
| §7.7.2 | Catalog dictionary structure |
| Annex F | Linearized PDF specification |
| Annex H | Example PDF file |

---

## Feed to AI

Use this research to design LintPDF's **File Structure Detection Module**:

1. **Header Parser**: Validate %PDF-n.n format, detect version, validate EOL
2. **Xref Router**: Identify traditional xref vs xref stream vs object streams vs linearized
3. **Offset Validator**: Cross-check all byte offsets against actual file positions
4. **Object Stream Handler**: Decompress, parse pairs, extract objects by index
5. **Incremental Update Handler**: Follow Prev chain, merge xref tables
6. **Hybrid Resolver**: Handle mixed traditional/xref-stream/object-stream files

For each variant, design separate parsing code paths that converge on unified XrefEntry structure. Generate detailed violation reports citing specific §7.5.x clauses and offending byte positions.

**Key Validation Flow:**
- Read header → determine version
- Read trailer → locate xref/xref stream
- Parse xref structure → identify variant(s)
- Resolve all object references → validate byte offsets
- For incremental updates → follow Prev chain, merge tables
- For object streams → decompress, extract indexed objects
- Report all violations with clause numbers and offsets

---

**Specification Version:** ISO 32000-2:2020 Chapter 7
**Date Generated:** 2026-03-11
