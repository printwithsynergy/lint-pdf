# Phase 3: Open-Source Foundation Assessment
## Grounded PDF Preflight Engine - Technology Stack Analysis

**Date:** March 2026
**Scope:** Tasks 3.1–3.5 Comprehensive Research
**Objective:** Assess open-source PDF tools for Grounded's detection-only preflight architecture

---

## TASK 3.1: pikepdf / QPDF Deep Assessment

### 3.1.1 Overview

**pikepdf** is a Python library providing a high-level, Pythonic interface to QPDF, a C++ PDF transformation library. pikepdf wraps QPDF's capabilities while adding Python-friendly APIs and additional functionality.

**QPDF** is a low-level C++ library for PDF structure manipulation, designed to be lightweight with minimal external dependencies. It focuses on content-preserving transformations rather than rendering or extraction.

### 3.1.2 Object Access Capabilities

| Capability | pikepdf | QPDF | Notes |
|---|---|---|---|
| **All PDF Object Types** | ✓ Full | ✓ Full | Both access all object types: streams, dictionaries, arrays, names, operators |
| **Indirect References** | ✓ Yes | ✓ Yes | `pikepdf.Object.is_indirect()` and `.make_indirect()` available |
| **Object Decompression** | ✓ Automatic | ✓ Yes | Object streams automatically decompressed on access |
| **Raw Binary Data Access** | ✓ Yes | ✓ Yes | Can access raw PDF bytes when needed |
| **Catalog/Root Access** | ✓ Yes | ✓ Yes | Full access to PDF document structure |

**Assessment:** Both pikepdf and QPDF provide complete object model access, sufficient for preflight analysis at the structural level.

### 3.1.3 Content Stream Parsing

| Aspect | Capability | Level |
|---|---|---|
| **Tokenization** | Supported | Full |
| **Operator Parsing** | Supported | Full |
| **Semantic Parsing** | Limited | Partial |
| **Parser vs Filter** | Two modes provided | Flexible |

**Detailed Breakdown:**

- **Parser Mode:** Returns higher-level information, grouping operands with operators. Useful for information retrieval (e.g., position detection) but loses subtleties unsuitable for content stream reconstruction.

- **Filter Mode (TokenFilter):** Works at lower token level, preserving comments and space distinctions. Allows fine-grained content stream editing through subclassable token handlers.

- **Operator Whitelisting:** pikepdf supports filtering specific operators by space-separated strings (e.g., `'q Q cm Do'` for image drawing operators, `'BI ID EI'` for inline images).

- **Content Stream Parsing Limitations:**
  - Basic tokenization and operator extraction only
  - No semantic understanding of graphics state, color spaces, text layout
  - Cannot infer relationships between operators (e.g., clip path vs. fill path intent)

**Preflight Gap:** Grounded must build semantic understanding of content streams (graphics state management, color intent detection, overprint flags, transparency interactions).

### 3.1.4 Page Box Access

| Box Type | Access | Notes |
|---|---|---|
| **MediaBox** | ✓ Direct | via `page['/MediaBox']` |
| **CropBox** | ✓ Direct | Inherited from MediaBox if not defined |
| **BleedBox** | ✓ Direct | via `page['/BleedBox']` |
| **TrimBox** | ✓ Direct | via `page['/TrimBox']` |
| **ArtBox** | ✓ Direct | via `page['/ArtBox']` |

**Implementation:** Page box properties are accessible as dictionary entries. pikepdf provides clean APIs through the page object model for reading and modifying all five boxes.

### 3.1.5 Font Dictionary Access and Inspection

| Feature | Capability | Notes |
|---|---|---|
| **Font Dictionary Retrieval** | ✓ Yes | Via page Resources dictionary `/Font` entry |
| **Font Type Detection** | ✓ Yes | Can identify Type0, Type1, TrueType, etc. |
| **Embedded Font Data** | ✓ Partial | Access to FontFile/FontFile2/FontFile3 streams |
| **Font Metrics** | ✓ Limited | Can read font descriptor metrics (Ascender, Descender, etc.) |
| **Subsetting Detection** | ✓ Possible | Via font name prefixes and subset tag analysis |
| **CMap Access** | ✓ Yes | Can access ToUnicode CMap for character mapping |

**Limitations:**
- No built-in font parsing (e.g., cannot introspect TrueType or CFF outlines)
- Cannot validate font encoding tables without external font libraries
- Limited glyph coverage analysis

**Preflight Gap:** Grounded needs external font parsing library (e.g., fontTools) for deep font validation (missing glyphs, encoding issues, license flags).

### 3.1.6 Image Extraction Capabilities

| Feature | Status | Notes |
|---|---|---|
| **Image Detection** | ✓ Full | All image XObjects accessible via Resources |
| **Direct Extraction** | ✓ Yes | Can extract to usable formats (PNG, JPEG, etc.) |
| **Lossless Extraction** | ✓ Preferred | Compressed data extracted without transcoding when possible |
| **Image Metadata** | ✓ Partial | Access to Width, Height, ColorSpace, Intent, SMask, etc. |
| **Color Space Validation** | Requires external | Must use color library for ICC profile validation |

**Implementation:** Images stored as stream objects with dictionary properties. pikepdf provides a Pillow-like API for extraction, with automatic format detection and optional transcoding.

### 3.1.7 Encryption Handling

| Feature | Support | Notes |
|---|---|---|
| **Encrypted PDF Opening** | ✓ Yes | `pikepdf.Pdf.open(pdf_path, password='...')` |
| **Algorithm Detection** | ✓ Yes | Automatically selects AES-256 by default |
| **Password-Protected Access** | ✓ Yes | Handles user and owner passwords |
| **Linearization** | ✓ Yes | QPDF supports linearization for streaming |
| **Metadata Encryption** | ✓ Supported | Respects /EncryptMetadata flag |

**Preflight Consideration:** Encrypted PDFs require correct password for full analysis. Some preflight checks can proceed without decryption (e.g., encryption method itself), but content analysis requires decryption.

### 3.1.8 Content Stream Operators and Exposure

**Supported Operators:** pikepdf's filter mechanism exposes all PDF content stream operators. Key operator categories:

