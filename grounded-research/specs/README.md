# PDF/UA Specifications Extraction - Preflight Analysis

## Project Overview

This directory contains comprehensive analysis of PDF/UA (PDF/Universal Accessibility) specifications and related technical standards, extracted specifically for preflight validation engine implementation.

## Generated Output

**Main Report:** `pdfua-and-supplements.md` (1,130 lines)

This consolidated report contains:

- **13 source documents analyzed** from ISO/IEC and PDF Association standards
- **117 must-have requirements** extracted for PDF/UA conformance
- **47 prohibited features** that must not appear in conforming files
- **79 recommended features** for best practices
- **53 tag-specific requirements** for logical structure validation
- **19 metadata-specific requirements** for document metadata validation
- **20 validation rules** for preflight engines

## Source Documents

### Core PDF/UA Standards

1. **ISO 14289-1:2014** - PDF/UA-1: Universal Accessibility
   - Foundation specification for PDF accessibility
   - Based on ISO 32000-1 (PDF 1.7)
   - 25 pages

2. **ISO 14289-2:2024** - PDF/UA-2: Universal Accessibility
   - Extended specification for PDF accessibility
   - Based on ISO 32000-2 (PDF 2.0)
   - 51 pages

### Technical Supplements

3. **ISO TS 32001:2022** - PDF/UA Reference Implementation: Logical Structure
   - Reference implementation guidance
   - 13 pages

4. **ISO TS 32002:2022** - PDF/UA Reference Implementation: Artifacts & Role Mapping
   - Artifact specification and role mapping rules
   - 13 pages

5. **ISO TS 32003:2023** - PDF/UA Reference Implementation: Marked Content
   - Marked content handling specifications
   - 13 pages

6. **ISO TS 32004:2024** - PDF/UA Reference Implementation: Conformance & Testing
   - Conformance testing procedures
   - 25 pages

7. **ISO TS 32005:2023** - Structure Namespace and Role Mapping
   - PDF structure namespace specifications
   - Role mapping framework
   - 49 pages

### Best Practices and Annexes

8. **Well-Tagged PDF (WTPDF) 1.0**
   - Specification for well-tagged PDFs
   - 57 pages

9. **Tagged PDF Best Practice Guide**
   - Industry best practices for tagged PDFs
   - 72 pages

10. **PDF Declarations**
    - PDF metadata declaration specifications
    - 10 pages

11. **PDF 2.0 Annex 1** - Best Practice Contents
    - 5 pages

12. **PDF 2.0 Annex 2** - Associated Files
    - 14 pages

13. **PDF 2.0 Annex 3** - Object Metadata Locations
    - 10 pages

**Total Pages Analyzed:** 347 pages

## Requirements Categorization

### Must-Have (Critical)
Requirements that MUST be satisfied for PDF/UA conformance:
- File identification and version declarations
- Logical structure tree requirements
- Tag conformance rules
- Metadata requirements
- Role mapping requirements

### Prohibited (Must Not)
Features and structures that MUST NOT appear:
- Untagged content (with exceptions)
- Improper form field structures
- Missing alternative text
- Unstructured text without proper tags

### Recommended (Best Practice)
Features that enhance accessibility:
- Comprehensive table structures
- Descriptive bookmarks
- Proper heading hierarchies
- Alternative descriptions
- Language declarations

### Tag Requirements
Specific logical structure rules:
- Document structure hierarchy
- Section and heading tagging
- List structures
- Table structure requirements
- Form field organization

### Metadata Requirements
Document metadata specifications:
- XMP metadata formatting
- PDF declaration requirements
- Language specification
- Author information
- Creation date handling

### Validation Rules
Concrete checks for automated validation:
- Presence verification
- Format compliance
- Structure validation
- Relationship verification
- Reference integrity

## Implementation Guide

### For Preflight Engine Developers

The extracted requirements provide actionable checks:

1. **Automatic Detection Rules** - Direct checks from requirement statements
2. **Conformance Level Mapping** - Requirements matched to accessibility levels
3. **Priority Hierarchy** - Requirements ordered by criticality
4. **Cross-Reference Support** - Links to source standards

### Recommended Check Sequence

1. **Pre-validation** - File format and version checks
2. **Structure Validation** - Tag tree and hierarchy verification
3. **Content Validation** - Alt text, labels, and text content checks
4. **Metadata Validation** - XMP and declaration verification
5. **Enhancement Checks** - Recommended feature presence

## Usage Notes

- Requirements are extracted from specification text
- Some requirements may have conditional applicability (noted in source)
- PDF version compatibility varies (1.4, 1.7, 2.0)
- Conformance levels (A, AA, etc.) apply to different requirements
- Role mappings are specified in ISO TS 32005:2023

## Files in This Directory

- `pdfua-and-supplements.md` - Main consolidated requirements document
- `final_extract.py` - Python script that generated the main report
- `README.md` - This file

## Analysis Methodology

Requirements were extracted using:
1. Text extraction from PDF documents (pdfplumber library)
2. Pattern matching for requirement keywords (MUST, SHALL, REQUIRED, etc.)
3. Categorization by requirement type and applicability
4. Deduplication and validation
5. Organization by standard and topic

## Key Findings

### Most Common Requirements
- PDF/UA version identification and declaration
- Logical structure tree presence and validity
- Alternative text for images and content
- Proper tag hierarchy and nesting
- Metadata and XMP compliance

### Critical Validation Areas
1. Document structure completeness
2. Tag role mapping accuracy
3. Metadata presence and format
4. Alternative text adequacy
5. Form field accessibility

### Conformance Complexity
- PDF/UA-1 has fewer requirements than PDF/UA-2
- PDF 2.0 adds extended metadata and namespace requirements
- Reference implementations provide implementation guidance
- Role mapping is critical for custom structures

## Generation Details

- **Generated:** 2026-03-11
- **Total Extraction Time:** <5 minutes
- **Extraction Method:** pdfplumber text extraction with pattern matching
- **Python Version:** 3.x
- **Output Format:** Markdown

## License

This analysis is based on ISO and PDF Association technical standards. Please refer to the original standards documents for authoritative requirements and licensing information.

---

**For questions about preflight validation requirements, refer to the consolidated report:**
`/sessions/adoring-peaceful-noether/mnt/grounded/grounded-research/specs/pdfua-and-supplements.md`
