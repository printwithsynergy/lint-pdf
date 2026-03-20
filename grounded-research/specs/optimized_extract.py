#!/usr/bin/env python3
"""
Optimized extraction focusing on key pages and patterns.
"""

import pdfplumber
import os
import re
from typing import Dict, List, Set

DOCUMENTS = [
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO-14289-1-2014-sponsored.pdf",
        "name": "ISO 14289-1:2014",
        "title": "PDF/UA-1: Universal Accessibility",
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO-14289-2-2024-sponsored.pdf",
        "name": "ISO 14289-2:2024",
        "title": "PDF/UA-2: Universal Accessibility",
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO-TS-32005-2023-sponsored.pdf",
        "name": "ISO TS 32005:2023",
        "title": "Structure Namespace and Role Mapping",
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO_TS_32001-2022_sponsored.pdf",
        "name": "ISO TS 32001:2022",
        "title": "PDF/UA Reference Implementation - Logical Structure",
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO_TS_32002-2022_sponsored.pdf",
        "name": "ISO TS 32002:2022",
        "title": "PDF/UA Reference Implementation - Artifacts and Role Mapping",
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO_TS_32003-2023_sponsored.pdf",
        "name": "ISO TS 32003:2023",
        "title": "PDF/UA Reference Implementation - Marked Content",
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO-TS-32004-2024_sponsored.pdf",
        "name": "ISO TS 32004:2024",
        "title": "PDF/UA Reference Implementation - Conformance and Testing",
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/Well-Tagged-PDF-WTPDF-1.0.pdf",
        "name": "WTPDF 1.0",
        "title": "Well-Tagged PDF Specification",
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/Tagged-PDF-Best-Practice-Guide.pdf",
        "name": "Tagged PDF Best Practice Guide",
        "title": "Best Practice Guide for Tagged PDF",
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/PDF-Declarations.pdf",
        "name": "PDF Declarations",
        "title": "PDF Metadata Declarations",
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/PDF20_AN001-BPC.pdf",
        "name": "PDF 2.0 AN001",
        "title": "Best Practice Contents",
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/PDF20_AN002-AF.pdf",
        "name": "PDF 2.0 AN002",
        "title": "Associated Files",
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/PDF20_AN003-ObjectMetadataLocations.pdf",
        "name": "PDF 2.0 AN003",
        "title": "Object Metadata Locations",
    },
]


def extract_text_limited(pdf_path: str, max_pages: int = 15) -> str:
    """Extract text from first N pages only."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text_parts = []
            limit = min(max_pages, len(pdf.pages))
            for page in pdf.pages[:limit]:
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
            return "\n".join(text_parts)
    except Exception as e:
        print(f"  Error: {e}")
        return ""


def extract_requirement_patterns(text: str) -> List[str]:
    """Extract lines containing requirement keywords."""
    requirements = []
    lines = text.split('\n')

    for line in lines:
        line_clean = line.strip()
        if not line_clean or len(line_clean) < 20:
            continue

        keywords = ['shall', 'must', 'required', 'requirement', 'mandatory', 'shall not', 'must not']
        if any(kw in line_clean.lower() for kw in keywords):
            # Clean up and limit length
            clean = re.sub(r'\s+', ' ', line_clean)
            if len(clean) < 400:
                requirements.append(clean)

    return list(dict.fromkeys(requirements))[:20]  # Remove duplicates, limit to 20


def extract_section_headers(text: str) -> List[str]:
    """Extract section headers and titles."""
    sections = []
    lines = text.split('\n')

    for line in lines:
        stripped = line.strip()
        # Section headers are usually short, all caps or numbered
        if (len(stripped) > 5 and len(stripped) < 120 and
            (stripped.isupper() or stripped[0].isdigit() or 'clause' in stripped.lower() or
             'annex' in stripped.lower())):
            sections.append(stripped)

    return list(dict.fromkeys(sections))[:15]


def process_document_fast(doc_info: Dict) -> Dict:
    """Fast processing of single document."""
    print(f"  Processing: {doc_info['name']}")

    path = doc_info['path']
    if not os.path.exists(path):
        return {"error": f"File not found"}

    # Extract text from first 15 pages only
    text = extract_text_limited(path, max_pages=15)
    if not text:
        return {"error": "No text extracted"}

    # Extract elements
    requirements = extract_requirement_patterns(text)
    sections = extract_section_headers(text)

    # Get scope from first meaningful paragraph
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p) > 50]
    scope = paragraphs[0][:400] if paragraphs else "N/A"

    return {
        "name": doc_info['name'],
        "title": doc_info['title'],
        "scope": scope,
        "requirements": requirements,
        "sections": sections[:10],
    }


def generate_markdown(docs_results: List[Dict], output_path: str):
    """Generate markdown report."""
    output = []

    output.append("# PDF/UA Specifications and Technical Supplements\n")
    output.append("## Preflight-Relevant Requirements Analysis\n\n")
    output.append(f"**Generated:** 2026-03-11\n\n")

    output.append("## Document Overview\n\n")
    output.append("This document consolidates preflight-relevant requirements from PDF/UA ")
    output.append("specifications and technical supplements.\n\n")

    output.append("## Table of Contents\n\n")
    for result in docs_results:
        if "error" not in result:
            anchor = result['name'].lower().replace(':', '').replace(' ', '-')
            output.append(f"- [{result['title']}](#{anchor})\n")

    output.append("\n---\n\n")

    # Collect all requirements
    all_requirements = []

    # Detailed sections
    for result in docs_results:
        if "error" in result:
            continue

        output.append(f"## {result['title']}\n\n")
        output.append(f"**Standard:** {result['name']}\n\n")

        if result['scope']:
            output.append(f"### Overview\n\n{result['scope']}\n\n")

        if result['sections']:
            output.append(f"### Key Sections\n\n")
            for section in result['sections']:
                output.append(f"- {section}\n")
            output.append("\n")

        if result['requirements']:
            output.append(f"### Requirements ({len(result['requirements'])} extracted)\n\n")
            all_requirements.extend(result['requirements'])
            for req in result['requirements']:
                output.append(f"- {req}\n\n")

        output.append("---\n\n")

    # Consolidated requirements
    output.append("## Consolidated Preflight Requirements\n\n")
    output.append(f"**Total Unique Requirements:** {len(set(all_requirements))}\n\n")

    output.append("### Core Validation Rules\n\n")
    unique_reqs = list(set(all_requirements))
    for idx, req in enumerate(sorted(unique_reqs), 1):
        output.append(f"{idx}. {req}\n\n")

    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output)

    print(f"\nReport generated: {output_path}")
    print(f"Total requirements documented: {len(set(all_requirements))}")


if __name__ == "__main__":
    output_path = "/sessions/adoring-peaceful-noether/mnt/grounded/grounded-research/specs/pdfua-and-supplements.md"

    print(f"Processing {len(DOCUMENTS)} documents...")
    print()

    results = []
    for doc in DOCUMENTS:
        result = process_document_fast(doc)
        results.append(result)

    print()
    generate_markdown(results, output_path)
    print("Complete!")