- **Graphics State:** `q` (push), `Q` (pop), `cm` (concat matrix), `w` (line width), `J` (line cap), `j` (line join), `M` (miter limit), `d` (dash), `ri` (rendering intent), `i` (flatness), `gs` (ext. graphics state)
- **Text:** `BT` (begin), `ET` (end), `Tf` (font select), `Tw` (word space), `Tc` (char space), `Tz` (scaling), `TL` (leading), `Tr` (render mode), `Ts` (rise), `Td`, `T*`, `Tm` (positioning)
- **Path:** `m` (moveto), `l` (lineto), `c` (curveto), `v`, `y`, `h` (closepath), `re` (rectangle), `S` (stroke), `f` (fill), `B` (fill+stroke), `W` (clipping), `n` (no-op)
- **Color:** `CS`, `cs` (color space), `SC`, `SCN`, `sc`, `scn` (color setting), `G`, `g` (gray), `RG`, `rg` (RGB), `K`, `k` (CMYK)
- **Images/XObjects:** `Do` (XObject invoke), `EI`, `ID`, `BI` (inline image boundaries)
- **Text Show:** `Tj`, `TJ`, `'`, `"` (text output)
- **Marked Content:** `BDC`, `BMC`, `EMC` (marked content tags and dictionary references)

**Limitation:** Only tokenization and operator identification; no semantic interpretation of graphics state transformations, color intent stacking, or operator interaction effects.

### 3.1.9 Performance Characteristics

| Aspect | Performance | Notes |
|---|---|---|
| **File Loading** | Fast (~100 MB/s) | C++ backend; minimal Python overhead |
| **Object Access** | Constant time | Pointer dereferencing |
| **Content Stream Parsing** | Linear, O(n) | C++ optimized parser; TokenFilter subclassing adds overhead |
| **Memory Efficiency** | Good | Streams kept compressed in memory unless accessed |
| **Memory Copy Reduction** | Improved | Recent versions minimize unnecessary copies when reading from file streams |
| **Large File Handling** | Good | Lazy loading reduces initial memory footprint |

**Bottleneck Considerations:**
- Parsing all content streams of a large PDF is I/O bound initially, then CPU bound for operator analysis
- Multiple document passes (e.g., font analysis + content analysis) require efficient caching

### 3.1.10 Gap Analysis: pikepdf/QPDF vs. Grounded Requirements

| Requirement | pikepdf | QPDF | Grounded Must Build |
|---|---|---|---|
| **Complete object model** | ✓ Full | ✓ Full | — |
| **Page boxes** | ✓ Full | ✓ Yes | — |
| **Content stream tokenization** | ✓ Full | ✓ Yes | — |
| **Semantic operator analysis** | ✗ No | ✗ No | Operator state machine, graphics state tracking |
| **Color space validation** | ✗ No | ✗ No | ICC profile parsing, color model checking |
| **Font validation** | ✗ No | ✗ No | fontTools integration, glyph coverage |
| **Overprint/transparency intent** | ✗ No | ✗ No | Extended graphics state (GS) parsing |
| **Ink coverage detection** | ✗ No | ✗ No | Ghostscript integration or custom rasterizer |
| **PDF/A/X compliance rules** | ✗ No | ✗ No | Standards-specific rule engine |
| **Annotation analysis** | ✓ Partial | ✓ Yes | Custom annotation rule evaluation |

### 3.1.11 Recommendation

**Primary Foundation:** pikepdf is the recommended primary foundation for Grounded.

**Rationale:**
- Clean Python API reduces development friction
- QPDF's C++ backend ensures fast parsing and object manipulation
- Content stream tokenization is sufficient foundation for semantic analysis layers
- Well-maintained project with active community
- Excellent documentation and examples

**Integration Strategy:**
1. Use pikepdf for all structural analysis (objects, pages, boxes, resources)
2. Implement custom content stream semantic analyzer on top of pikepdf's TokenFilter
3. Layer external tools for specialized validation (fonts, colors, ink coverage)

---

## TASK 3.2: veraPDF Deep Assessment

### 3.2.1 Overview

veraPDF is an industry-backed, open-source PDF/A validator. It provides:
- PDF/A and PDF/UA compliance checking
- Feature extraction (metadata, properties, objects)
- Policy-based custom rule checking via Schematron
- REST API and CLI interfaces
- Docker deployment with web UI

### 3.2.2 REST API Endpoints and Format

**Base URL:** `http://localhost:8080/api`

| Endpoint | Method | Purpose | Request Body | Response Format |
|---|---|---|---|---|
| `/profiles` | GET | List all validation profiles | — | JSON array of profile objects |
| `/profiles/{id}` | GET | Retrieve specific profile | — | JSON profile definition |
| `/validate/{id}` | POST | Validate PDF against profile | Binary PDF file | JSON validation result |
| `/features` | POST | Extract features from PDF | Binary PDF file | XML feature report |
| `/policy` | POST | Apply policy rules to report | XML report + policy | JSON policy check result |

**Request Format:**
- Content-Type: `multipart/form-data` or `application/octet-stream` for PDF upload
- Profile ID format: `pdf-a-1-b`, `pdf-ua-1`, etc.

**Response Format (Validation Result):**
```json
{
  "jobId": "unique-id",
  "jobEndDate": "2026-03-11T10:30:00Z",
  "validationReport": {
    "profileName": "PDF/A-1b",
    "isCompliant": true,
    "totalAssertions": 150,
    "failedAssertions": 0,
    "passedAssertions": 150
  }
}
```

**Response Format (Feature Extraction):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<report>
  <infoDict>
    <title>...</title>
    <author>...</author>
  </infoDict>
  <document>
    <pageCount>10</pageCount>
    <isEncrypted>false</isEncrypted>
  </document>
  <fonts>
    <font embedded="true" subset="false">Helvetica</font>
  </fonts>
  <!-- additional features -->
</report>
```

### 3.2.3 Validation Profile XML Format

Profiles are XML documents defining rules for a PDF standard. Example structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<profile>
  <name>PDF/A-1b</name>
  <description>ISO 19005-1:2005, Conformance level B</description>
  <rules>
    <rule id="rule1">
      <description>File must be valid PDF/A-1b</description>
      <test>/* XPath or assertion logic */</test>
    </rule>
  </rules>
</profile>
```

