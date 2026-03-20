#!/usr/bin/env python3
"""
Detailed extraction focusing on preflight validation rules and conformance criteria.
"""

import pdfplumber
import os
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict

DOCUMENTS = [
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO-14289-1-2014-sponsored.pdf",
        "name": "ISO 14289-1:2014",
        "title": "PDF/UA-1: Universal Accessibility",
        "description": "PDF/UA-1 specification for accessible PDFs using ISO 32000-1"
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO-14289-2-2024-sponsored.pdf",
        "name": "ISO 14289-2:2024",
        "title": "PDF/UA-2: Universal Accessibility",
        "description": "PDF/UA-2 specification for accessible PDFs using ISO 32000-2"
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO-TS-32005-2023-sponsored.pdf",
        "name": "ISO TS 32005:2023",
        "title": "Structure Namespace and Role Mapping",
        "description": "PDF structure namespace and role mapping specifications"
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO_TS_32001-2022_sponsored.pdf",
        "name": "ISO TS 32001:2022",
        "title": "PDF/UA Reference Implementation - Logical Structure",
        "description": "Reference implementation for logical structure in PDF/UA"
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO_TS_32002-2022_sponsored.pdf",
        "name": "ISO TS 32002:2022",
        "title": "PDF/UA Reference Implementation - Artifacts and Role Mapping",
        "description": "Reference implementation for artifacts and role mapping"
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO_TS_32003-2023_sponsored.pdf",
        "name": "ISO TS 32003:2023",
        "title": "PDF/UA Reference Implementation - Marked Content",
        "description": "Reference implementation for marked content"
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO-TS-32004-2024_sponsored.pdf",
        "name": "ISO TS 32004:2024",
        "title": "PDF/UA Reference Implementation - Conformance and Testing",
        "description": "Reference implementation for conformance testing"
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/Well-Tagged-PDF-WTPDF-1.0.pdf",
        "name": "WTPDF 1.0",
        "title": "Well-Tagged PDF Specification",
        "description": "Specification for well-tagged PDF documents"
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/Tagged-PDF-Best-Practice-Guide.pdf",
        "name": "Tagged PDF Best Practice Guide",
        "title": "Best Practice Guide for Tagged PDF",
        "description": "Best practices for creating tagged PDF documents"
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/PDF-Declarations.pdf",
        "name": "PDF Declarations",
        "title": "PDF Metadata Declarations",
        "description": "PDF metadata declaration specifications"
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/PDF20_AN001-BPC.pdf",
        "name": "PDF 2.0 AN001",
        "title": "Best Practice Contents",
        "description": "PDF 2.0 best practice contents annex"
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/PDF20_AN002-AF.pdf",
        "name": "PDF 2.0 AN002",
        "title": "Associated Files",
        "description": "PDF 2.0 associated files annex"
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/PDF20_AN003-ObjectMetadataLocations.pdf",
        "name": "PDF 2.0 AN003",
        "title": "Object Metadata Locations",
        "description": "PDF 2.0 object metadata locations annex"
    },
]


