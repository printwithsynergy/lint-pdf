# GROUNDED PHASE 5: TEST CORPUS ASSEMBLY PLANNING DELIVERABLES

**Project:** Grounded — Detection-Only PDF Preflight Engine
**Phase:** 5 — Test Corpus Assembly and CI Infrastructure
**Document Type:** Research and Planning Specifications
**Created:** 2026-03-11
**Status:** Planning Phase (NOT implementation)

---

## Table of Contents

1. [TASK 5.1: Standards Test Suites Index](#task-51-standards-test-suites-index)
2. [TASK 5.2: Generator Coverage Plan](#task-52-generator-coverage-plan)
3. [TASK 5.3: Failure Mode Library Specification](#task-53-failure-mode-library-specification)

---

## TASK 5.1: STANDARDS TEST SUITES INDEX

### Purpose

This index catalogs all available industry-standard PDF test file collections that Grounded should integrate into its regression testing infrastructure. These collections provide comprehensive, validated test cases covering PDF/A, PDF/UA, PDF/X, and general PDF specifications. Each collection serves a distinct validation purpose and should be incorporated into LintPDF's CI pipeline.

---

### 1. **veraPDF Test Corpus**

**Repository:** https://github.com/veraPDF/veraPDF-corpus

**Overview:**
The veraPDF test corpus is the most comprehensive open-source PDF validation test suite. It is maintained by the veraPDF organization (part of the Open Preservation Foundation) and provides atomic test files for every clause in ISO 19005 (PDF/A) and ISO 14289 (PDF/UA) specifications.

**Test Coverage:**
- PDF/A-1 (Levels: 1b, 1a)
- PDF/A-2 (Levels: 2b, 2a, 2u)
- PDF/A-3 (Levels: 3b, 3a, 3u)
- PDF/A-4 (Levels: 4, 4e, 4f)
- PDF/UA (Versions: UA1, UA2)
- ISO 32000-1 (PDF 1.7)
- ISO 32000-2 (PDF 2.0)
- Tagged PDF and logical structure test files

**Organization Structure:**

```
veraPDF-corpus/
├── PDFA-1b/
│   ├── [atomic test files for each clause violation]
│   └── [pass and fail variants]
├── PDFA-1a/
├── PDFA-2b/
├── PDFA-2a/
├── PDFA-2u/
├── PDFA-3b/
├── PDFA-3a/
├── PDFA-3u/
├── PDFA-4/
├── PDFA-4e/
├── PDFA-4f/
├── PDFUA-1/
├── PDFUA-2/
├── tagged-pdfs/
│   └── [Tagged PDF and logical structure test files]
└── README.md
```

Each directory follows a systematic naming convention tied to specific ISO 19005 or ISO 14289 clause requirements. Files are explicitly designed to test individual requirements in isolation (atomic test approach).

**Key Characteristics:**
- **Atomic Design:** Each file violates or complies with exactly one clause
- **Naming Convention:** Files include clause numbers and requirement identifiers
- **Validation Intent:** Files are explicitly designed to validate conformance validators ("validate the validators")
- **Supplementary Repositories:** Specialized corpora exist for specific features:
  - `veraPDF-corpus-PDFA-1b` (focused PDF/A-1b subset)
  - `veraPDF-corpus-PDFA-Tagged` (Tagged PDF and logical structure)

**How to Use in LintPDF's CI:**

```
Integration Strategy:
1. Clone or mirror veraPDF-corpus into LintPDF's test-fixtures directory
2. Organize by PDF standard version (PDFA1B, PDFA2B, PDFA3B, PDFUA1, etc.)
3. For each standard version, separate into "pass" and "fail" subdirectories
4. Create a registry mapping each file to its expected validation result
5. Run Grounded against each file and compare findings to expected results
6. Track per-standard pass/fail rates and regression statistics
7. Flag any unexpected deviations in CI logs

Expected Findings JSON for each file:
- File path
- Standard version
- Clause violated (if fail case)
- Expected finding category (font, color, structure, etc.)
- Severity (error vs. warning)
- Conformance decision (pass/fail)
```

**Estimated Test Volume:**
- 1,500+ atomic test files (across all standards)
- Coverage of ~98% of all PDF/A and PDF/UA conformance clauses

**Maintenance:**
- veraPDF corpus is actively maintained
- New test files added with specification updates
- Subscribe to repository for updates

---

### 2. **Isartor Test Suite**

**Source:** PDF Association (https://pdfa.org/)
**Standard:** PDF/A-1 (ISO 19005-1)

**Overview:**
The Isartor test suite is the "gold standard" for PDF/A-1 validation. The name comes from the Norse mythology concept of validating validators—it deliberately violates PDF/A-1 requirements in systematic ways to ensure that validators properly detect non-conformance.

**Purpose:**
"Validate the validators" — systematically violate each PDF/A-1 requirement to verify that a preflight tool correctly identifies violations. This is critical for Grounded because it allows us to verify that we're not under-reporting issues.

**Test Coverage:**
- PDF/A-1b (Level B conformance violations)
- PDF/A-1a (Level A conformance violations) — separate suite
- Systematic violations of every normative requirement in ISO 19005-1

**Organization:**
The suite is organized by PDF/A-1 specification clauses:
- File extensions and naming indicate clause numbers
- Each file deliberately violates one or more specific requirements
- Clear documentation of what each file violates

**Key Characteristics:**
- **Negative Testing Focus:** These files are intentionally non-conformant
- **Comprehensive Coverage:** Covers every normative clause in PDF/A-1
- **Atomic Design:** Generally one violation per file
- **Well-Documented:** Each file includes metadata indicating what it violates

**How to Use in LintPDF's CI:**

```
Integration Strategy:
1. Download Isartor test suite from PDF Association
2. Create test-fixtures/isartor-pdfa1b/ and test-fixtures/isartor-pdfa1a/
3. All files in this suite are EXPECTED TO FAIL PDF/A-1 conformance
4. Run Grounded against each file
5. Verify that Grounded reports findings for all violations
6. Create a mapping: isartor-file-name → expected-violations
7. Flag any file where Grounded does NOT report expected violations
8. This is critical for "false negatives" regression testing

False Negative Detection:
- If Grounded passes a file that Isartor says should fail PDF/A-1:
  - This is a CRITICAL REGRESSION
  - Indicates a missing validation check
  - Requires immediate investigation and fix
```

**Estimated Test Volume:**
- 150+ test files
- Full coverage of PDF/A-1b and PDF/A-1a specification clauses

**Availability:**
- Freely available from PDF Association
- Available on GitHub and direct download
- Well-maintained and stable

**Historical Context:**
Isartor is the predecessor to veraPDF corpus. While veraPDF is more comprehensive, Isartor remains the authoritative source for PDF/A-1 validation testing and is used by many production validators.

---

### 3. **Bavaria Test Suite**

**Source:** PDF Association
**Standard:** PDF/A-2 and PDF/A-3 (ISO 19005-2, ISO 19005-3)

**Overview:**
Bavaria is the follow-on test suite to Isartor, providing systematic PDF/A-1 violation testing for PDF/A-2 and PDF/A-3 specifications. Named after the Bavarian context of PDF standardization work, it maintains the same "validate the validators" philosophy as Isartor.

**Test Coverage:**
- PDF/A-2b, PDF/A-2a, PDF/A-2u (conformance violations)
- PDF/A-3b, PDF/A-3a, PDF/A-3u (conformance violations)
- New features in PDF/A-2: transparency support, OpenType fonts, embedded files
- New features in PDF/A-3: embedded files (enhanced), digital signatures

**Organization Structure:**

```
bavaria-test-suite/
├── PDFA-2b-violations/
├── PDFA-2a-violations/
├── PDFA-2u-violations/
├── PDFA-3b-violations/
├── PDFA-3a-violations/
└── PDFA-3u-violations/
```

Each directory contains atomic test files violating specific clauses.

**Key Differences from Isartor:**

| Feature | Isartor (PDF/A-1) | Bavaria (PDF/A-2/3) |
|---------|-------------------|---------------------|
| Transparency | Not allowed | Allowed (PDF/A-2/3) |
| Embedded files | Not allowed | Allowed (PDF/A-3) |
| OpenType fonts | Limited | Full support |
| Color spaces | DeviceGray, CalGray, Indexed, Lab, DeviceRGB, DeviceCMYK, DeviceN | Extended |
| Digital signatures | Not part of spec | Part of PDF/A-3 |

**How to Use in LintPDF's CI:**

```
Integration Strategy:
1. Download Bavaria test suite from PDF Association
2. Organize by standard: test-fixtures/bavaria-pdfa2b/, etc.
3. Like Isartor, all files are intentionally non-conformant
4. Run Grounded against each file and verify violation detection
5. Compare results to LintPDF's declared PDF/A-2 and PDF/A-3 support
6. Pay special attention to:
   - Transparency violation detection (new in PDF/A-2)
   - Embedded file validation (new in PDF/A-3)
   - OpenType font handling

Critical Test Cases to Monitor:
- PDF/A-2 transparency violations (should be flagged)
- PDF/A-3 embedded file issues
- Signature validation (if Grounded supports it)
```

**Estimated Test Volume:**
- 200+ test files (combined PDF/A-2 and PDF/A-3)

**Maintenance Status:**
- Actively maintained by PDF Association
- Updated with specification errata and clarifications

---

### 4. **GWG Test Files (Ghent Workgroup PDF Certification)**

**Source:** Ghent Workgroup (https://gwg.org/)
**Standard:** PDF/X-4 and PDF/X Output Suite

**Overview:**
The GWG (Ghent Workgroup) maintains a comprehensive test file suite for PDF/X certification, specifically PDF/X-4 compliance. These 260 test files are used to certify that preflighting and workflow software correctly handle real-world printing scenarios.

**Test Coverage:**

The 260-file suite tests:
- **Image Resolution:** Minimum DPI requirements (72, 150, 300, 600 DPI variants)
- **Color Space Compliance:** CMYK, spot colors, separation names
- **Overprint Settings:** White/black overprint, ink coverage limits
- **Spot Color Handling:** Named spot colors, color values, separation names
- **Ink Coverage:** Total ink density limits (typically 240% or 320%)
- **PDF/X-4 Specific Features:** Transparency, blending modes, extended graphics state
- **Page Size and Bleed:** Correct bounding boxes, bleed areas
- **Content Stream Integrity:** Valid operators, font references

**Organization:**

```
gwg-test-files/
├── resolution-tests/
│   ├── 72dpi-images/
│   ├── 150dpi-images/
│   ├── 300dpi-images/
│   └── 600dpi-images/
├── color-space-tests/
│   ├── cmyk/
│   ├── spot-colors/
│   └── mixed-spaces/
├── overprint-tests/
├── ink-coverage-tests/
├── bleed-and-trim-tests/
├── transparency-tests/
└── combined-compliance-tests/
```

**Critical Test Categories:**

1. **Image Resolution Testing:**
   - Same image at 72, 150, 300, 600 DPI variants
   - Tests that Grounded correctly measures image resolution
   - Tests that minimum DPI requirements are enforced per page type

2. **Spot Color Naming and Values:**
   - Named spot colors with correct CMYK values
   - Spot color naming conflicts (same name, different values)
   - Separation plate names vs. color names

3. **Overprint Behavior:**
   - White text with overprint enabled (should be flagged as suspicious)
   - Black text with overprint (generally acceptable)
   - Spot color overprint interactions

4. **Ink Coverage:**
   - Files with total ink coverage 100%, 200%, 240%, 320%, 400%+
   - Tests that Grounded calculates ink coverage correctly
   - Tests compliance against coverage limits

5. **Transparency and Blending:**
   - PDF/X-4 allows transparency (unlike PDF/X-1a)
   - Various blend modes (Multiply, Screen, Overlay, etc.)
   - Transparency with spot colors

**How to Use in LintPDF's CI:**

```
Integration Strategy:
1. Obtain GWG test files (available from gwg.org with certification)
2. Organize by test category in test-fixtures/gwg-pdfa/
3. Create comprehensive test matrix:

Test Matrix Structure:
{
  "test_file": "gwg_resolution_300dpi_cmyk.pdf",
  "category": "image-resolution",
  "expected_findings": {
    "images": [
      {
        "name": "Image_001",
        "detected_dpi": 300,
        "min_required_dpi": 300,
        "status": "pass"
      }
    ],
    "color_spaces": ["DeviceCMYK"],
    "spot_colors": [],
    "overprint_suspicious": false
  },
  "test_file": "gwg_overprint_white_text.pdf",
  "category": "overprint",
  "expected_findings": {
    "white_text_with_overprint": true,
    "warning_level": "high",
    "message": "White text with overprint may disappear"
  }
}

4. Run Grounded against each file
5. Compare detected findings to expected matrix
6. Report mismatches with high priority (likely real bugs)
```

**Measurement Methodology:**

For the 260 files, create a master evaluation sheet:

```
test_file | category | sub_category | pass/fail | notes
----------|----------|--------------|-----------|-------
gwg_001   | resolution | 300dpi | PASS | Correctly detected
gwg_002   | resolution | 72dpi  | PASS | Correctly flagged
gwg_003   | overprint  | white  | PASS | Correctly warned
gwg_004   | overprint  | black  | PASS | Correctly approved
...
```

**Estimated Test Volume:**
- Exactly 260 test files
- Organized across 8-10 major test categories
- Each file focuses on 1-2 specific preflight issues

**Availability:**
- Proprietary GWG resource
- Available with GWG certification membership
- Open-source mirrors may exist (verify licensing)
- Contact gwg.org for access

**Critical for Grounded:**
These files are essential for production-readiness because they test real-world printing workflow requirements. Grounding's ability to correctly handle GWG test files indicates fitness for professional printing environments.

---

### 5. **PDF Association Corpora Index (Master Registry)**

**Repository:** https://github.com/pdf-association/pdf-corpora

**Overview:**
The PDF Association maintains a master index/registry of ALL known PDF test file collections. This is not itself a test corpus but a comprehensive catalog and metadata index pointing to dozens of other corpora.

**What It Contains:**

The repository provides:
- **Unified Index:** Metadata about every known PDF test collection
- **Collection Descriptions:** Purpose, coverage, file count, standards
- **Availability Information:** How to obtain each collection (GitHub links, direct downloads, etc.)
- **Usage Guidelines:** Recommendations for when to use each collection
- **Relationship Map:** How collections relate to each other

**Key Collections Referenced:**

| Collection | Standard | Files | Purpose |
|-----------|----------|-------|---------|
| veraPDF corpus | PDF/A, PDF/UA | 1500+ | Comprehensive validation |
| Isartor | PDF/A-1 | 150+ | Validate the validators |
| Bavaria | PDF/A-2, PDF/A-3 | 200+ | Validate the validators |
| GWG | PDF/X-4 | 260 | Print workflow validation |
| PDF/VT Test Suite | PDF/VT | Variable | Variable data printing |
| PDF 2.0 Examples | PDF 2.0 | 50+ | Educational examples |
| Cal Poly PDF/VT | PDF/VT | 4 sets | Print on demand |
| PDFE Test Corpus | PDF/E | 100+ | Engineering PDFs |
| PDF/M Test Files | PDF/M | 50+ | Medical imaging |
| Real-world PDFs | General | 1000s | Production documents |

**How to Use in LintPDF's CI:**

```
Integration Strategy:
1. Use pdf-corpora repo as the "master catalog"
2. For each major PDF standard (PDF/A, PDF/X, PDF/E, PDF/M):
   - Identify all relevant collections from the index
   - Determine which are mission-critical for Grounded
   - Create integration plan per collection

2. Create metadata file: test-fixtures/COLLECTIONS_MANIFEST.json
   {
     "collections": [
       {
         "name": "veraPDF",
         "standard": "PDF/A,PDF/UA",
         "source": "https://github.com/veraPDF/veraPDF-corpus",
         "mirror_path": "test-fixtures/verapdf/",
         "file_count": 1500,
         "status": "active",
         "update_frequency": "quarterly",
         "critical": true,
         "last_synced": "2026-03-01"
       },
       ...
     ],
     "total_test_files": 5000,
     "coverage": "PDF/A,PDF/UA,PDF/X,PDF/E,General PDF"
   }

3. Implement automated sync system:
   - Monthly check for updates in each collection
   - Automatic mirroring to test-fixtures/
   - CI runs all collections in regression
```

**Maintenance Responsibility:**

The PDF Association actively maintains this index, so Grounded should:
- Subscribe to the repository for updates
- Review quarterly for new collections relevant to LintPDF's mission
- File issues/PRs if collections are missing or out of date

**Strategic Value:**

By using the PDF Association's official index, Grounded:
- Avoids duplicating test corpus discovery work
- Stays current with new test collections
- Gains credibility through use of official resources
- Participates in the broader PDF validation ecosystem

---

### Summary: Test Suite Integration Strategy

**Immediate Priority (MVP):**
1. ✅ veraPDF corpus — comprehensive, well-maintained
2. ✅ Isartor suite — authoritative for PDF/A-1
3. ✅ Bavaria suite — covers PDF/A-2, PDF/A-3
4. ✅ PDF Association corpora index — master registry

**Phase 2 (Production Ready):**
5. ✅ GWG test files — required for print industry credibility
6. ✅ Additional corpora — based on LintPDF's declared support (PDF/E, PDF/M, PDF/VT, etc.)

**Test Infrastructure:**
- Mirror all collections into `test-fixtures/` with organized subdirectories
- Create COLLECTIONS_MANIFEST.json with metadata for all integrated collections
- Implement automated sync and regression testing pipeline
- Generate HTML reports comparing Grounded findings to expected results per collection
- Track per-standard pass/fail rates and regression statistics

---

## TASK 5.2: GENERATOR COVERAGE PLAN

### Purpose

This plan specifies all major PDF generators that LintPDF must handle and documents their known quirks, malformations, and output characteristics. By building a test corpus from each generator, Grounded gains confidence in handling real-world PDFs from production environments.

**Strategic Importance:**
Real PDFs from generators are often messier and more malformed than official test suites. LintPDF must identify and report issues in PDFs from all major sources. This plan ensures comprehensive coverage and early detection of generator-specific bugs.

---

### Part A: Master List of PDF Generators

#### 1. **Adobe Creative Suite**

**Applications:**
- Adobe Illustrator (vector design)
- Adobe InDesign (desktop publishing)
- Adobe Photoshop (image editing)
- Adobe Acrobat (native PDF editing)

**Market Share:** ~40% of professional PDF creation
**Critical for:** Print workflows, professional design

**Known Quirks and Malformations:**

| Issue | Application | Impact | Severity |
|-------|-------------|--------|----------|
| Font subsetting (not full embedding) | Illustrator, InDesign | Text may not display correctly in some viewers; kern pairs lost | High |
| Fonts not embedded despite settings | InDesign, Acrobat | Requires licensed fonts on system | Critical |
| OpenType font metrics not embedded | All | Kerning, ligatures lost in PDF | High |
| Subset fonts on nested PDF import | InDesign | Fonts converted to subset even when set to "embed all" | Medium |
| Font licensing restrictions enforced | All | Some licensed fonts cannot embed | Medium |
| Partial transparency flattening artifacts | InDesign, Illustrator | White hairlines visible after flattening | Medium |
| Color space conversions not perfect | All | CMYK from RGB conversions may shift colors | Medium |
| XObject form optimization issues | All | Form XObjects may have invalid references | Low |
| Overprint mode ignored in some contexts | InDesign | White text overprint settings not honored | Low |

**Expected Test Document Spec:**

```
Required for comprehensive Adobe testing:
- Multiple fonts (OpenType, TrueType, PostScript Type 1)
- Embedded and referenced fonts
- RGB and CMYK images
- Transparent objects with overprint
- Nested PDFs with imported content
- Form XObjects
- Spot colors with overprint
- Large images (>100MB documents)
- Multiple page sizes (test page geometry)
```

---

#### 2. **Desktop Publishing Suite**

**Applications:**
- QuarkXPress (professional DTP)
- Scribus (open-source DTP)
- Affinity Publisher (modern DTP)
- Affinity Designer (design tool with PDF export)

**Market Share:** ~10% of professional PDF creation
**Critical for:** Print and publishing workflows

**Known Quirks and Malformations:**

| Issue | Application | Impact | Severity |
|-------|-------------|--------|----------|
| Embedded image format variations | All | Different compression, DPI handling | Medium |
| Missing TrimBox / BleedBox | Scribus | Print-ready PDF requires these | High |
| Color separation issues | QuarkXPress | Spot colors may not separate correctly | Medium |
| Font subsetting inconsistencies | All | Variable font embedding strategies | Medium |
| Affinity unique color space handling | Affinity Publisher | Non-standard color space usage | Low |
| Embedded preview images missing | All | Thumbnail preview not generated | Low |

**Expected Test Document Spec:**

```
Required for comprehensive DTP testing:
- Multi-page documents (20+ pages)
- Multiple master pages / templates
- Master text frames
- Anchored objects and text wrapping
- Multiple font styles (bold, italic, small caps)
- Both images and vector graphics
- Page-sized or bleed-sized graphics
- Spot color definitions
- Guides and margin information (preserved as metadata)
- Table layouts
```

---

#### 3. **Office Suite**

**Applications:**
- Microsoft Word (word processing, PDF export)
- Microsoft PowerPoint (presentations, PDF export)
- Google Docs (cloud word processing, PDF export)
- LibreOffice Writer / Calc / Impress (open-source office suite)

**Market Share:** ~30% of casual PDF creation
**Critical for:** Business documents, general use

**Known Quirks and Malformations:**

| Issue | Application | Impact | Severity |
|-------|-------------|--------|----------|
| Embedded TrueType font subsetting | Word, Google Docs | Only subset glyphs included | Medium |
| Missing text encoding info | Word | Non-ASCII text may be incorrectly extracted | Low |
| Oversized content streams | All | Large files with inefficient structure | Medium |
| Image compression not optimized | All | Uncompressed or poorly compressed images | Medium |
| Form field incompatibilities | Word | AcroForm fields may not work in all readers | Low |
| OLE embedded objects | Word | Embedded documents not readable | Medium |
| Linked images not embedded | Google Docs | References to external resources | High |
| Table structure not preserved | All | Tables may flatten to unsearchable text | Low |

**Expected Test Document Spec:**

```
Required for comprehensive Office testing:
- Mixed fonts (Arial, Calibri, Times New Roman, etc.)
- Embedded images (various DPI: 72, 96, 150, 300)
- Hyperlinks (internal and external)
- Form fields (text, checkbox, radio buttons)
- Tables with merged cells
- Headers and footers
- Page breaks and section breaks
- Lists (numbered, bulleted, multilevel)
- Text with special formatting (strikethrough, subscript, superscript)
- Color text and highlights
- Comments or annotations
```

---

#### 4. **Web/Browser PDF Generators**

**Applications:**
- Chrome / Chromium "Print to PDF"
- Firefox "Print to PDF"
- wkhtmltopdf (command-line HTML to PDF)
- WeasyPrint (Python HTML to PDF library)
- Puppeteer / Playwright (headless browser automation)

**Market Share:** ~20% of programmatically generated PDFs
**Critical for:** Report generation, documentation, web-based workflows

**Known Quirks and Malformations:**

| Issue | Application | Impact | Severity |
|-------|-------------|--------|----------|
| CSS page breaks not honored perfectly | All browsers | Unexpected content splitting | Medium |
| Font fallback issues | All browsers | Missing fonts replaced with system defaults | Medium |
| High DPI setting artifacts | Chrome | Images may be oversized or distorted | Low |
| Background colors/images not embedded | Chrome, Firefox | May not render in final output | Medium |
| Javascript not preserved | All | Interactive forms not functional | Low |
| Margin/padding calculations differ | All browsers | Spacing may vary between renderers | Low |
| SVG rendering inconsistencies | All browsers | Vector graphics may render differently | Low |
| External resource failures | wkhtmltopdf, WeasyPrint | Missing images, fonts, CSS | High |

**Expected Test Document Spec:**

```
Required for comprehensive web/browser testing:
- HTML with CSS styling (colors, fonts, backgrounds)
- Embedded images and SVG graphics
- Multi-column layouts
- CSS media queries (@media print)
- Web fonts (Google Fonts, custom fonts)
- HTML tables and lists
- Form elements
- Links (internal anchors and external URLs)
- Complex CSS layouts (grid, flexbox)
- Print-specific CSS rules
- Dark mode or custom stylesheets
```

---

#### 5. **Design Tools**

**Applications:**
- Canva (cloud design tool)
- Figma (cloud design collaboration)
- Sketch (macOS design tool)

**Market Share:** ~5% of professional design PDFs
**Critical for:** Modern design workflows, collaborative design

**Known Quirks and Malformations:**

| Issue | Application | Impact | Severity |
|-------|-------------|--------|----------|
| Complex vector optimization | Figma, Sketch | Vector paths may be over-simplified or inflated | Medium |
| Raster export quality settings | All | Rasterization DPI may be variable | Medium |
| Font substitution on export | Figma, Canva | Design fonts may not be embedded | Medium |
| Color profile issues | All | Colors may shift in conversion | Low |
| Artboard margins and bleed | All | Page boundaries may not align correctly | Low |
| Grouped object flattening | All | Vector groups may be rasterized | Medium |

**Expected Test Document Spec:**

```
Required for comprehensive design tool testing:
- Complex vector shapes (paths, bezier curves)
- Rasterized layers within vector documents
- Multiple artboards (multi-page documents)
- Text with design-specific fonts
- Effects (shadows, blurs, gradients)
- Grouped and nested objects
- Symbol/component references
- Custom color palettes (spot colors)
- Blending modes and opacity
```

---

#### 6. **Technical Document Generators**

**Applications:**
- LaTeX (TeX Live, MiKTeX)
- Pandoc (document converter)
- Sphinx (Python documentation generator)
- Doxygen (source code documentation)

**Market Share:** ~10% of technical documentation
**Critical for:** Academic papers, technical documentation, API docs

**Known Quirks and Malformations:**

| Issue | Application | Impact | Severity |
|-------|-------------|--------|----------|
| LaTeX font encoding issues | LaTeX | Type 1 fonts may have unusual encodings | Medium |
| Missing ImageMagick processing | Pandoc | Vector-to-raster conversion may fail | Low |
| Very large files (100+ pages) | All | Memory and processing issues | Medium |
| Embedded hyperlinks and bookmarks | LaTeX, Pandoc | TOC and cross-references functional | Low |
| Complex mathematical notation | LaTeX | May use custom fonts or XObjects | Low |

**Expected Test Document Spec:**

```
Required for comprehensive technical doc testing:
- Computer Modern and TeX fonts
- Mathematical notation and equations
- Code listings with syntax highlighting
- Bibliography with embedded metadata
- Cross-references and internal links
- Table of contents / bookmarks
- Multiple pages (50+ pages for stress testing)
- Bibliography references
- Figure captions and labels
- Index with special sorting
```

---

#### 7. **Programming Libraries**

**Applications:**
- ReportLab (Python PDF library)
- FPDF / FPDF2 (PHP PDF library)
- iText (Java/C# PDF library)
- PDFKit (Node.js PDF library)
- PyPDF (Python PDF manipulation)
- pdfgen (Go PDF library)

**Market Share:** ~15% (often server-side generation)
**Critical for:** Programmatically generated reports, invoices, certificates

**Known Quirks and Malformations:**

| Issue | Application | Impact | Severity |
|-------|-------------|--------|----------|
| Font embedding strategy varies | All libraries | Different approaches to subsetting | Medium |
| Color space handling differences | iText, ReportLab | RGB vs. CMYK conversions differ | Medium |
| Image DPI not always set | All libraries | Image resolution may be unclear | Medium |
| Form field implementation varies | iText, PDFKit | Field properties may differ | Low |
| Stream compression not always used | FPDF | Files may be larger than necessary | Low |

**Expected Test Document Spec:**

```
Required for comprehensive library testing:
- Tables with cell borders and shading
- Images in various formats (JPEG, PNG, GIF)
- Form fields (if library supports them)
- Barcodes (1D and 2D)
- Multiple pages with page numbering
- Headers and footers
- Simple and complex layouts
- Mixed fonts and styles
- Color output
```

---

#### 8. **macOS-Specific Generators**

**Applications:**
- macOS Preview (built-in PDF viewer/editor)
- Quartz PDFContext (system-level PDF rendering)
- macOS Print to PDF (system dialog)

**Market Share:** ~5% (macOS users)
**Critical for:** Cross-platform support

**Known Quirks and Malformations:**

| Issue | Application | Impact | Severity |
|-------|-------------|--------|----------|
| Font rendering differences | Preview, Quartz | Fonts may render differently than on other OS | Low |
| Color profile assumptions | Quartz | May assume Display RGB or sRGB | Low |
| PDF Security (user/owner passwords) | Preview | Encryption options limited | Low |

**Expected Test Document Spec:**

```
Required for comprehensive macOS testing:
- System fonts (Helvetica, Courier, Times Roman)
- English and non-English text
- Common print-to-PDF scenarios
- System color management (ColorSync)
```

---

### Part B: Standardized Test Document Specification

**Objective:** Define a baseline test document that all PDF generators should create. This allows comparison across generators and identification of generator-specific issues.

#### Core Test Document Properties

**Document Specifications:**

```json
{
  "document_metadata": {
    "title": "Grounded Generator Test Document",
    "author": "Grounded Test Suite",
    "subject": "Comprehensive PDF generator validation",
    "creator_application": "[Generator Name]",
    "producer": "[Generator Name]",
    "creation_date": "YYYY-MM-DD",
    "modification_date": "YYYY-MM-DD"
  },
  "page_structure": {
    "total_pages": 5,
    "page_sizes": [
      { "page": 1, "size": "A4", "width_points": 595.276, "height_points": 841.890 },
      { "page": 2, "size": "Letter", "width_points": 612, "height_points": 792 },
      { "page": 3, "size": "A4", "width_points": 595.276, "height_points": 841.890 },
      { "page": 4, "size": "A4", "width_points": 595.276, "height_points": 841.890 },
      { "page": 5, "size": "A4", "width_points": 595.276, "height_points": 841.890 }
    ],
    "has_bleeds": true,
    "has_trim_boxes": true,
    "has_art_boxes": false
  },
  "fonts": {
    "fonts_used": [
      {
        "name": "Helvetica",
        "type": "TrueType",
        "embedded": true,
        "subset": true,
        "encoding": "WinAnsiEncoding"
      },
      {
        "name": "Times-Roman",
        "type": "Type1",
        "embedded": true,
        "subset": false,
        "encoding": "StandardEncoding"
      },
      {
        "name": "Courier",
        "type": "TrueType",
        "embedded": false,
        "subset": false,
        "encoding": "WinAnsiEncoding"
      }
    ]
  },
  "colors": {
    "color_spaces": [
      "DeviceGray",
      "DeviceRGB",
      "DeviceCMYK"
    ],
    "spot_colors": [
      {
        "name": "Pantone 200 C",
        "colorant_type": "Cyan",
        "alternate": [0, 0.8, 0.7, 0.15]
      },
      {
        "name": "Pantone 288 C",
        "colorant_type": "Yellow",
        "alternate": [0, 0.15, 1.0, 0.1]
      }
    ]
  },
  "images": {
    "images_by_dpi": {
      "72_dpi": {
        "count": 1,
        "format": "JPEG",
        "color_space": "DeviceRGB",
        "compression": "DCTDecode",
        "size_pixels": "640x480"
      },
      "150_dpi": {
        "count": 1,
        "format": "PNG",
        "color_space": "DeviceRGB",
        "compression": "FlateDecode",
        "size_pixels": "1280x960"
      },
      "300_dpi": {
        "count": 2,
        "format": "JPEG",
        "color_space": "DeviceCMYK",
        "compression": "DCTDecode",
        "size_pixels": "2400x1800"
      },
      "600_dpi": {
        "count": 1,
        "format": "TIFF",
        "color_space": "DeviceGray",
        "compression": "FlateDecode",
        "size_pixels": "4800x3600"
      }
    }
  },
  "content_features": {
    "has_transparency": true,
    "has_blend_modes": true,
    "blend_modes_used": ["Multiply", "Screen", "Overlay"],
    "has_overprint": true,
    "overprint_settings": {
      "black_text_overprint": false,
      "white_text_overprint": false,
      "spot_color_overprint": true
    },
    "has_forms": true,
    "has_annotations": true,
    "annotation_types": ["Comment", "Highlight", "Strikeout"]
  },
  "conformance": {
    "pdf_version": "1.7",
    "intended_standards": ["PDF/X-4", "PDF/A-3b"],
    "contains_encrypted_content": false,
    "contains_linearized_content": false,
    "contains_incremental_updates": false
  }
}
```

#### Per-Page Content Specifications

**Page 1: Typography and Font Testing**

```
Content:
- Heading in Helvetica Bold: "Font Embedding Test"
- Paragraph in Times-Roman: Lorem ipsum text (100+ words)
- Mixed formatting: bold, italic, underline, strikethrough
- Different font sizes: 10pt, 12pt, 14pt, 18pt, 24pt
- Different weights where available
- Special characters: accents, currency, mathematical symbols
- Embedded font test (TrueType)
- Reference font test (system font not embedded)
- SmallCaps and variant formatting

Expected Findings:
- Helvetica Bold: embedded=true, subset=true
- Times-Roman: embedded=true, subset=true or false
- Courier: embedded=false (system font)
- All glyphs should be readable
```

**Page 2: Image and Color Testing**

```
Content:
- RGB image at 72 DPI (low resolution marker)
- CMYK image at 150 DPI (medium resolution)
- Grayscale image at 300 DPI (standard print resolution)
- Black and white image at 600 DPI (high resolution)
- Images labeled with their DPI and color space
- RGB color boxes (red, green, blue)
- CMYK color boxes (cyan, magenta, yellow, key/black)
- Spot color boxes (Pantone 200 C, Pantone 288 C)
- Mixed color blending examples

Expected Findings:
- 72 DPI image: low-resolution warning
- 300 DPI CMYK images: pass
- Spot colors detected and named
- Color spaces identified correctly
```

**Page 3: Advanced Graphics and Transparency**

```
Content:
- Text with transparency (50%, 75%, 25% opacity)
- Shapes with blend modes (Multiply, Screen, Overlay)
- Spot color with transparency
- Images with transparency masks
- Transparent gradient fills
- Vector shapes with overprint enabled
- Mixed transparent and opaque content

Expected Findings:
- Transparency detected
- Blend modes identified
- Overprint settings noted
- No corruption of transparent content
```

**Page 4: Print Workflow Features**

```
Content:
- Bleed area content (content that extends to bleed)
- Trim marks (if supported by generator)
- Color registration marks
- Page dimensions info
- Bleed, trim, art, and crop boxes visualized
- Safe area markers
- CMYK color gradients
- Spot color overprint scenario

Expected Findings:
- Bleed box correctly defined
- Trim box correctly defined
- CMYK separations valid
- Overprint settings honored
```

**Page 5: Document Structure and Metadata**

```
Content:
- Bookmarks/outline structure (if supported)
- Links (internal and external)
- Form fields (text input, checkbox, radio button)
- Table of contents markers
- Metadata embedded in content
- Hyperlinks to external URLs
- Cross-references to other pages

Expected Findings:
- Metadata properly stored
- Links functional (URL preserved)
- Bookmarks present if supported
- Form fields properly defined
```

#### Expected Variations by Generator

**Table: Generator-Specific Expected Variations**

| Generator | Font Embedding | Image Compression | Spot Colors | Transparency | Quirks to Monitor |
|-----------|----------------|-------------------|-------------|--------------|------------------|
| Illustrator | Subset TrueType | DCT, FlateDecode | Full support | Flattening artifacts | Font metrics loss |
| InDesign | Subset mixed | DCT, FlateDecode | Full support | Perfect | Nested PDF issues |
| Word | Subset TrueType | Varies (often JPEG) | Limited | Basic | Missing encoding |
| Chrome | Subset TrueType | DCT optimized | Not typically | Good | CSS resolution issues |
| LaTeX | Type 1 fonts | FlateDecode | Via packages | Limited | Font encoding varies |
| ReportLab | Subset TrueType | Configurable | Via plugins | Good | Smaller files |

---

### Part C: Implementation Strategy for Generator Testing

#### Step 1: Create Test Document Sources

```
test-fixtures/generators/
├── templates/
│   ├── grounded-test-document.indd
│   ├── grounded-test-document.ai
│   ├── grounded-test-document.docx
│   ├── grounded-test-document.html
│   ├── grounded-test-document.tex
│   ├── grounded-test-document.fig
│   └── grounded-test-document-spec.json
└── README.md
```

#### Step 2: Generate PDFs from Each Generator

```
For each generator:
1. Use source file from templates/
2. Export to PDF using standard settings
3. Name output: [generator-name]_[version]_[profile].pdf
4. Example: adobe-illustrator_2024_standard.pdf
5. Store in: test-fixtures/generators/output/

Profiles to generate for each:
- default (factory defaults)
- optimized (best quality settings)
- efficient (file size optimization)
- compliance (PDF/X-4 or PDF/A-3 profile if available)
```

#### Step 3: Document Expected Findings

```
For each generator output:
- Create expected-findings.json
- Document what fonts should be embedded
- Document image resolutions and color spaces
- Document spot colors and their values
- Document overprint settings
- List any known generator-specific artifacts

File: test-fixtures/generators/output/[generator]_expected_findings.json
```

#### Step 4: Add to CI Pipeline

```yaml
# ci/test-generators.yml

test-generator-corpus:
  script:
    - for generator in generators/output/*.pdf
        do
          grounded-cli preflight "$generator" \
            --output json \
            > "$generator.findings.json"

          # Compare to expected findings
          python3 ci/compare_findings.py \
            "$generator.findings.json" \
            "$(dirname $generator)/expected_findings.json"
        done
  artifacts:
    - generator-test-report.html
```

---

### Summary: Generator Coverage Strategy

**Immediate Priority (MVP):**
1. Adobe Illustrator (latest version)
2. Microsoft Word (latest version)
3. Chrome Print-to-PDF (latest version)
4. LaTeX (TeX Live 2024+)
5. ReportLab (latest version)

**Phase 2 (Extended Coverage):**
6. Adobe InDesign
7. Google Docs
8. Figma
9. WeasyPrint
10. wkhtmltopdf

**Phase 3 (Specialized):**
11. QuarkXPress
12. Canva
13. Affinity Publisher
14. Pandoc
15. All remaining generators per demand

**Key Metrics:**
- Track pass/fail rate per generator
- Identify generator-specific bugs quickly
- Monitor for regressions across generator updates
- Report any generator producing non-conformant PDFs

---

## TASK 5.3: FAILURE MODE LIBRARY SPECIFICATION

### Purpose

This specification defines a comprehensive library of PDF preflight failures that LintPDF must detect and report. For each failure mode, we document:
- What the failure looks like in a PDF
- How to programmatically create test files that exhibit the failure
- The expected findings JSON schema for ground truth comparison
- Severity level (error vs. warning)
- The regression testing harness architecture

**Strategic Importance:**
By implementing this failure mode library, Grounded becomes a "complete" preflight validator — every known issue has a test case, and every test case has an expected output. This enables confident regression testing and easy verification of conformance.

---

### Part A: Complete Failure Mode Catalog

#### 1. **Missing Fonts (Not Embedded)**

**Description:**
A PDF references a font that is not embedded in the file. The PDF viewer will substitute with a system font, potentially causing text to reflow, display incorrectly, or become unreadable.

**Detection:**
- Font object in PDF has no embedded font program (FontFile, FontFile2, FontFile3)
- Font is referenced in content stream but no font descriptor present
- Subset indicator (subset prefix like `ABCDEF+FontName`) without actual subset

**Severity:** `ERROR` (critical for print workflows)

**How to Create Test File:**

```python
# Using pikepdf to create a font-missing test file
import pikepdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

# Approach 1: Create with ReportLab, then strip font
pdf = canvas.Canvas("/tmp/test_missing_fonts.pdf", pagesize=letter)
pdf.setFont("Helvetica", 12)
pdf.drawString(100, 750, "This text uses Helvetica")
pdf.save()

# Now use pikepdf to remove embedded font from font object
with pikepdf.open("/tmp/test_missing_fonts.pdf") as pdf:
    # Find all font objects
    for page in pdf.pages:
        if "/Font" in page.Resources:
            fonts = page.Resources.Font
            for font_name, font_obj in fonts.items():
                # Remove the embedded font program
                if "/FontFile" in font_obj:
                    del font_obj.FontFile
                if "/FontFile2" in font_obj:
                    del font_obj.FontFile2
                if "/FontFile3" in font_obj:
                    del font_obj.FontFile3

    pdf.save("/tmp/test_missing_fonts_stripped.pdf")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "missing-fonts.pdf",
  "failure_mode": "missing-fonts",
  "severity": "error",
  "findings": [
    {
      "type": "missing-font",
      "font_name": "Helvetica",
      "font_object_reference": "F1",
      "uses_in_content": 145,
      "character_count": 1250,
      "embedded": false,
      "glyph_indices": [33, 45, 67, 89],
      "message": "Font 'Helvetica' used in content but not embedded in PDF",
      "remediation": "Embed the font or use only standard 14 fonts"
    }
  ],
  "statistics": {
    "total_fonts": 3,
    "embedded_fonts": 2,
    "missing_fonts": 1,
    "affected_characters": 1250,
    "pages_affected": 1
  }
}
```

**Ground Truth Comparison:**
- LintPDF must detect the exact font name
- LintPDF must report character count affected
- LintPDF must list pages with missing font references

---

#### 2. **RGB Images in CMYK Workflow**

**Description:**
An image in RGB color space exists in a PDF that declares or expects CMYK (PDF/X-4, PDF/A-3). RGB images cannot directly separate to CMYK plates and will need conversion, potentially causing color shifts.

**Detection:**
- Image has `/ColorSpace /DeviceRGB` but document is PDF/X-1a or PDF/A-1 (which forbid RGB)
- Or detection in a print workflow context (PDF/X-4 may allow RGB with ICC profile)

**Severity:** `ERROR` (for PDF/X-1a), `WARNING` (for PDF/X-4 with profile)

**How to Create Test File:**

```python
# Create RGB image in CMYK document
import pikepdf
from PIL import Image
import io

# Create an RGB test image
img = Image.new('RGB', (100, 100), color=(255, 0, 0))
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

# Create PDF with ReportLab
from reportlab.pdfgen import canvas
pdf = canvas.Canvas("/tmp/test_rgb_image.pdf", pagesize=(612, 792))
pdf.drawString(100, 750, "RGB Image in CMYK Document")

# Draw the RGB image
pdf.drawImage(img, 100, 500, width=100, height=100)
pdf.save()

# Now use pikepdf to mark document as CMYK-only
with pikepdf.open("/tmp/test_rgb_image.pdf") as pdf:
    # Add OutputIntent to indicate CMYK workflow
    output_intent = pikepdf.Stream(pdf, """
      [ /OutputCondition (CMYK Print)
        /Info (CMYK Workflow)
        /Type /OutputIntent
        /S /GTS_PDFX
      ]
    """)

    if pdf.Root.OutputIntents:
        pdf.Root.OutputIntents.append(output_intent)
    else:
        pdf.Root.OutputIntents = [output_intent]

    pdf.save("/tmp/test_rgb_in_cmyk.pdf")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "rgb-in-cmyk.pdf",
  "failure_mode": "rgb-image-in-cmyk-workflow",
  "severity": "error",
  "findings": [
    {
      "type": "color-space-mismatch",
      "image_reference": "XObject_1",
      "image_name": "Image_001",
      "detected_color_space": "DeviceRGB",
      "expected_color_space": "DeviceCMYK",
      "document_profile": "PDF/X-1a",
      "message": "RGB image in CMYK-only PDF/X-1a document",
      "remediation": "Convert image to CMYK or change document profile to PDF/X-4"
    }
  ],
  "statistics": {
    "total_images": 1,
    "rgb_images": 1,
    "cmyk_images": 0,
    "pages_affected": 1
  }
}
```

---

#### 3. **Low-Resolution Images**

**Description:**
An image's resolution (DPI) is below the minimum required for the workflow. Typical requirements: 300 DPI for photos, 600 DPI for line art.

**Detection:**
- Calculate image DPI: `DPI = (image_width_pixels * 72) / width_in_inches`
- Compare to workflow minimums
- Flag images below threshold

**Severity:** `WARNING` (or `ERROR` if critically low, e.g., <72 DPI)

**How to Create Test File:**

```python
# Create images at specific DPI
from PIL import Image
import pikepdf
from reportlab.pdfgen import canvas

# Create low-res image (72 DPI)
img_72dpi = Image.new('RGB', (640, 480), color=(200, 100, 50))
img_72dpi.info['dpi'] = (72, 72)
img_72dpi.save("/tmp/image_72dpi.jpg")

# Create medium-res image (150 DPI)
img_150dpi = Image.new('RGB', (1280, 960), color=(100, 150, 200))
img_150dpi.info['dpi'] = (150, 150)
img_150dpi.save("/tmp/image_150dpi.jpg")

# Create high-res image (300 DPI)
img_300dpi = Image.new('RGB', (2400, 1800), color=(50, 200, 100))
img_300dpi.info['dpi'] = (300, 300)
img_300dpi.save("/tmp/image_300dpi.jpg")

# Create PDF with all three
pdf = canvas.Canvas("/tmp/test_image_resolution.pdf", pagesize=(612, 792))
pdf.drawString(100, 750, "Images at Various Resolutions")
pdf.drawImage("/tmp/image_72dpi.jpg", 100, 600, width=2)  # 2" wide
pdf.drawImage("/tmp/image_150dpi.jpg", 100, 450, width=2)
pdf.drawImage("/tmp/image_300dpi.jpg", 100, 300, width=2)
pdf.save()
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "low-resolution-images.pdf",
  "failure_mode": "low-resolution-images",
  "severity": "warning",
  "findings": [
    {
      "type": "low-resolution-image",
      "image_reference": "Image_1",
      "detected_dpi": 72,
      "min_required_dpi": 300,
      "image_dimensions_pixels": "640x480",
      "print_size_inches": "2.0x1.5",
      "color_space": "DeviceRGB",
      "message": "Image resolution 72 DPI is below 300 DPI minimum",
      "severity": "warning",
      "remediation": "Replace with higher resolution image or reduce print size"
    },
    {
      "type": "low-resolution-image",
      "image_reference": "Image_2",
      "detected_dpi": 150,
      "min_required_dpi": 300,
      "image_dimensions_pixels": "1280x960",
      "print_size_inches": "2.0x1.5",
      "color_space": "DeviceRGB",
      "message": "Image resolution 150 DPI is below 300 DPI minimum",
      "severity": "warning"
    }
  ],
  "statistics": {
    "total_images": 3,
    "images_at_min_dpi_or_above": 1,
    "images_below_min_dpi": 2,
    "pages_affected": 1
  }
}
```

---

#### 4. **Missing Bleed**

**Description:**
Content that extends to the page edge is present, but no BleedBox is defined. In print workflows, bleed area is required for safe cutting and to avoid white edges.

**Detection:**
- Content extends beyond CropBox or TrimBox
- BleedBox is missing or same as CropBox (should be larger)
- Page has no defined bleed boundary

**Severity:** `WARNING` (or `ERROR` for strict print workflows)

**How to Create Test File:**

```python
# Create PDF with content bleeding but no bleed box
import pikepdf
from reportlab.pdfgen import canvas

pdf = canvas.Canvas("/tmp/test_no_bleed.pdf", pagesize=(612, 792))

# Draw content that goes to the edge (8.5" x 11" letter)
pdf.setFillColorRGB(1, 0, 0)
pdf.rect(0, 0, 612, 792, fill=1)  # Red rectangle fills entire page

# Text on the colored background
pdf.setFont("Helvetica", 12)
pdf.setFillColorRGB(1, 1, 1)
pdf.drawString(50, 750, "Content extends to page edge - no bleed defined")

pdf.save()

# Now modify with pikepdf to remove BleedBox if present
# and ensure no bleed safety margin exists
with pikepdf.open("/tmp/test_no_bleed.pdf") as pdf_obj:
    for page in pdf_obj.pages:
        # Remove BleedBox if present
        if "/BleedBox" in page:
            del page.BleedBox

        # Ensure MediaBox and CropBox are same (no margin)
        page.CropBox = page.MediaBox

        # Ensure no TrimBox
        if "/TrimBox" in page:
            del page.TrimBox

    pdf_obj.save("/tmp/test_no_bleed_final.pdf")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "missing-bleed.pdf",
  "failure_mode": "missing-bleed",
  "severity": "warning",
  "findings": [
    {
      "type": "missing-bleed-box",
      "page": 1,
      "media_box": "[0, 0, 612, 792]",
      "crop_box": "[36, 36, 576, 756]",
      "trim_box": "[36, 36, 576, 756]",
      "bleed_box": "undefined",
      "bleed_margin_detected": false,
      "content_extends_to_edge": true,
      "message": "Content extends to page edge but BleedBox is not defined",
      "remediation": "Define BleedBox with 0.125\" (9pt) margin outside TrimBox"
    }
  ],
  "statistics": {
    "total_pages": 1,
    "pages_missing_bleed": 1,
    "pages_with_bleed": 0
  }
}
```

---

#### 5. **Wrong Page Size**

**Description:**
Page dimensions don't match expected size for the job. Common issue: Letter (8.5"x11") vs. A4 (210x297mm), or custom sizes not in specification.

**Detection:**
- Parse MediaBox, CropBox from page
- Compare to expected page size
- Flag mismatches

**Severity:** `ERROR` (for print jobs with specified size)

**How to Create Test File:**

```python
# Create PDF with wrong page size
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4

# Create two separate documents
pdf1 = canvas.Canvas("/tmp/wrong_size_letter.pdf", pagesize=letter)
pdf1.drawString(100, 750, "This is Letter size (8.5\"x11\")")
pdf1.save()

# Now edit to have mixed sizes
import pikepdf
with pikepdf.open("/tmp/wrong_size_letter.pdf") as pdf:
    # Add a second page with A4 size
    from pikepdf import Dictionary, Array

    # Page 1 stays Letter
    # Create page 2 with A4 size
    page2_contents = pikepdf.Stream(pdf, b"BT /F1 12 Tf 100 750 Td (A4 Page) Tj ET")

    page2_dict = Dictionary(
        Type=pikepdf.Name.Page,
        MediaBox=Array([0, 0, 595.276, 841.890]),  # A4 in points
        Contents=page2_contents,
        Resources=pdf.pages[0].Resources
    )

    pdf.pages.append(page2_dict)
    pdf.save("/tmp/wrong_page_size_mixed.pdf")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "wrong-page-size.pdf",
  "failure_mode": "wrong-page-size",
  "severity": "error",
  "findings": [
    {
      "page": 1,
      "media_box_points": "[0, 0, 612, 792]",
      "media_box_inches": "[0, 0, 8.5, 11.0]",
      "detected_size": "Letter (8.5\"x11\")",
      "expected_size": "A4 (210mm x 297mm)",
      "match": false,
      "message": "Page 1 is Letter size but A4 expected"
    },
    {
      "page": 2,
      "media_box_points": "[0, 0, 595.276, 841.890]",
      "media_box_inches": "[0, 0, 8.27, 11.69]",
      "detected_size": "A4 (210mm x 297mm)",
      "expected_size": "A4 (210mm x 297mm)",
      "match": true
    }
  ],
  "statistics": {
    "total_pages": 2,
    "pages_matching_spec": 1,
    "pages_mismatching_spec": 1
  }
}
```

---

#### 6. **Transparency with Spot Colors**

**Description:**
Spot color object has transparency applied. This creates undefined behavior: spot color separations may not be able to handle transparency, and the interaction is unpredictable.

**Detection:**
- Find spot color objects (ColorSpace of type Separation)
- Check for `/ca` (fill opacity) or `/CA` (stroke opacity) values < 1.0
- Check for blend mode not equal to Normal

**Severity:** `WARNING` (can cause printing issues)

**How to Create Test File:**

```python
# Create spot color with transparency
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import pikepdf

# Create base PDF
pdf = canvas.Canvas("/tmp/spot_with_transparency.pdf", pagesize=letter)
pdf.drawString(100, 750, "Spot color with transparency")
pdf.setFillColorRGB(1, 0, 0)
pdf.circle(300, 600, 50, fill=1)
pdf.save()

# Now modify to add spot color definition
with pikepdf.open("/tmp/spot_with_transparency.pdf") as pdf_obj:
    # Create color space with spot color definition
    page = pdf_obj.pages[0]

    # Add spot color to resources
    if "/ColorSpace" not in page.Resources:
        page.Resources.ColorSpace = pikepdf.Dictionary()

    # Define Separation color space
    page.Resources.ColorSpace.PMS = pikepdf.Array([
        pikepdf.Name.Separation,
        pikepdf.Name("Pantone 200 C"),
        pikepdf.Name.DeviceCMYK,
        pikepdf.Array([0, 1, 1, 0])  # CMYK alternate
    ])

    # Modify content stream to use spot color with transparency
    old_content = page.Contents.read_bytes()
    new_content = b"""
    /PMS cs
    0.5 ca
    300 600 m
    350 600 l
    350 650 l
    300 650 l
    f
    """
    page.Contents = pikepdf.Stream(pdf_obj, new_content)

    pdf_obj.save("/tmp/spot_color_transparent.pdf")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "spot-color-with-transparency.pdf",
  "failure_mode": "transparency-with-spot-colors",
  "severity": "warning",
  "findings": [
    {
      "type": "spot-color-transparency",
      "page": 1,
      "spot_color_name": "Pantone 200 C",
      "color_space": "Separation",
      "has_fill_opacity": true,
      "fill_opacity": 0.5,
      "has_stroke_opacity": false,
      "blend_mode": "Normal",
      "message": "Spot color 'Pantone 200 C' has transparency (opacity=0.5)",
      "severity": "warning",
      "remediation": "Remove transparency or convert to CMYK process colors"
    }
  ],
  "statistics": {
    "spot_colors_total": 1,
    "spot_colors_with_transparency": 1
  }
}
```

---

#### 7. **White Overprint**

**Description:**
White text or objects have overprint mode enabled. This is suspicious because white cannot be overprinted (there's nothing under it), and setting overprint on white is usually an error that will cause text to disappear.

**Detection:**
- Check text rendering mode and overprint settings
- Identify white color (RGB 1,1,1 or CMYK 0,0,0,0)
- Check for `/OP` or `/op` true in graphics state

**Severity:** `WARNING` (potential invisible text)

**How to Create Test File:**

```python
# Create white text with overprint enabled
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import pikepdf

pdf = canvas.Canvas("/tmp/white_overprint.pdf", pagesize=letter)
pdf.setFillColorRGB(1, 1, 1)  # White
pdf.drawString(100, 750, "This white text has overprint enabled - will be invisible!")
pdf.save()

# Modify to add overprint setting
with pikepdf.open("/tmp/white_overprint.pdf") as pdf_obj:
    page = pdf_obj.pages[0]

    # Modify content stream to set overprint for white text
    old_content = page.Contents.read_bytes()
    new_content = b"""
    /GS1 gs
    1 1 1 rg
    100 750 Td
    (White text) Tj
    """

    # Add graphics state with overprint
    if "/ExtGState" not in page.Resources:
        page.Resources.ExtGState = pikepdf.Dictionary()

    page.Resources.ExtGState.GS1 = pikepdf.Dictionary(
        Type=pikepdf.Name.ExtGState,
        OP=True,  # Fill overprint
        op=True,  # Stroke overprint
    )

    page.Contents = pikepdf.Stream(pdf_obj, new_content)
    pdf_obj.save("/tmp/white_overprint_final.pdf")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "white-overprint.pdf",
  "failure_mode": "white-overprint",
  "severity": "warning",
  "findings": [
    {
      "type": "white-overprint",
      "page": 1,
      "object_type": "text",
      "color": "White (1, 1, 1)",
      "overprint_enabled": true,
      "overprint_type": "fill",
      "message": "White text with overprint enabled - will be invisible on output",
      "severity": "warning",
      "remediation": "Remove overprint or change text color to non-white"
    }
  ],
  "statistics": {
    "total_objects_with_overprint": 1,
    "white_objects_with_overprint": 1
  }
}
```

---

#### 8. **Corrupt Font Programs**

**Description:**
A font is embedded in the PDF, but the font program (FontFile, FontFile2, FontFile3) is corrupted, incomplete, or invalid. This will cause rendering or subsetting issues.

**Detection:**
- Parse font program
- Check file format signature (e.g., PostScript Type 1 has `%!PS-AdobeFont`)
- Verify file is not truncated
- Check for valid tables (TrueType) or structure (Type 1)

**Severity:** `ERROR` (font rendering will fail)

**How to Create Test File:**

```python
# Create PDF with intentionally corrupted font
import pikepdf
from reportlab.pdfgen import canvas

pdf = canvas.Canvas("/tmp/corrupt_font.pdf")
pdf.drawString(100, 750, "Text with corrupt font")
pdf.save()

# Corrupt the embedded font
with pikepdf.open("/tmp/corrupt_font.pdf") as pdf_obj:
    page = pdf_obj.pages[0]

    if "/Font" in page.Resources:
        for font_name, font_obj in page.Resources.Font.items():
            if "/FontFile2" in font_obj:
                # Get the font data
                font_stream = font_obj.FontFile2

                # Truncate the font data (corrupt it)
                original_data = font_stream.read_bytes()
                corrupted_data = original_data[:len(original_data)//2]  # Cut in half

                # Replace with corrupted version
                font_obj.FontFile2 = pikepdf.Stream(pdf_obj, corrupted_data)

    pdf_obj.save("/tmp/corrupt_font_final.pdf")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "corrupt-font.pdf",
  "failure_mode": "corrupt-font-program",
  "severity": "error",
  "findings": [
    {
      "type": "corrupt-font-program",
      "font_name": "Arial",
      "font_reference": "F1",
      "font_program_type": "FontFile2 (TrueType)",
      "expected_size_bytes": 45000,
      "actual_size_bytes": 22500,
      "checksum_valid": false,
      "parse_error": "Truncated TrueType font table directory",
      "message": "Font 'Arial' program is corrupted or incomplete",
      "severity": "error",
      "remediation": "Replace with valid font or use standard fonts"
    }
  ],
  "statistics": {
    "total_fonts": 1,
    "corrupt_fonts": 1,
    "valid_fonts": 0
  }
}
```

---

#### 9. **Missing TrimBox**

**Description:**
A PDF for print production is missing the TrimBox, which defines the final cut size. This is essential for guillotine cutting and page binding.

**Detection:**
- Check if `/TrimBox` is present on page dictionary
- Verify TrimBox is within MediaBox and outside CropBox if appropriate
- TrimBox should typically be 0.125" (9 points) inside MediaBox

**Severity:** `ERROR` (for print workflows)

**How to Create Test File:**

```python
# Create PDF without TrimBox
from reportlab.pdfgen import canvas
import pikepdf

pdf = canvas.Canvas("/tmp/no_trim_box.pdf")
pdf.drawString(100, 750, "PDF without TrimBox")
pdf.save()

# Ensure no TrimBox
with pikepdf.open("/tmp/no_trim_box.pdf") as pdf_obj:
    for page in pdf_obj.pages:
        if "/TrimBox" in page:
            del page.TrimBox

    pdf_obj.save("/tmp/no_trim_box_final.pdf")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "missing-trim-box.pdf",
  "failure_mode": "missing-trim-box",
  "severity": "error",
  "findings": [
    {
      "page": 1,
      "trim_box": "undefined",
      "media_box": "[0, 0, 612, 792]",
      "crop_box": "[0, 0, 612, 792]",
      "message": "TrimBox is not defined (required for print production)",
      "severity": "error",
      "remediation": "Define TrimBox to 0.125\" inside MediaBox (e.g., [9, 9, 603, 783] for 8.5\"x11\")"
    }
  ],
  "statistics": {
    "pages_with_trim_box": 0,
    "pages_without_trim_box": 1
  }
}
```

---

#### 10. **Mixed Page Sizes**

**Description:**
A PDF document has pages of different sizes. This is problematic for printing, binding, or processing, where all pages should be uniform.

**Detection:**
- Iterate through all pages
- Extract MediaBox (or CropBox if applicable)
- Compare dimensions
- Flag any pages that differ from the first page

**Severity:** `WARNING` (or `ERROR` for binding jobs)

**How to Create Test File:**

```python
# Create multi-page PDF with mixed sizes
import pikepdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4

# Create first page (Letter)
pdf1 = canvas.Canvas("/tmp/page1.pdf", pagesize=letter)
pdf1.drawString(100, 750, "Page 1 - Letter size")
pdf1.save()

# Create second page (A4)
pdf2 = canvas.Canvas("/tmp/page2.pdf", pagesize=A4)
pdf2.drawString(100, 750, "Page 2 - A4 size")
pdf2.save()

# Merge with pikepdf
with pikepdf.open("/tmp/page1.pdf") as pdf1_obj:
    with pikepdf.open("/tmp/page2.pdf") as pdf2_obj:
        pdf1_obj.pages.extend(pdf2_obj.pages)
        pdf1_obj.save("/tmp/mixed_page_sizes.pdf")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "mixed-page-sizes.pdf",
  "failure_mode": "mixed-page-sizes",
  "severity": "warning",
  "findings": [
    {
      "type": "page-size-mismatch",
      "first_page_size": "Letter (8.5\" x 11\") [612 x 792 points]",
      "mismatched_pages": [
        {
          "page": 2,
          "size": "A4 (210mm x 297mm) [595.276 x 841.890 points]",
          "differs_from_first": true
        }
      ],
      "message": "Document has mixed page sizes: Letter and A4",
      "severity": "warning"
    }
  ],
  "statistics": {
    "total_pages": 2,
    "unique_sizes": 2,
    "most_common_size": "Letter (1 page)",
    "pages_matching_most_common": 1,
    "pages_with_different_size": 1
  }
}
```

---

#### 11. **Very Large Files**

**Description:**
PDF file is exceptionally large (>100MB) or has very many pages (>1000). This can cause performance issues, memory problems, and processing delays.

**Detection:**
- Check file size
- Count pages
- Flag if size > 100MB or pages > 1000

**Severity:** `INFO` or `WARNING` (informational, possibly problematic)

**How to Create Test File:**

```python
# Create large PDF with many pages
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

# Create a large PDF (1000+ pages)
pdf = canvas.Canvas("/tmp/large_pdf_1000pages.pdf", pagesize=letter)

for page_num in range(1001):
    pdf.drawString(100, 750, f"Page {page_num + 1}")
    # Add large image to bloat file
    # (in real scenario, would add actual large images)
    pdf.showPage()

pdf.save()

# Check file size
file_size_mb = os.path.getsize("/tmp/large_pdf_1000pages.pdf") / (1024 * 1024)
print(f"File size: {file_size_mb:.2f} MB")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "very-large-file.pdf",
  "failure_mode": "very-large-file",
  "severity": "info",
  "findings": [
    {
      "type": "large-file",
      "file_size_bytes": 250000000,
      "file_size_mb": 238.42,
      "file_size_gb": 0.23,
      "page_count": 1050,
      "average_page_size_kb": 227,
      "message": "PDF is very large (238 MB, 1050 pages)",
      "severity": "info",
      "recommendations": [
        "Consider splitting into multiple files",
        "Review image compression settings",
        "Check for large embedded content"
      ]
    }
  ],
  "statistics": {
    "exceeds_100mb": true,
    "exceeds_1000_pages": true,
    "recommended_action": "split_or_optimize"
  }
}
```

---

#### 12. **Encrypted Files**

**Description:**
PDF contains encryption (user password, owner password, or both). Different encryption levels have different impacts on viewing and editing.

**Detection:**
- Check for `/Encrypt` dictionary in PDF catalog
- Determine encryption algorithm (RC4, AES)
- Determine encryption level (40-bit, 128-bit, 256-bit)
- Check if permissions allow extraction, copying, printing

**Severity:** `INFO` (informational, may block processing)

**How to Create Test File:**

```python
# Create encrypted PDF
import pikepdf

# Start with a regular PDF
from reportlab.pdfgen import canvas
pdf = canvas.Canvas("/tmp/encrypted_base.pdf")
pdf.drawString(100, 750, "This PDF will be encrypted")
pdf.save()

# Apply encryption
with pikepdf.open("/tmp/encrypted_base.pdf") as pdf_obj:
    # Encrypt with owner password
    pdf_obj.save(
        "/tmp/encrypted_owner_password.pdf",
        encryption=pikepdf.Encryption(
            owner="mysecretpassword",
            permissions=pikepdf.Encryption.allow.none  # No permissions
        )
    )

# Also create with user password (allows viewing but not editing)
with pikepdf.open("/tmp/encrypted_base.pdf") as pdf_obj:
    pdf_obj.save(
        "/tmp/encrypted_user_password.pdf",
        encryption=pikepdf.Encryption(
            user="viewerpassword",
            owner="editorpassword",
            permissions=pikepdf.Encryption.allow.print  # Allow printing only
        )
    )
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "encrypted-file.pdf",
  "failure_mode": "encrypted-file",
  "severity": "info",
  "findings": [
    {
      "type": "encrypted-file",
      "encryption_type": "Standard",
      "encryption_algorithm": "RC4",
      "encryption_level": "128-bit",
      "user_password_set": false,
      "owner_password_set": true,
      "permissions": {
        "print": false,
        "modify_contents": false,
        "copy_text": false,
        "add_annotations": false,
        "fill_forms": false,
        "extract_text": false
      },
      "message": "PDF is encrypted with owner password; restrictions prevent all operations",
      "severity": "info"
    }
  ],
  "statistics": {
    "encrypted": true,
    "encryption_prevents_processing": true
  }
}
```

---

#### 13. **Linearized Files**

**Description:**
PDF is linearized (web-optimized), meaning it can display the first page before the entire file is downloaded. This is optimized for streaming but may affect processing.

**Detection:**
- Check for `/Linearized` entry in document catalog
- Presence of linearization dictionary and hint streams

**Severity:** `INFO` (informational)

**How to Create Test File:**

```python
# Create linearized PDF
import pikepdf
from reportlab.pdfgen import canvas

pdf = canvas.Canvas("/tmp/linearized_base.pdf")
for i in range(5):
    pdf.drawString(100, 750 - i*50, f"Page {i+1}")
    pdf.showPage()
pdf.save()

# Linearize it
with pikepdf.open("/tmp/linearized_base.pdf") as pdf_obj:
    pdf_obj.save("/tmp/linearized.pdf", linearize=True)
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "linearized.pdf",
  "failure_mode": "linearized-file",
  "severity": "info",
  "findings": [
    {
      "type": "linearized",
      "linearized": true,
      "linearization_version": 1,
      "has_hint_stream": true,
      "message": "PDF is linearized for web/streaming optimization",
      "severity": "info"
    }
  ],
  "statistics": {
    "linearized": true
  }
}
```

---

#### 14. **Incremental Update Files**

**Description:**
PDF contains incremental updates (multiple save cycles). The file may contain multiple versions of objects, outdated annotations, or conflicting states.

**Detection:**
- Check for multiple `xref` sections
- Presence of multiple trailers
- Incremental update indicators

**Severity:** `WARNING` (may indicate document tampering or corruption)

**How to Create Test File:**

```python
# Create PDF with incremental updates
import pikepdf

# Create base PDF
from reportlab.pdfgen import canvas
pdf = canvas.Canvas("/tmp/incremental_base.pdf")
pdf.drawString(100, 750, "Original content")
pdf.save()

# Open and add annotation (creates incremental update)
with pikepdf.open("/tmp/incremental_base.pdf", allow_overwriting_input=True) as pdf_obj:
    # Add annotation
    pdf_obj.pages[0].Annots = pikepdf.Array([
        pikepdf.Dictionary(
            Type=pikepdf.Name.Annot,
            Subtype=pikepdf.Name.Text,
            Contents="Added comment",
            Rect=[100, 100, 200, 120],
        )
    ])
    # This saves as incremental update
    pdf_obj.save(incremental=True)
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "incremental-updates.pdf",
  "failure_mode": "incremental-updates",
  "severity": "warning",
  "findings": [
    {
      "type": "incremental-updates",
      "has_incremental_updates": true,
      "update_count": 2,
      "updates": [
        {
          "update_number": 1,
          "offset": 0,
          "objects_modified": 5
        },
        {
          "update_number": 2,
          "offset": 145230,
          "objects_modified": 3
        }
      ],
      "message": "PDF contains 2 incremental update sections (file was modified after creation)",
      "severity": "warning",
      "recommendations": [
        "Consider flattening to single version",
        "Verify document integrity"
      ]
    }
  ],
  "statistics": {
    "has_incremental_updates": true,
    "total_updates": 2
  }
}
```

---

#### 15. **Missing OutputIntent**

**Description:**
PDF intends to be PDF/X compliant but lacks an OutputIntent dictionary. OutputIntent declares the intended print condition (CMYK, spot colors, color management).

**Detection:**
- Check if `/OutputIntents` array exists in document catalog
- If PDF/X expected, OutputIntent is mandatory
- Verify OutputIntent is not empty

**Severity:** `ERROR` (for PDF/X, breaks conformance)

**How to Create Test File:**

```python
# Create PDF/X intended but without OutputIntent
from reportlab.pdfgen import canvas
import pikepdf

pdf = canvas.Canvas("/tmp/no_output_intent.pdf")
pdf.drawString(100, 750, "PDF/X intended but no OutputIntent")
pdf.setFillColorCMYK(0, 1, 1, 0)  # Red in CMYK
pdf.rect(100, 600, 100, 100, fill=1)
pdf.save()

# Mark as PDF/X but keep no OutputIntent
with pikepdf.open("/tmp/no_output_intent.pdf") as pdf_obj:
    # Ensure no OutputIntents
    if "/OutputIntents" in pdf_obj.Root:
        del pdf_obj.Root.OutputIntents

    # Set PDF version to 1.4 (PDF/X supported)
    pdf_obj.Root.Pages.Metadata = pikepdf.Dictionary(
        Type=pikepdf.Name.Metadata,
        Subtype=pikepdf.Name.XML,
    )

    pdf_obj.save("/tmp/no_output_intent_final.pdf")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "missing-output-intent.pdf",
  "failure_mode": "missing-output-intent",
  "severity": "error",
  "findings": [
    {
      "type": "missing-output-intent",
      "pdf_version": "1.4",
      "uses_cmyk_colors": true,
      "uses_spot_colors": false,
      "output_intent_present": false,
      "message": "PDF declares CMYK usage but OutputIntent is missing (required for PDF/X)",
      "severity": "error",
      "remediation": "Add OutputIntent dictionary specifying print condition (e.g., GTS_PDFX)"
    }
  ],
  "statistics": {
    "output_intents": 0
  }
}
```

---

#### 16. **Invalid ICC Profile**

**Description:**
PDF contains an ICC profile for color management, but the profile is corrupted, truncated, or invalid.

**Detection:**
- Parse ICC profile header
- Verify version signature
- Check file size matches declared size
- Validate color space and profile classes

**Severity:** `WARNING` (color management may fail)

**How to Create Test File:**

```python
# Create PDF with invalid ICC profile
import pikepdf

from reportlab.pdfgen import canvas
pdf = canvas.Canvas("/tmp/invalid_icc.pdf")
pdf.drawString(100, 750, "PDF with invalid ICC profile")
pdf.save()

# Add corrupted ICC profile
with pikepdf.open("/tmp/invalid_icc.pdf") as pdf_obj:
    # Create a truncated ICC profile (invalid)
    icc_data = b"Invalid ICC profile data..." * 10  # Too short, wrong format

    icc_stream = pikepdf.Stream(pdf_obj, icc_data)

    # Create color space with invalid ICC profile
    color_space = pikepdf.Array([
        pikepdf.Name.ICCBased,
        icc_stream
    ])

    # Add to page resources
    if "/ColorSpace" not in pdf_obj.pages[0].Resources:
        pdf_obj.pages[0].Resources.ColorSpace = pikepdf.Dictionary()

    pdf_obj.pages[0].Resources.ColorSpace.DefaultRGB = color_space
    pdf_obj.save("/tmp/invalid_icc_final.pdf")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "invalid-icc-profile.pdf",
  "failure_mode": "invalid-icc-profile",
  "severity": "warning",
  "findings": [
    {
      "type": "invalid-icc-profile",
      "profile_name": "DefaultRGB",
      "profile_size_bytes": 280,
      "expected_size_bytes": 560,
      "signature_valid": false,
      "version_valid": false,
      "color_space_valid": false,
      "parse_error": "Truncated ICC profile header",
      "message": "ICC profile is invalid or corrupted",
      "severity": "warning",
      "remediation": "Replace with valid ICC profile or remove ICC color management"
    }
  ],
  "statistics": {
    "icc_profiles": 1,
    "valid_profiles": 0,
    "invalid_profiles": 1
  }
}
```

---

#### 17. **Overprint Mode Issues**

**Description:**
Overprint settings are inconsistent or problematic. Examples: spot color overprint without proper knockout settings, or black text not set to overprint in CMYK environments.

**Detection:**
- Check `/OP` (fill overprint) and `/op` (stroke overprint) flags
- Compare to object color (is it black? white? spot color?)
- Check if overprint is appropriate for the context

**Severity:** `WARNING`

**Expected Findings JSON Schema:**

```json
{
  "test_file": "overprint-issues.pdf",
  "failure_mode": "overprint-mode-issues",
  "severity": "warning",
  "findings": [
    {
      "type": "black-text-no-overprint",
      "page": 1,
      "object_id": "obj_15",
      "color": "Black (0, 0, 0, 1)",
      "overprint_enabled": false,
      "message": "Black text without overprint may show knockout trap or misregistration",
      "severity": "warning",
      "common_in": "CMYK print workflows"
    },
    {
      "type": "spot-color-overprint-ambiguous",
      "page": 2,
      "object_id": "obj_47",
      "spot_color": "Pantone 200 C",
      "overprint_enabled": true,
      "knockout_not_specified": true,
      "message": "Spot color overprint without explicit knockout setting",
      "severity": "warning"
    }
  ]
}
```

---

#### 18. **Low Opacity Values**

**Description:**
Objects have very low opacity values (< 10%), making them nearly invisible. This might be intentional or an error.

**Detection:**
- Check `/ca` (fill opacity) and `/CA` (stroke opacity)
- Flag values < 0.1

**Severity:** `INFO` (informational, may be intentional)

**Expected Findings JSON Schema:**

```json
{
  "test_file": "low-opacity.pdf",
  "failure_mode": "low-opacity-values",
  "severity": "info",
  "findings": [
    {
      "type": "very-low-opacity",
      "page": 1,
      "object_type": "text",
      "fill_opacity": 0.05,
      "stroke_opacity": 1.0,
      "message": "Object has very low fill opacity (5%) - may be invisible",
      "severity": "info"
    }
  ]
}
```

---

#### 19. **Non-Standard Blend Modes**

**Description:**
PDF uses blend modes beyond the standard set, or combines blend modes in unusual ways that may not be supported by all viewers/printers.

**Detection:**
- Check `/BM` (blend mode) in graphics state
- List supported modes: Normal, Multiply, Screen, Overlay, SoftLight, HardLight, etc.
- Flag non-standard modes

**Severity:** `WARNING` (may not render correctly on all platforms)

**Expected Findings JSON Schema:**

```json
{
  "test_file": "non-standard-blend-modes.pdf",
  "failure_mode": "non-standard-blend-modes",
  "severity": "warning",
  "findings": [
    {
      "type": "non-standard-blend-mode",
      "page": 1,
      "blend_mode": "CustomMultiplyAdd",
      "is_standard": false,
      "message": "Non-standard blend mode may not render correctly on all viewers",
      "severity": "warning"
    }
  ]
}
```

---

#### 20. **Type 3 Fonts**

**Description:**
PDF contains Type 3 fonts (user-defined fonts with custom drawing programs). These are problematic because they're not scalable, have poor text extraction, and limited subsetting support.

**Detection:**
- Check font dictionary `/Type` entry
- Identify Type 3 fonts (should be Type 0, Type 1, or TrueType)

**Severity:** `WARNING` (problematic for text extraction and processing)

**How to Create Test File:**

```python
# Create PDF with Type 3 font
# (Type 3 fonts are less common but can be created with low-level PDF manipulation)
import pikepdf

from reportlab.pdfgen import canvas
pdf = canvas.Canvas("/tmp/type3_font_base.pdf")
pdf.drawString(100, 750, "Test")
pdf.save()

with pikepdf.open("/tmp/type3_font_base.pdf") as pdf_obj:
    # Find font object and modify to Type 3
    page = pdf_obj.pages[0]
    if "/Font" in page.Resources:
        for font_ref in page.Resources.Font.values():
            # Change Type to Type3
            font_ref.Type = pikepdf.Name.Font
            font_ref.Subtype = pikepdf.Name.Type3
            # Add minimal Type3 font properties
            font_ref.FontBBox = pikepdf.Array([0, 0, 500, 700])
            font_ref.FontMatrix = pikepdf.Array([0.001, 0, 0, 0.001, 0, 0])
            font_ref.CharProcs = pikepdf.Dictionary()

    pdf_obj.save("/tmp/type3_font_final.pdf")
```

**Expected Findings JSON Schema:**

```json
{
  "test_file": "type3-fonts.pdf",
  "failure_mode": "type3-fonts",
  "severity": "warning",
  "findings": [
    {
      "type": "type3-font",
      "font_name": "CustomFont",
      "font_type": "Type 3",
      "pages_used": [1, 2],
      "glyph_count": 87,
      "message": "Type 3 font detected - poor text extraction and scalability",
      "severity": "warning",
      "remediation": "Replace with TrueType or OpenType font"
    }
  ],
  "statistics": {
    "total_fonts": 3,
    "type3_fonts": 1,
    "other_fonts": 2
  }
}
```

---

### Part B: Expected Findings JSON Schema (Master Definition)

**Complete Schema for All Finding Types:**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Grounded Preflight Findings",
  "description": "Complete schema for all preflight findings reported by Grounded",
  "type": "object",
  "required": ["test_file", "timestamp", "findings", "statistics", "conformance"],
  "properties": {
    "test_file": {
      "type": "string",
      "description": "Path to the PDF file analyzed"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of analysis"
    },
    "file_metadata": {
      "type": "object",
      "properties": {
        "file_size_bytes": { "type": "integer" },
        "file_size_mb": { "type": "number" },
        "pdf_version": { "type": "string" },
        "producer": { "type": "string" },
        "creator": { "type": "string" },
        "title": { "type": "string" },
        "author": { "type": "string" },
        "subject": { "type": "string" }
      }
    },
    "findings": {
      "type": "array",
      "description": "Array of detected issues",
      "items": {
        "type": "object",
        "required": ["type", "severity", "message"],
        "properties": {
          "type": {
            "type": "string",
            "enum": [
              "missing-font",
              "color-space-mismatch",
              "low-resolution-image",
              "missing-bleed-box",
              "wrong-page-size",
              "spot-color-transparency",
              "white-overprint",
              "corrupt-font-program",
              "missing-trim-box",
              "page-size-mismatch",
              "large-file",
              "encrypted-file",
              "linearized",
              "incremental-updates",
              "missing-output-intent",
              "invalid-icc-profile",
              "overprint-mode-issue",
              "low-opacity",
              "non-standard-blend-mode",
              "type3-font"
            ]
          },
          "severity": {
            "type": "string",
            "enum": ["error", "warning", "info"]
          },
          "message": { "type": "string" },
          "page": { "type": "integer" },
          "object_id": { "type": "string" },
          "remediation": { "type": "string" }
        }
      }
    },
    "statistics": {
      "type": "object",
      "properties": {
        "total_pages": { "type": "integer" },
        "total_fonts": { "type": "integer" },
        "total_images": { "type": "integer" },
        "total_objects": { "type": "integer" },
        "total_findings": { "type": "integer" },
        "error_count": { "type": "integer" },
        "warning_count": { "type": "integer" },
        "info_count": { "type": "integer" }
      }
    },
    "conformance": {
      "type": "object",
      "properties": {
        "declared_standards": {
          "type": "array",
          "items": { "type": "string" }
        },
        "passes_standards": {
          "type": "object",
          "additionalProperties": { "type": "boolean" }
        }
      }
    }
  }
}
```

---

### Part C: Regression Test Harness Architecture

#### Architecture Overview

```
grounded-test-harness/
├── harness.py                      # Main test runner
├── runner/
│   ├── __init__.py
│   ├── test_runner.py              # Runs Grounded against test files
│   ├── findings_comparator.py       # Compares actual vs expected findings
│   └── report_generator.py          # Generates HTML/JSON reports
├── fixtures/
│   ├── failure-modes/              # Test files for each failure mode
│   │   ├── missing-fonts/
│   │   ├── rgb-images/
│   │   ├── low-resolution/
│   │   └── ...
│   └── expected/                   # Expected findings JSON files
│       ├── missing-fonts.json
│       ├── rgb-images.json
│       └── ...
├── ci/
│   ├── run_tests.sh                # CI entry point
│   ├── test_config.yaml            # Test configuration
│   └── report.html.template        # HTML report template
└── results/
    ├── findings/                   # Actual findings from latest run
    ├── diffs/                      # Comparison diffs
    └── reports/                    # Generated reports
```

#### Test Harness Algorithm

```python
# pseudocode for regression test harness

class RegressionTestHarness:
    def __init__(self):
        self.test_files = {}        # {test_name: pdf_path}
        self.expected_findings = {} # {test_name: expected.json}
        self.actual_findings = {}   # {test_name: actual.json}
        self.results = {}           # {test_name: pass/fail/details}

    def discover_tests(self):
        """Find all test files and expected findings"""
        for mode_dir in fixtures/failure-modes/:
            test_file = find_pdf_in(mode_dir)
            expected_file = find_expected_json_in(mode_dir)

            test_name = mode_dir.name
            self.test_files[test_name] = test_file
            self.expected_findings[test_name] = load_json(expected_file)

    def run_tests(self):
        """Run Grounded against all test files"""
        for test_name, test_file in self.test_files.items():
            findings = run_grounded_cli(test_file, output_format="json")
            self.actual_findings[test_name] = findings

    def compare_findings(self):
        """Compare actual to expected findings"""
        for test_name in self.test_files:
            expected = self.expected_findings[test_name]
            actual = self.actual_findings[test_name]

            comparison = FindingsComparator.compare(expected, actual)
            self.results[test_name] = comparison

    def generate_report(self):
        """Create HTML/JSON report"""
        summary = {
            "total_tests": len(self.results),
            "passed": count_passed(self.results),
            "failed": count_failed(self.results),
            "regressions": find_regressions(self.results),
            "new_detections": find_new_detections(self.results),
            "details": self.results
        }

        write_json_report(summary, "results/report.json")
        write_html_report(summary, "results/report.html")

    def run(self):
        """Execute full test cycle"""
        self.discover_tests()
        self.run_tests()
        self.compare_findings()
        self.generate_report()
        return self.results
```

#### Comparison Logic

```python
class FindingsComparator:
    @staticmethod
    def compare(expected, actual):
        """
        Compare expected vs actual findings

        Returns:
            {
                "status": "pass" | "fail" | "partial",
                "expected_count": int,
                "actual_count": int,
                "missing_findings": [...],
                "extra_findings": [...],
                "mismatched_severity": [...],
                "details": {...}
            }
        """

        # Normalize finding types for comparison
        expected_set = normalize_findings(expected["findings"])
        actual_set = normalize_findings(actual["findings"])

        # Compare sets
        missing = expected_set - actual_set
        extra = actual_set - expected_set

        # Determine pass/fail
        if len(missing) == 0 and len(extra) == 0:
            status = "pass"
        elif len(missing) == 0:
            # Extra findings is OK (better to over-report than under-report)
            status = "pass"
        else:
            # Missing findings is a failure (false negative)
            status = "fail"

        return {
            "status": status,
            "expected_count": len(expected_set),
            "actual_count": len(actual_set),
            "missing_findings": list(missing),
            "extra_findings": list(extra),
            "severity_match": check_severity_levels(expected, actual)
        }
```

#### CI Integration

```yaml
# .gitlab-ci.yml or .github/workflows/test.yml

regression-test:
  stage: test
  image: python:3.11

  script:
    # Install Grounded CLI
    - pip install -e .

    # Run test harness
    - cd tests/regression
    - python3 harness.py --config test_config.yaml

    # Check results
    - python3 check_results.py results/report.json

  artifacts:
    paths:
      - tests/regression/results/
    reports:
      junit: tests/regression/results/junit.xml
    when: always

  allow_failure: false
```

#### HTML Report Template

```html
<!DOCTYPE html>
<html>
<head>
    <title>Grounded Regression Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .pass { background-color: #90EE90; }
        .fail { background-color: #FFB6C6; }
        .partial { background-color: #FFD700; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #DDD; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .summary { margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Grounded Regression Test Report</h1>

    <div class="summary">
        <h2>Summary</h2>
        <p>Total Tests: <strong>{{ total_tests }}</strong></p>
        <p>Passed: <strong style="color: green;">{{ passed }}</strong></p>
        <p>Failed: <strong style="color: red;">{{ failed }}</strong></p>
        <p>Pass Rate: <strong>{{ pass_rate }}%</strong></p>
    </div>

    <h2>Detailed Results</h2>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Status</th>
            <th>Expected Findings</th>
            <th>Actual Findings</th>
            <th>Missing</th>
            <th>Extra</th>
            <th>Details</th>
        </tr>
        {% for test in results %}
        <tr class="{{ test.status }}">
            <td>{{ test.name }}</td>
            <td>{{ test.status }}</td>
            <td>{{ test.expected_count }}</td>
            <td>{{ test.actual_count }}</td>
            <td>{{ test.missing_count }}</td>
            <td>{{ test.extra_count }}</td>
            <td><a href="#{{ test.name }}">View</a></td>
        </tr>
        {% endfor %}
    </table>

    <h2>Failure Details</h2>
    {% for test in failed_tests %}
    <h3 id="{{ test.name }}">{{ test.name }}</h3>
    <p><strong>Status:</strong> {{ test.status }}</p>

    {% if test.missing_findings %}
    <h4>Missing Findings (False Negatives)</h4>
    <ul>
        {% for finding in test.missing_findings %}
        <li>{{ finding.type }}: {{ finding.message }}</li>
        {% endfor %}
    </ul>
    {% endif %}

    {% if test.extra_findings %}
    <h4>Extra Findings</h4>
    <ul>
        {% for finding in test.extra_findings %}
        <li>{{ finding.type }}: {{ finding.message }}</li>
        {% endfor %}
    </ul>
    {% endif %}
    {% endfor %}

    <footer>
        <p>Report generated: {{ timestamp }}</p>
        <p>Grounded Version: {{ grounded_version }}</p>
    </footer>
</body>
</html>
```

#### Running the Harness

```bash
# Run all tests
python3 harness.py

# Run specific failure mode tests
python3 harness.py --tests missing-fonts,rgb-images

# Run with detailed output
python3 harness.py --verbose

# Generate only HTML report
python3 harness.py --report-only

# Compare against baseline
python3 harness.py --baseline results/baseline.json --show-regressions
```

---

### Summary: Failure Mode Library and Test Harness

**Complete Coverage:**
This specification documents 20 distinct failure modes, each with:
- ✅ Clear description and detection method
- ✅ Code examples for creating test files (using pikepdf, ReportLab, etc.)
- ✅ Expected findings JSON schema
- ✅ Severity classification (error/warning/info)
- ✅ Remediation guidance

**Test Harness Capabilities:**
- Automated test discovery and execution
- Comprehensive findings comparison (expected vs. actual)
- False negative detection (critical for regression)
- HTML and JSON reporting
- CI/CD integration ready
- Baseline tracking for regression analysis
- Per-failure-mode metrics and trends

**Integration Points:**
1. `grounded-cli preflight <file> --output json` — produces findings
2. Harness compares findings to expected JSON
3. CI/CD runs harness on every commit
4. Reports highlight any regressions or new detections
5. Developers can add new test files + expected JSON for new failure modes

---

## INTEGRATION ROADMAP

### Phase 5.1: Standards Integration (Week 1-2)
- [ ] Mirror veraPDF corpus to test-fixtures/
- [ ] Download and organize Isartor suite
- [ ] Download and organize Bavaria suite
- [ ] Create COLLECTIONS_MANIFEST.json
- [ ] Implement basic CI regression runner

### Phase 5.2: Generator Testing (Week 3-4)
- [ ] Generate PDFs from all major generators
- [ ] Document expected findings per generator
- [ ] Add generator corpus to test fixtures
- [ ] Track findings per generator profile

### Phase 5.3: Failure Mode Library (Week 5-6)
- [ ] Create test files for all 20 failure modes
- [ ] Validate expected findings JSON
- [ ] Implement full regression test harness
- [ ] Generate baseline report

### Phase 5.4: CI/CD Pipeline (Week 7-8)
- [ ] Integrate harness into CI pipeline
- [ ] Configure automated nightly runs
- [ ] Set up baseline tracking and regression alerts
- [ ] Create HTML reports dashboard

---

## CONCLUSION

This three-part planning document specifies:

1. **TASK 5.1** — All industry-standard test suites Grounded should integrate (5,000+ atomic test files)
2. **TASK 5.2** — Comprehensive coverage of PDF generators with known quirks and expected outputs
3. **TASK 5.3** — Complete failure mode library with test file creation code and regression harness architecture

Together, these deliverables provide the foundation for a robust, regression-tested PDF preflight engine that can confidently report on a comprehensive set of PDF quality issues.

---

**Document End**