**Available Profiles:**
- PDF/A-1 (1b, 1a)
- PDF/A-2 (2b, 2u, 2a)
- PDF/A-3 (3b, 3u, 3a)
- PDF/A-4 (4, 4f, 4e)
- PDF/UA-1
- PDF/UA-2
- WTPDF 1.0

**Extensibility:** Profiles can be extended, but modification requires recompiling veraPDF or leveraging the policy checker for custom rules.

### 3.2.4 Feature Extraction Mode Output

**Purpose:** Extract structured metadata and properties without validation.

**Extracted Features (partial list):**
- **Information Dictionary:** Title, Author, Subject, Keywords, CreationDate, ModDate, Producer, Creator
- **Document Properties:** Page count, encryption status, encryption method, PDF version
- **Fonts:** Font names, types, embedding status, subsetting
- **Images:** Count, color spaces, compression, dimensions
- **Annotations:** Types, counts, areas
- **Color Spaces:** RGB, CMYK, Lab, Indexed, etc.
- **ICC Profiles:** Embedded profiles, color intents
- **Transparency:** Presence, blend modes, soft masks
- **Marked Content:** Presence, structure

**Configuration:** Features are controlled via `config/features.xml`. Example:

```xml
<features>
  <feature name="INFORMATION_DICTIONARY">true</feature>
  <feature name="DOCUMENT">true</feature>
  <feature name="FONTS">true</feature>
  <feature name="IMAGES">true</feature>
  <feature name="ANNOTATIONS">true</feature>
  <feature name="COLORS">true</feature>
  <feature name="TRANSPARENCY">true</feature>
  <feature name="MARKED_CONTENT">true</feature>
</features>
```

**Output:** XML report suitable for downstream processing by policy checker or custom analysis tools.

### 3.2.5 Policy Checker with Custom Schematron Rules

**Mechanism:** veraPDF policy checker processes the XML feature extraction report using Schematron (an ISO standard for XML validation using XPath assertions).

**Workflow:**
1. PDF → Feature Extraction → XML Report
2. XML Report + Policy File (Schematron) → Policy Checker
3. Result: Pass/Fail with detailed assertion failures

**Policy File Format (Schematron):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:pattern id="custom-rules">
    <!-- Assert no fonts without embedding -->
    <sch:rule context="//font">
      <sch:assert test="@embedded='true'">
        All fonts must be embedded
      </sch:assert>
    </sch:rule>

    <!-- Assert page count limit -->
    <sch:rule context="/report/document">
      <sch:assert test="pageCount &lt; 1000">
        Document must not exceed 999 pages
      </sch:assert>
    </sch:rule>

    <!-- Assert specific metadata present -->
    <sch:rule context="/report/infoDict">
      <sch:assert test="title">Title must be present</sch:assert>
      <sch:assert test="author">Author must be present</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
```

**Capabilities:**
- XPath-based assertions on XML structure
- Flexible rule composition
- Custom messages for failures
- Pattern-based rule grouping

**Limitations:**
- Requires feature extraction report; cannot directly analyze PDF content
- Schematron is XML-centric; limited to features exposed by veraPDF's feature extractor
- Complex rules can be verbose in Schematron

**Security Note:** XSLT injection vulnerability has been noted in veraPDF (GHSA-qxqf-2mfx-x8jw); ensure policy files are from trusted sources.

### 3.2.6 Docker Deployment

**Official Docker Images:**

| Image | Purpose | Port | Status |
|---|---|---|---|
| `verapdf/rest:latest` | REST API + Web UI | 8080 (API/UI), 8081 (diagnostics) | Recommended |
| `verapdf/arlington:latest` | Arlington PDF analysis | Variable | Specialized |
| `pdfix/verapdf-validation:latest` | Validation CLI | — | Community maintained |

**Multi-Stage Build:** Official image uses multi-stage build to minimize final image size (JRE only, not full JDK).

**Environment Configuration:**

```bash
docker run -d \
  -p 8080:8080 \
  -p 8081:8081 \
  -e JAVA_OPTS="-Xmx2g -Xms512m" \
  -v /path/to/config:/opt/verapdf-rest/config \
  verapdf/rest:latest
```

**Configuration Directories:**
- `/opt/verapdf-rest/config/features.xml` - Feature extraction configuration
- `/opt/verapdf-rest/config/server.yml` - HTTP server configuration
- `/opt/verapdf-rest/config/policies/` - Custom policy files

**Scaling Considerations:**
- Stateless REST API suitable for load balancing
- Each request independent; no session management required
- Memory-intensive for large PDFs; adjust JAVA_OPTS accordingly

### 3.2.7 Licensing Analysis

**Dual License Structure:**
- **GNU General Public License v3 or later (GPLv3+)**
- **Mozilla Public License v2 or later (MPLv2+)**

**SaaS Implications:**

| License | SaaS Usage | Considerations |
|---|---|---|
| **GPLv3+** | Restricted | "Conveying" a work via SaaS may trigger source disclosure obligations. Distributing Grounded as a service using GPLv3 components requires careful legal review. **Not recommended for commercial SaaS.** |
| **MPLv2+** | Permitted | MPLv2 allows mixing with proprietary code. veraPDF code must remain under MPLv2 and be source-available, but Grounded's code can be proprietary. **Recommended for SaaS.** |

**Recommendation:** Explicitly license veraPDF usage under MPLv2 to enable commercial SaaS deployment. Verify with legal counsel for specific use case.

### 3.2.8 Integration Architecture Recommendation

**Option A: Sidecar Service (Recommended for SaaS)**

```
Grounded (FastAPI) ←→ veraPDF REST Service (Docker container)
                       └─ Validates PDFs, returns reports