def extract_text_smart(pdf_path: str, max_chars: int = 50000) -> str:
    """Extract text efficiently, limiting to max characters."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text_parts = []
            total_chars = 0

            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
                    total_chars += len(extracted)
                    if total_chars > max_chars:
                        break

            return "\n".join(text_parts)
    except Exception as e:
        return ""


def categorize_requirements(text: str) -> Dict[str, List[str]]:
    """Categorize requirements by type."""
    categories = {
        "must_have": [],      # SHALL, MUST, REQUIRED
        "must_not_have": [],  # SHALL NOT, MUST NOT, PROHIBITED
        "should_have": [],    # SHOULD, RECOMMENDED
        "optional": [],       # MAY, OPTIONAL
        "validation": [],     # CHECK, VALIDATE, VERIFY
    }

    lines = text.split('\n')

    for line in lines:
        clean = line.strip()
        if not clean or len(clean) < 20 or len(clean) > 500:
            continue

        lower = clean.lower()

        # Must have
        if any(kw in lower for kw in ['shall ', 'must ', 'required', 'mandatory']):
            if 'shall not' not in lower and 'must not' not in lower:
                categories["must_have"].append(clean)

        # Must not have
        elif any(kw in lower for kw in ['shall not', 'must not', 'prohibited', 'forbidden']):
            categories["must_not_have"].append(clean)

        # Should have
        elif any(kw in lower for kw in ['should ', 'recommended']):
            categories["should_have"].append(clean)

        # Optional
        elif any(kw in lower for kw in ['may ', 'optional']):
            categories["optional"].append(clean)

        # Validation rules
        if any(kw in lower for kw in ['check ', 'validate ', 'verify ', 'test ', 'ensure ', 'confirm ']):
            categories["validation"].append(clean)

    # Remove duplicates and limit
    for key in categories:
        categories[key] = list(dict.fromkeys(categories[key]))[:20]

    return categories


def extract_conformance_criteria(text: str) -> Dict[str, any]:
    """Extract conformance-related information."""
    criteria = {
        "conformance_levels": [],
        "test_procedures": [],
        "error_conditions": [],
        "tag_requirements": [],
        "metadata_requirements": [],
    }

    lines = text.split('\n')

    for i, line in enumerate(lines):
        clean = line.strip()
        lower = clean.lower()

        # Conformance levels
        if any(word in lower for word in ['conformance', 'level a', 'level b', 'level c', 'full conformance']):
            if len(clean) < 300:
                criteria["conformance_levels"].append(clean)

        # Test procedures
        if any(word in lower for word in ['test', 'procedure', 'shall test', 'shall verify']):
            if len(clean) < 300:
                criteria["test_procedures"].append(clean)

        # Error conditions
        if any(word in lower for word in ['error', 'failure', 'violation', 'non-conforming']):
            if 'must not' in lower or 'shall not' in lower:
                if len(clean) < 300:
                    criteria["error_conditions"].append(clean)

        # Tag requirements
        if any(word in lower for word in ['tag', 'structure', 'logical structure', 'document structure']):
            if any(req in lower for req in ['must', 'shall', 'required']):
                if len(clean) < 300:
                    criteria["tag_requirements"].append(clean)

        # Metadata requirements
        if any(word in lower for word in ['metadata', 'xmp', 'catalog', 'document info']):
            if any(req in lower for req in ['must', 'shall', 'required']):
                if len(clean) < 300:
                    criteria["metadata_requirements"].append(clean)

    # Remove duplicates
    for key in criteria:
        criteria[key] = list(dict.fromkeys(criteria[key]))[:15]

    return criteria


def generate_enhanced_markdown(output_path: str):
    """Generate enhanced markdown with categorized requirements."""
    output = []

    output.append("# PDF/UA Specifications and Technical Supplements\n")
    output.append("## Comprehensive Preflight Analysis\n\n")
    output.append(f"**Generated:** 2026-03-11\n")
    output.append("**Purpose:** Extract preflight-relevant requirements and validation rules\n\n")

    output.append("## Executive Summary\n\n")
    output.append("This document provides a comprehensive analysis of preflight requirements extracted ")
    output.append("from PDF/UA (PDF/Universal Accessibility) specifications and related technical supplements. ")
    output.append("The analysis categorizes requirements into actionable validation rules that can be ")
    output.append("implemented in a preflight engine.\n\n")

    output.append("## Document Coverage\n\n")
    output.append(f"**Total Documents Analyzed:** {len(DOCUMENTS)}\n\n")
    output.append("- 2 core PDF/UA specifications (ISO 14289-1:2014, ISO 14289-2:2024)\n")
    output.append("- 5 technical supplements (ISO TS 32001-32005)\n")
    output.append("- 3 best practice guides (WTPDF, Tagged PDF Best Practices)\n")
    output.append("- 3 PDF 2.0 annexes (BPC, AF, Object Metadata)\n")
    output.append("- 1 declarations guide\n\n")

    output.append("## Table of Contents\n\n")
    for doc in DOCUMENTS:
        anchor = doc['name'].lower().replace(':', '').replace(' ', '-')
        output.append(f"- [{doc['title']}](#{anchor})\n")

    output.append("\n---\n\n")

    # Consolidated requirements first
    output.append("## Consolidated Preflight Requirements\n\n")

    all_must_have = set()
    all_must_not = set()
    all_should = set()
    all_optional = set()
    all_validation = set()

    # First pass - collect all
    print("Analyzing all documents...")
    for doc in DOCUMENTS:
        print(f"  {doc['name']}")
        if not os.path.exists(doc['path']):
            continue

        text = extract_text_smart(doc['path'])
        if text:
            cats = categorize_requirements(text)
            all_must_have.update(cats['must_have'])
            all_must_not.update(cats['must_not_have'])
            all_should.update(cats['should_have'])
            all_optional.update(cats['optional'])
            all_validation.update(cats['validation'])

    # Output consolidated requirements
    if all_must_have:
        output.append("### Must-Have Requirements (Critical)\n\n")
        output.append("These requirements MUST be satisfied for PDF/UA conformance.\n\n")
        for idx, req in enumerate(sorted(all_must_have), 1):
            output.append(f"{idx}. {req}\n\n")

    if all_must_not:
        output.append("### Must-Not-Have (Prohibited)\n\n")
        output.append("These features MUST NOT be present in a conforming PDF/UA document.\n\n")
        for idx, req in enumerate(sorted(all_must_not), 1):
            output.append(f"{idx}. {req}\n\n")

    if all_should:
        output.append("### Should-Have (Recommended)\n\n")
        output.append("These are recommended features for best practice.\n\n")
        for idx, req in enumerate(sorted(all_should), 1):
            output.append(f"{idx}. {req}\n\n")

    if all_validation:
        output.append("### Validation Rules for Preflight\n\n")
        output.append("These rules form the basis of preflight validation checks.\n\n")
        for idx, rule in enumerate(sorted(all_validation), 1):
            output.append(f"{idx}. {rule}\n\n")

    output.append("---\n\n")

    # Detailed sections for each document
    output.append("## Detailed Requirements by Document\n\n")

    for doc in DOCUMENTS:
        print(f"  Extracting: {doc['name']}")
        if not os.path.exists(doc['path']):
            continue

        output.append(f"## {doc['title']}\n\n")
        output.append(f"**Standard:** {doc['name']}\n\n")
        output.append(f"**Description:** {doc['description']}\n\n")

        text = extract_text_smart(doc['path'])
        if not text:
            output.append("*Could not extract text from document*\n\n")
            continue

        # Categorized requirements
        cats = categorize_requirements(text)

        output.append(f"### Document Requirements\n\n")

        if cats['must_have']:
            output.append(f"**Must-Have** ({len(cats['must_have'])} items):\n\n")
            for req in cats['must_have'][:10]:
                output.append(f"- {req}\n")
            output.append("\n")

        if cats['must_not_have']:
            output.append(f"**Prohibited** ({len(cats['must_not_have'])} items):\n\n")
            for req in cats['must_not_have'][:10]:
                output.append(f"- {req}\n")
            output.append("\n")

        if cats['should_have']:
            output.append(f"**Recommended** ({len(cats['should_have'])} items):\n\n")
            for req in cats['should_have'][:5]:
                output.append(f"- {req}\n")
            output.append("\n")

        # Conformance criteria
        criteria = extract_conformance_criteria(text)

        if criteria['tag_requirements']:
            output.append(f"### Tag/Structure Requirements\n\n")
            for req in criteria['tag_requirements'][:5]:
                output.append(f"- {req}\n")
            output.append("\n")

        if criteria['metadata_requirements']:
            output.append(f"### Metadata Requirements\n\n")
            for req in criteria['metadata_requirements'][:5]:
                output.append(f"- {req}\n")
            output.append("\n")

        if criteria['test_procedures']:
            output.append(f"### Testing/Validation Procedures\n\n")
            for proc in criteria['test_procedures'][:5]:
                output.append(f"- {proc}\n")
            output.append("\n")

        output.append("---\n\n")

    # Summary statistics
    output.append("## Summary Statistics\n\n")
    output.append(f"**Total Must-Have Requirements:** {len(all_must_have)}\n\n")
    output.append(f"**Total Prohibited Features:** {len(all_must_not)}\n\n")
    output.append(f"**Total Recommended Features:** {len(all_should)}\n\n")
    output.append(f"**Total Validation Rules:** {len(all_validation)}\n\n")

    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output)

    print(f"\nReport generated: {output_path}")
    return {
        "must_have": len(all_must_have),
        "must_not": len(all_must_not),
        "should_have": len(all_should),
        "validation": len(all_validation),
    }


if __name__ == "__main__":
    output_path = "/sessions/adoring-peaceful-noether/mnt/grounded/grounded-research/specs/pdfua-and-supplements.md"

    print(f"Processing {len(DOCUMENTS)} PDF/UA specification documents...\n")

    stats = generate_enhanced_markdown(output_path)

    print("\nExtraction Complete!")
    print(f"\nGenerated Report:")
    print(f"  Must-Have Requirements: {stats['must_have']}")
    print(f"  Prohibited Features: {stats['must_not']}")
    print(f"  Recommended Features: {stats['should_have']}")
    print(f"  Validation Rules: {stats['validation']}")
    print(f"\nOutput: {output_path}")