```

**Advantages:**
- Complete separation of concerns
- Easy scaling and independent deployment
- Updates to veraPDF don't require Grounded redeployment
- Leverages existing veraPDF Docker infrastructure

**Disadvantages:**
- Network overhead for each validation request
- Requires managing sidecar container lifecycle

**Configuration:**
- Deploy veraPDF REST in Docker container alongside Grounded
- Grounded makes HTTP POST requests to `/api/validate/{profile-id}`
- Feature extraction via `/api/features` for deeper analysis

**Option B: Embedded Java Library (Not Recommended)**

Embedding veraPDF-library directly in Grounded (as Java bytecode via Jython or subprocess):

**Disadvantages:**
- Adds Java/JVM dependency to Python stack
- Operational complexity managing JVM within Python process
- Harder to update independently

**Recommendation:** Use sidecar architecture.

### 3.2.9 Gap Analysis: veraPDF vs. Grounded

| Requirement | veraPDF | Grounded Must Build |
|---|---|---|
| **PDF/A validation** | ✓ Full | — (leverage veraPDF) |
| **PDF/UA validation** | ✓ Full | — (leverage veraPDF) |
| **Feature extraction** | ✓ Comprehensive | — (leverage veraPDF) |
| **Custom policy rules** | ✓ Via Schematron | Rule inference engine, rule feedback |
| **Detection-only (no fixes)** | ✓ Yes | — |
| **Color/ink analysis** | ✗ Limited | Ghostscript integration |
| **Font validation** | Partial | fontTools + custom rules |
| **Performance optimization** | Standard | Caching, request batching |
| **Real-time feedback** | ✗ No | Streaming detection reports |
| **Rule learning/updates** | ✗ No | ML-based rule generation |

---

## TASK 3.3: Ghostscript Assessment

### 3.3.1 Overview

Ghostscript is a PostScript and PDF interpreter and renderer. For preflight purposes, it offers specialized output devices (`inkcov`, `ink_cov`) for detecting color/ink coverage, which is valuable for print production workflows.

### 3.3.2 ink_cov Device Output Format and Capabilities

**Device Name:** `ink_cov`

**Purpose:** Reports the percentage and weight of each colorant (CMYK or RGB) on each page.

**Usage:**

```bash
gs -dSAFER -dNOPAUSE -dBATCH -o- -sDEVICE=ink_cov input.pdf
```

**Output Format:** Plain text, line per page:

```
Page 1
CMYK cover = 25.50 % (equal fill density)
Cyan = 25.50 %, Magenta = 0.00 %, Yellow = 0.00 %, Black = 5.20 %

Page 2
CMYK cover = 100.00 % (equal fill density)
Cyan = 100.00 %, Magenta = 75.30 %, Yellow = 50.10 %, Black = 25.00 %
```

**Alternative Device: `inkcov`**

Similar output, but percentages reflect the number of pixels containing each colorant (not the amount/intensity). Results in slightly different percentages:

```
Page 1
CMYK cover = 35.00 % (equal fill density)
Cyan = 30.00 %, Magenta = 5.00 %, Yellow = 2.00 %, Black = 10.00 %
```

| Aspect | ink_cov | inkcov |
|---|---|---|
| **Calculation** | Weighted per pixel | Pixel presence |
| **Use Case** | Actual ink consumption | Color presence detection |
| **Accuracy** | Higher for print planning | Higher for color detection |

### 3.3.3 Accuracy Considerations

**Strengths:**
- Rasterizes the PDF at high resolution (~300 DPI) before measuring
- Accounts for transparency and blending
- Detects all rendered colors including overprints
- Suitable for print production workflows

**Limitations:**
- Rasterization-based; not vector analysis
- Time-consuming for large documents (typically ~1-3 seconds per page)
- Requires full PDF rendering (slower than structural analysis)
- May be inaccurate for PDFs with complex transparency or non-standard color spaces
- Spot colors mapped to process colors; loses spot color identity

**Overprint & Transparency Handling:**
- Device properly respects PDF transparency and blend modes
- Overprint flags are honored during rendering
- Soft masks and masked images rendered correctly

### 3.3.4 AGPL Licensing Implications for SaaS

**License:** AGPL v3 (GNU Affero General Public License)

**SaaS "Conveying" Problem:**

The AGPL explicitly restricts SaaS deployment. Section 13 of the AGPL defines "conveying" to include:

> "If you operate a network service that allows users to interact with... a covered work through a computer network, your service must provide a mechanism for users... to obtain the source code of your modified version."

**Practical Implication:** If Grounded is offered as a SaaS, and Grounded invokes Ghostscript via API/subprocess, this may be interpreted as "conveying" Ghostscript to end users. Therefore:

- **Open SaaS:** If Grounded is AGPL-licensed, using AGPL Ghostscript is compliant.
- **Proprietary/Closed SaaS:** Using AGPL Ghostscript requires **commercial license from Artifex**.

**Risk Assessment:** High. Artifex actively enforces AGPL compliance and has taken legal action against non-compliant users.

### 3.3.5 Artifex Commercial License

**Alternative:** Purchase commercial license from Artifex Software, Inc.

**Pricing:** Not publicly disclosed; contact [email protected] for quote.

**License Features:**
- Removes AGPL restrictions
- Permits closed-source, proprietary use
- Includes commercial support options

**Typical Use Case:** Grounded as closed-source SaaS requires commercial Ghostscript license.

**Fallback Option:** If licensing cost is prohibitive, Grounded can implement custom ink coverage detection:
1. Use pikepdf to extract all content streams
2. Parse graphics state (color spaces, fill/stroke colors, overprint flags)
3. Aggregate color coverage without rasterization
4. Trade-off: Less accurate than Ghostscript rasterization, but avoids licensing issue

### 3.3.6 Decision Framework: Ghostscript vs. Custom Ink Coverage

| Criterion | Ghostscript (ink_cov) | Custom Detection |
|---|---|---|
| **Accuracy** | Very High | Moderate |
| **Licensing (SaaS)** | High Risk / Commercial License | None |
| **Performance** | Slower (~1-3s/page) | Faster (10-100ms/page) |
| **Complexity** | Low (subprocess call) | High (implement analyzer) |
| **Transparency Handling** | Perfect | Approximate |
| **Overprint Accuracy** | Perfect | Good with GS state tracking |
| **Spot Color Mapping** | Automatic (loses identity) | Can preserve identity |
| **Development Cost** | ~$0 or license fee | ~2-3 weeks engineering |
| **ROI for Grounded** | High if licensing cost < engineering cost | Depends on requirements |

### 3.3.7 Recommendation

**Strategy 1 (Recommended for MVP):** Use Ghostscript with commercial license.

**Rationale:**
- Ink coverage is critical for print preflight
- Ghostscript's rasterization-based approach is accurate
- Commercial license cost (~$5-50k/year estimate) is justified by reduced engineering effort
- Allows Grounded to launch faster with proven accuracy

**Strategy 2 (Alternative for Cost Constraints):** Implement custom ink coverage analyzer.

**Approach:**
1. Parse extended graphics state (GS) dictionaries for color parameters
2. Walk content stream operators, tracking current graphics state
3. Identify text, path fills, and image XObjects
4. Aggregate color usage without rasterization
5. Provide confidence scores for inaccurate estimations

**Strategy 3 (Hybrid):** Use custom analyzer for fast detection, fall back to Ghostscript for high-confidence validation.

---

## TASK 3.4: Poppler Tools Assessment

### 3.4.1 Overview

Poppler is a free PDF rendering library (based on xpdf-3.0 codebase). Poppler-utils is a collection of command-line tools built on Poppler for PDF manipulation and analysis.

### 3.4.2 pdffonts – Reliability for Font Detection

**Tool:** `pdffonts [options] <pdf-file>`

**Purpose:** Lists all fonts used in a PDF.

**Output:**

```
name                                 type              encoding         emb sub uni object ID
DejaVuSans                           TrueType          Identity-H        no  no  yes 12  0
Helvetica                            Type1 (Standard)  WinAnsi           no  no   no  0  0
NHLACQ+Cambria                       CIDFont           Identity-H        yes yes yes 45  0
```

**Reported Metrics:**
- **Name:** Font PostScript name
- **Type:** Type1, Type3, TrueType, CIDFont, etc.
- **Encoding:** Windows/Mac/custom encoding or Identity-H (Unicode)
- **Emb (Embedded):** Whether font is embedded in PDF
- **Sub (Subset):** Whether font is a subset
- **Uni (Unicode):** Whether Unicode mapping available (ToUnicode CMap)
- **Object ID:** PDF object reference

**Reliability Assessment:**

| Aspect | Reliability | Notes |
|---|---|---|
| **Font Identification** | High | Correctly identifies font types and properties |
| **Embedding Detection** | Very High | Reliably detects embedded fonts |
| **Subsetting Detection** | High | Detects common subsetting prefixes (e.g., `ABCDE+`) |
| **Unicode Support** | High | Detects ToUnicode CMap presence |
| **Encoding Detection** | High | Identifies encoding types |
| **Missing Fonts** | Very High | Flags fonts not present in system |

**Limitations:**
- Does not validate font file integrity
- Cannot detect missing required glyph subsets
- Does not check font licensing flags
- Limited metadata extraction beyond PostScript name

**Comparison to pikepdf:**

Both pikepdf and pdffonts can access the font dictionary. pdffonts provides more human-readable output and additional metrics (subsetting, Unicode), but pikepdf allows programmatic access for integration.

### 3.4.3 pdfimages – Image Reporting Capabilities

**Tool:** `pdfimages [options] <pdf-file> <output-prefix>`

**Purpose:** Extracts and analyzes all images in a PDF.

**Usage Variant: `-list`**

```bash
pdfimages -list myfile.pdf
```

**Output:**

```
page  num type   width height  color comp bpc  enc interp object ID x-ppi y-ppi size
   1    0 image  1200  1600   rgb    3   8  flate yes    5  0  72    72    120K
   1    1 image   800   600   gray   1   8  jpeg yes    8  0 300   300     45K
```

**Reported Metrics:**
- **Page:** Page number
- **Num:** Image index on page
- **Type:** Image, Mask, or SMask
- **Width/Height:** Image dimensions in pixels
- **Color:** Color space (RGB, CMYK, Gray, Indexed, etc.)
- **Comp:** Number of color components
- **Bpc:** Bits per component
- **Enc:** Compression encoding (JPEG, Flate, etc.)
- **Interp:** Interpolation flag
- **Object ID:** PDF object reference
- **X-ppi / Y-ppi:** Horizontal/vertical DPI (resolution)
- **Size:** Estimated uncompressed size

**Capabilities:**
- Lists all images without extraction
- Provides resolution and compression data
- Detects soft masks and image masks
- Distinguishes image types

**Limitations:**
- No color space profile detection
- Cannot validate image integrity
- No analysis of rendering intent or overprint flags
- Limited metadata (no creation date, camera info, etc.)

### 3.4.4 pdfinfo – Page Box Reporting

**Tool:** `pdfinfo [options] <pdf-file>`

**Purpose:** Reports document metadata and properties.

**Output:**

```
Title:          My Document
Author:         John Doe
Subject:        Technical Report
Keywords:       PDF, preflight
Creator:        Adobe InDesign CS6
Producer:       Adobe PDF Library 9.0
CreationDate:   Wed Mar 11 12:34:56 2026
ModDate:        Wed Mar 11 14:22:18 2026
Trapped:        Unknown
Encrypt:        none
Page size:      612 x 792 pts (letter)
Pages:          42
File size:      2456123 bytes
Optimized:      no
PDF version:    1.4
```

**Page Box Access:**

The standard `pdfinfo` output shows "Page size," which corresponds to the effective page dimensions (CropBox if defined, else MediaBox). However, the `-box` option (if available) may provide detailed box information:

```
MediaBox:  [0 0 612 792]
CropBox:   [36 36 576 756]
BleedBox:  [0 0 612 792]
TrimBox:   [0 0 612 792]
ArtBox:    [0 0 612 792]
```

**Note:** The `-box` option availability depends on Poppler version. Check `pdfinfo --help` for your installation.

**Capabilities:**
- Reports all document metadata
- Page box dimensions
- Encryption status and type
- PDF version
- File optimization status

### 3.4.5 Comparison: Poppler vs. pikepdf

| Feature | Poppler | pikepdf | Winner |
|---|---|---|---|
| **Font Reporting** | Good (human-readable) | Programmatic access | Tie (different use cases) |
| **Page Box Access** | Limited (basic dimensions) | Full (all 5 boxes, programmatic) | pikepdf |
| **Image Analysis** | Good (resolution, compression) | Good (programmatic API) | Tie |
| **Metadata Access** | Good (human-readable) | Programmatic access | Tie |
| **Integration** | CLI tool; requires subprocess | Python library | pikepdf |
| **Performance** | Moderate (~100-500ms per tool) | Fast (C++ backend) | pikepdf |
| **Parsing Accuracy** | Reliable | Reliable | Tie |
| **Extensibility** | Limited (CLI output parsing) | High (Python API) | pikepdf |

### 3.4.6 Decision: Include Poppler or Rely on pikepdf Alone?

**Recommendation:** Rely primarily on pikepdf; use Poppler for specific validation workflows only.

**Rationale:**

1. **pikepdf is sufficient** for object-level analysis (fonts, images, boxes, metadata)
2. **Poppler's CLI tools** are useful for:
   - Quick human validation (e.g., `pdffonts file.pdf | grep missing`)
   - Parsing human-readable reports in scripts
   - Educational/debugging workflows
3. **Integration complexity** of parsing Poppler CLI output is higher than using pikepdf's Python API
4. **Performance:** subprocess calls to Poppler tools slower than pikepdf's C++ backend

**Integration Strategy:**

- **Primary:** pikepdf for all programmatic PDF analysis
- **Secondary (Optional):** Poppler tools for validation or fallback checks
- **CLI Fallback:** Provide Poppler as optional dependency for debugging/validation workflows

**Example Hybrid Approach:**

```python
# Primary: pikepdf
pdf = pikepdf.open('file.pdf')
fonts = pdf.pages[0].Resources.Font

# Fallback: Poppler CLI for additional validation
import subprocess
result = subprocess.run(['pdffonts', 'file.pdf'], capture_output=True, text=True)
# Parse result.stdout for additional checks
```

---

## TASK 3.5: Little CMS Assessment

### 3.5.1 Overview

Little CMS (lcms2) is a free, open-source Color Management Module (CMM) implementing the ICC Profile standard. It provides fast color transformations and ICC profile I/O in C, with Python bindings available through Pillow (PIL).

### 3.5.2 ICC Profile Parsing Capabilities

| Capability | Status | Notes |
|---|---|---|
| **V2 Profiles** | ✓ Full | Complete support for ICC v2 profiles |
| **V4 Profiles** | ✓ Full | Complete support for ICC v4 profiles |
| **Profile Types** | ✓ Full | Input, Display, Output, Abstract, DeviceLink, NamedColor |
| **Tag Access** | ✓ Yes | Direct access to ICC profile tags |
| **Header Info** | ✓ Yes | Profile size, version, device class, color space, rendering intent |
| **Curve Tables** | ✓ Yes | TRC, A2B0, B2A0, LUT, Matrix profiles |
| **Color Space Conversion** | ✓ Yes | RGB ↔ CMYK ↔ Lab ↔ XYZ, etc. |
| **Softproof/Simulation** | ✓ Yes | Simulates output on different devices |
| **Profile Validation** | ✓ Partial | Basic validation; stricter validation in recent versions |

**Profile Tag Support (Partial List):**
- **profileDescription** (desc): Human-readable profile name
- **mediaIlluminant** (mILL): Reference illuminant
- **colorantTable** (clrt): Spot color names and Lab values
- **colorantOrder** (clro): Colorant sequence
- **mediaRelativePermeance** (mrel): Media properties
- **chromatic** (chrm): Chromatic adaptation
- **mediaBlackPoint** (bXYZ): Media black point

### 3.5.3 Profile Validation

**Current State (lcms2):**

- **Basic Validation:** lcms2 validates profile syntax and tag structure
- **Conformance Checking:** Recent versions (post-2020) implement stricter ICC spec 4.4 validation
- **Fuzz-Hardening:** Ongoing improvements to reject malformed profiles
- **Limits Checking:** Validates numeric ranges and tag consistency

**Limitations:**

- No built-in license flag checking (permitted for specific use in profiles)
- Cannot validate rendering intent applicability for device
- Limited semantic validation (e.g., matrix profile invertibility)
- Does not check profile optimization or gamut coverage

**Validation Output:**

lcms2 returns error codes on profile opening. Basic validation:

```python
from PIL import ImageCms

try:
    profile = ImageCms.createProfile("PATH", outputMode='RGB')
    # Profile is valid
except OSError as e:
    # Profile is invalid: e.args[0] contains error message
    pass
```

### 3.5.4 Python Binding Options

**Option 1: Pillow (PIL) ImageCms Module (Recommended)**

- **Status:** Stable, widely used
- **Coverage:** Core ICC profile functionality
- **API:**

```python
from PIL import Image, ImageCms

# Open profile
icc_profile = open('profile.icc', 'rb').read()
profile = ImageCms.ImageCmsProfile(icc_profile)

# Transform image
input_mode = 'RGB'
output_mode = 'CMYK'
transformer = ImageCms.buildTransform(input_image_profile, output_profile, input_mode, output_mode)
converted_image = ImageCms.applyTransform(image, transformer)
```

**Limitations:**
- Limited to common color spaces
- No direct tag access (only transformation)
- Profile I/O is image-centric

**Option 2: python-liblcms2 (Direct Binding)**

- **Status:** Less common; fewer recent releases
- **Coverage:** More complete API coverage
- **Installation:** `pip install liblcms2`

```python
import liblcms2 as cms

# Open profile
profile = cms.cmsOpenProfileFromFile('profile.icc', 'r')
device_class = cms.cmsGetDeviceClass(profile)
profile_version = cms.cmsGetProfileVersion(profile)

# Access tags
tag_count = cms.cmsGetTagCount(profile)
for i in range(tag_count):
    tag_sig = cms.cmsGetTagSignature(profile, i)
    tag_data = cms.cmsReadTag(profile, tag_sig)
```

**Advantages:**
- Direct C library access
- More complete API
- Lower-level control

**Disadvantages:**
- Less stable; fewer users
- Requires C compiler for installation
- Less documentation

**Option 3: Custom ctypes Binding**

- Wrap lcms2.h directly using Python's ctypes
- Provides maximum control
- Requires careful memory management

### 3.5.5 Integration Approach for Grounded

**Recommended Integration:**

1. **Profile Discovery:** Use pikepdf to locate embedded ICC profiles in PDFs
   ```python
   pdf = pikepdf.open('file.pdf')
   # Access /OutputIntent in Catalog
   # Access /ICC in ColorSpace dictionaries
   ```

2. **Profile Parsing:** Use Pillow's ImageCms to load and analyze profiles
   ```python
   from PIL import ImageCms

   icc_data = extract_profile_from_pdf(pdf)
   profile = ImageCms.ImageCmsProfile(icc_data)
   profile_mode = ImageCms.getDefaultIntent(profile)  # or similar
   ```

3. **Validation:** Check profile consistency with PDF color space declarations
   ```python
   # Verify RGB profile is used with RGB color space, etc.
   # Validate profile version (V2 vs V4)
   # Check for required tags based on profile type
   ```

4. **Fallback:** For deep validation beyond Pillow's API, implement custom tag reader using ctypes or python-liblcms2

**Validation Rule Examples:**

```python
# Rule: All color spaces must have matching ICC profiles
# Rule: RGB profiles must be DeviceRGB type
# Rule: CMYK profiles must use CMYK color space
# Rule: Lab profiles require proper illuminant and observer
# Rule: Embedded profiles must match declared color intents
```

### 3.5.6 Preflight Checks Enabled by ICC Profile Analysis

| Check | Requirement | Implementation |
|---|---|---|
| **Profile Presence** | Output intent must be defined | Check /OutputIntent in Catalog |
| **Profile Embedding** | Recommended | Check if profile is embedded vs. external |
| **Profile Validity** | Must be valid ICC v2 or v4 | Load and validate with lcms2 |
| **Color Space Match** | Profile must match document color space | Cross-check profile device class vs. PDF ColorSpace |
| **Rendering Intent** | Must be valid and declared | Check /Intent in /OutputIntent dictionary |
| **Fallback Color Space** | Must be defined if profile is external | Check alternate ColorSpace in Image XObjects |
| **Profile Version Compatibility** | V2 for PDF/A-1; V4 for PDF/A-2+ | Validate lcms2 version field |

### 3.5.7 Gap Analysis: Little CMS vs. Grounded

| Requirement | lcms2 | Grounded Must Build |
|---|---|---|
| **Profile I/O** | ✓ Full | — |
| **Tag Parsing** | ✓ Full (with ctypes) | — (or use lcms2 directly) |
| **Color Transformation** | ✓ Full | — (if needed for gamut checking) |
| **Profile Validation** | Partial | Extended validation rules, rendering intent inference |
| **DeviceLink Chains** | ✓ Yes | Analysis of multi-hop transforms |
| **Embedded Profile Extraction** | ✗ No | Custom extraction via pikepdf + ICC spec |
| **Profile Optimization Checks** | ✗ No | Custom size/performance validation |

### 3.5.8 Recommendation

**Integration:** Use Pillow's ImageCms as primary interface; optional python-liblcms2 for advanced tag access.

**Approach:**

1. **Phase 1 (MVP):** Pillow ImageCms for basic profile validation
   - Verify profile openability
   - Check color space consistency
   - Validate rendering intents

2. **Phase 2 (Enhancement):** python-liblcms2 for deep tag analysis
   - Extract metadata tags (profileDescription, colorantTable)
   - Validate tag consistency
   - Check profile version compatibility

3. **Phase 3 (Advanced):** Color transformation simulation
   - Gamut mapping validation
   - Softproof simulation for output intent
   - Color accuracy reporting

---

## Cross-Tool Capability Matrix

### All Tools Comparison

| Capability | pikepdf | QPDF | veraPDF | Ghostscript | Poppler | lcms2 |
|---|---|---|---|---|---|---|
| **Object Model** | ✓✓ | ✓✓ | — | — | ✓ | — |
| **Content Streams** | ✓✓ | ✓ | ✓ | — | ✓ | — |
| **Page Boxes** | ✓✓ | ✓ | ✓ | — | ✓ | — |
| **Fonts** | ✓ | ✓ | ✓ | — | ✓✓ | — |
| **Images** | ✓✓ | — | ✓ | ✓ | ✓✓ | — |
| **Annotations** | ✓ | — | ✓ | — | — | — |
| **Color Spaces** | ✓ | — | ✓ | — | — | ✓ |
| **ICC Profiles** | ✓ | — | ✓ | — | — | ✓✓ |
| **Encryption** | ✓ | ✓ | — | — | ✓ | — |
| **Metadata** | ✓ | ✓ | ✓ | — | ✓✓ | — |
| **PDF/A Validation** | — | — | ✓✓ | — | — | — |
| **Ink Coverage** | — | — | — | ✓✓ | — | — |
| **SaaS Friendly** | ✓ (Apache 2.0) | ✓ (Apache 2.0) | ✓ (MPL 2.0) | ✗ (AGPL) | ✓ (GPL 3.0) | ✓ (MIT/LGPL) |

---

## Recommended Technology Stack for Grounded

### Foundation Layer (Required)

| Component | Tool | Rationale |
|---|---|---|
| **Object Model & Structural Analysis** | pikepdf | Python API, fast C++ backend, complete object access |
| **PDF/A Validation** | veraPDF (sidecar) | Industry-standard, REST API, feature extraction |
| **Ink Coverage Detection** | Ghostscript (with commercial license) OR Custom analyzer | Accurate for print preflight; licensing must be resolved |
| **ICC Profile Analysis** | Pillow ImageCms + python-liblcms2 | Color space validation, profile consistency |

### Enhancement Layer (Recommended)

| Component | Tool | Purpose |
|---|---|---|
| **Font Validation** | fontTools | Deep glyph, subsetting, and license validation |
| **Content Stream Semantics** | Custom parser on pikepdf | Graphics state tracking, operator interpretation |
| **CLI Reference Validation** | Poppler tools (optional) | Human-readable reports, educational use |

### Integration Architecture

```
┌─────────────────────────────────────────────┐
│         Grounded (FastAPI + Celery)         │
│   Detection Engine with Rule Inference      │
├─────────────────────────────────────────────┤
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │  pikepdf + Custom Content Analyzer    │ │
│  │  - Object model access                │ │
│  │  - Content stream semantic analysis   │ │
│  │  - Font/Image resource extraction     │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │  Pillow ImageCms + python-liblcms2    │ │
│  │  - ICC profile parsing                │ │
│  │  - Color space validation             │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │  fontTools (optional for Phase 2+)    │ │
│  │  - Font glyph validation              │ │
│  │  - License flag detection             │ │
│  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
             ↓              ↓              ↓
      ┌────────────┐  ┌──────────────┐  ┌──────────────┐
      │ veraPDF    │  │ Ghostscript  │  │   Poppler    │
      │ (REST API) │  │  (via Celery)│  │  (optional)  │
      │ Sidecar    │  │  subprocess) │  │   CLI tools  │
      │ Container  │  │              │  │              │
      └────────────┘  └──────────────┘  └──────────────┘
```

### Deployment Topology

**Docker Compose Setup:**

```yaml
version: '3.8'
services:
  grounded:
    build: ./grounded
    ports:
      - "8000:8000"
    environment:
      VERAPDF_URL: "http://verapdf:8080"
      GHOSTSCRIPT_BIN: "/usr/bin/gs"
    depends_on:
      - verapdf
      - redis

  verapdf:
    image: verapdf/rest:latest
    ports:
      - "8080:8080"
    environment:
      JAVA_OPTS: "-Xmx4g -Xms1g"
    volumes:
      - ./verapdf-config:/opt/verapdf-rest/config

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## Summary of Findings and Decisions

### Phase 3 Deliverables

1. **pikepdf/QPDF (Task 3.1)**
   - pikepdf recommended as primary structural foundation
   - QPDF C++ backend ensures performance
   - Content stream tokenization sufficient; semantic analysis must be built by Grounded
   - **Gap:** No semantic understanding, font/color validation, ink coverage detection

2. **veraPDF (Task 3.2)**
   - Sidecar REST service architecture recommended
   - Dual licensing (MPL 2.0 preferred for commercial SaaS)
   - Feature extraction enables policy checking
   - **Gap:** Limited to PDF/A/UA standards; color/ink analysis limited

3. **Ghostscript (Task 3.3)**
   - ink_cov device accurate for print preflight
   - AGPL licensing requires commercial license for SaaS use
   - **Decision:** Purchase commercial license OR implement custom analyzer as fallback
   - Trade-off analysis supports licensing if cost < engineering effort

4. **Poppler (Task 3.4)**
   - Good for reference/validation but not necessary with pikepdf
   - Optional fallback for CLI-based checks
   - **Recommendation:** Primary reliance on pikepdf; Poppler as secondary

5. **Little CMS (Task 3.5)**
   - Pillow ImageCms + python-liblcms2 for ICC profile analysis
   - Phase 1: Basic profile validation; Phase 2+: Deep tag analysis
   - **Gap:** Custom validation rules for PDF/A and rendering intent consistency

### Critical Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Structural Analysis** | pikepdf | Python API, performance, completeness |
| **Validation** | veraPDF (sidecar) | Industry standard, REST API, independent deployment |
| **Ink Coverage** | Ghostscript (licensed) | Accuracy justifies cost; custom alternative available |
| **ICC Profiles** | Pillow + lcms2 | Python-friendly, two-tier approach (basic + advanced) |
| **Content Semantics** | Custom Implementation | No library provides this; Grounded's core innovation |
| **Architecture** | Sidecar Services + Library Stack | Separation of concerns, independent scaling, clear APIs |

---

## References and Sources

**pikepdf Documentation:**
- [pikepdf 10.5.0 Official Documentation](https://pikepdf.readthedocs.io/)
- [pikepdf Tutorial](https://pikepdf.readthedocs.io/en/latest/tutorial.html)
- [Working with Content Streams](https://pikepdf.readthedocs.io/en/latest/topics/content_streams.html)
- [Working with Pages](https://pikepdf.readthedocs.io/en/latest/topics/page.html)
- [Working with Images](https://pikepdf.readthedocs.io/en/latest/topics/images.html)
- [GitHub Repository: pikepdf/pikepdf](https://github.com/pikepdf/pikepdf)

**QPDF Documentation:**
- [QPDF Official Documentation](https://qpdf.readthedocs.io/en/stable/)
- [GitHub Repository: qpdf/qpdf](https://github.com/qpdf/qpdf)

**veraPDF Documentation and Resources:**
- [veraPDF Official Documentation](https://docs.verapdf.org/)
- [veraPDF CLI Validation](https://docs.verapdf.org/cli/validation/)
- [veraPDF CLI Configuration](https://docs.verapdf.org/cli/config/)
- [veraPDF Feature Extraction](https://docs.verapdf.org/cli/feature-extraction/)
- [veraPDF Policy Checking](https://docs.verapdf.org/policy/)
- [veraPDF Processor API](https://docs.verapdf.org/develop/processor/)
- [veraPDF REST Client Demo](https://demo.verapdf.org/)
- [veraPDF GitHub Repository](https://github.com/veraPDF/veraPDF-rest)
- [veraPDF Docker Images](https://hub.docker.com/r/verapdf/rest)
- [veraPDF Validation Profiles GitHub](https://github.com/veraPDF/veraPDF-validation-profiles)
- [Policy-based Assessment with veraPDF - First Impression](https://bitsgalore.org/2017/06/01/policy-based-assessment-with-verapdf-a-first-impression.html)

**Ghostscript:**
- [Ghostscript Official Documentation](https://ghostscript.com/)
- [Ghostscript Licensing](https://ghostscript.com/licensing/)
- [Ghostscript FAQ](https://ghostscript.com/faq/)
- [Ghostscript Output Devices](https://ghostscript.readthedocs.io/en/latest/Devices.html)
- [Artifex Commercial Licensing](https://artifex.com/licensing)
- [Conditions on Distributing Ghostscript in a Commercial Context](https://ghostscript.com/docs/9.54.0/Commprod.htm)

**Poppler:**
- [Poppler Official Website](https://poppler.freedesktop.org/)
- [Wikipedia: Poppler](https://en.wikipedia.org/wiki/Poppler_(software))
- [PDF Processing and Analysis with Open-Source Tools](https://www.bitsgalore.org/2021/09/06/pdf-processing-and-analysis-with-open-source-tools)
- [Poppler Tools in Ubuntu](https://www.glukhov.org/post/2025/04/ubuntu-poppler/)
- [GitHub: elswork/poppler-utils](https://github.com/elswork/poppler-utils)

**Little CMS:**
- [Little CMS Official Website](https://www.littlecms.com/)
- [Little CMS GitHub Repository](https://github.com/mm2/Little-CMS)
- [Pillow ImageCms Module Documentation](https://pillow.readthedocs.io/en/stable/reference/ImageCms.html)
- [ICC Profile Resources](https://www.color.org/opensource.xalter)

---

**Document Status:** Complete Phase 3 Assessment (Tasks 3.1–3.5)
**Next Phase:** Architecture Design and Integration Planning
**Audience:** Development Team, Technical Decision Makers, Architecture Review Board
