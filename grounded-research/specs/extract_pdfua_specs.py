#!/usr/bin/env python3
"""
Extract preflight-relevant content from PDF/UA specifications and technical supplements.
"""

import pdfplumber
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Define documents to process
DOCUMENTS = [
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO-14289-1-2014-sponsored.pdf",
        "name": "ISO 14289-1:2014",
        "title": "PDF/UA-1: Universal Accessibility",
        "pages": 25,
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO-14289-2-2024-sponsored.pdf",
        "name": "ISO 14289-2:2024",
        "title": "PDF/UA-2: Universal Accessibility",
        "pages": 51,
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO-TS-32005-2023-sponsored.pdf",
        "name": "ISO TS 32005:2023",
        "title": "Structure Namespace",
        "pages": 49,
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO_TS_32001-2022_sponsored.pdf",
        "name": "ISO TS 32001:2022",
        "title": "Technical Supplement 1",
        "pages": 13,
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO_TS_32002-2022_sponsored.pdf",
        "name": "ISO TS 32002:2022",
        "title": "Technical Supplement 2",
        "pages": 13,
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO_TS_32003-2023_sponsored.pdf",
        "name": "ISO TS 32003:2023",
        "title": "Technical Supplement 3",
        "pages": 13,
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/ISO-TS-32004-2024_sponsored.pdf",
        "name": "ISO TS 32004:2024",
        "title": "Technical Supplement 4",
        "pages": 25,
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/Well-Tagged-PDF-WTPDF-1.0.pdf",
        "name": "WTPDF 1.0",
        "title": "Well-Tagged PDF",
        "pages": 57,
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/Tagged-PDF-Best-Practice-Guide.pdf",
        "name": "Best Practice Guide",
        "title": "Tagged PDF Best Practices",
        "pages": 72,
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/PDF-Declarations.pdf",
        "name": "PDF Declarations",
        "title": "PDF Declarations",
        "pages": 10,
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/PDF20_AN001-BPC.pdf",
        "name": "PDF 2.0 Annex 1",
        "title": "Best Practice Contents",
        "pages": 5,
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/PDF20_AN002-AF.pdf",
        "name": "PDF 2.0 Annex 2",
        "title": "Associated Files",
        "pages": 14,
    },
    {
        "path": "/sessions/adoring-peaceful-noether/mnt/uploads/PDF20_AN003-ObjectMetadataLocations.pdf",
        "name": "PDF 2.0 Annex 3",
        "title": "Object Metadata Locations",
        "pages": 10,
    },
]


def extract_document_content(pdf_path: str) -> Dict[str, any]:
    """Extract comprehensive content from a single PDF document."""

    if not os.path.exists(pdf_path):
        return {"error": f"File not found: {pdf_path}"}

    doc_data = {
        "pages": [],
        "text_content": "",
        "tables": [],
        "headings": [],
        "requirements": [],
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""

            for page_num, page in enumerate(pdf.pages, 1):
                page_data = {
                    "page_num": page_num,
                    "text": page.extract_text() or "",
                    "tables": [],
                }

                # Extract tables
                if page.tables:
                    for table in page.tables:
                        try:
                            extracted_table = page.extract_table()
                            if extracted_table:
                                page_data["tables"].append({
                                    "data": extracted_table,
                                    "page": page_num,
                                })
                                doc_data["tables"].append({
                                    "page": page_num,
                                    "data": extracted_table,
                                })
                        except Exception as e:
                            pass

                full_text += page_data["text"] + "\n"
                doc_data["pages"].append(page_data)

            doc_data["text_content"] = full_text

    except Exception as e:
        doc_data["error"] = str(e)

    return doc_data


def extract_key_sections(text: str, doc_name: str) -> Dict[str, any]:
    """Extract key sections and requirements from document text."""

    sections = {
        "requirements": [],
        "validation_rules": [],
        "prohibited_features": [],
        "required_features": [],
        "conformance_levels": [],
    }

    lines = text.split('\n')

    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Extract requirements
        if any(req in line_lower for req in ['shall', 'must', 'required', 'requirement', 'shallnot', 'shall not']):
            sections["requirements"].append(line.strip())

        # Extract prohibited/required features
        if 'prohibited' in line_lower or 'forbidden' in line_lower:
            sections["prohibited_features"].append(line.strip())

        if 'required' in line_lower and 'feature' in line_lower:
            sections["required_features"].append(line.strip())

        # Extract conformance levels
        if 'conformance' in line_lower or 'conform' in line_lower:
            sections["conformance_levels"].append(line.strip())

        # Extract validation hints
        if any(hint in line_lower for hint in ['check', 'validate', 'verify', 'test', 'detection', 'identify']):
            sections["validation_rules"].append(line.strip())

    return sections


def generate_markdown_report(documents: List[Dict], output_path: str):
    """Generate consolidated markdown report."""

    output = []
    output.append("# PDF/UA Specifications and Technical Supplements - Preflight Analysis\n")
    output.append(f"**Generated:** 2026-03-11\n\n")
    output.append("## Overview\n\n")
    output.append("This document consolidates preflight-relevant requirements, validation rules, and ")
    output.append("conformance criteria extracted from PDF/UA specifications and technical supplements.\n\n")

    output.append("## Table of Contents\n\n")

    for doc in documents:
        doc_title = doc.get("title", doc.get("name", "Unknown"))
        anchor = doc_title.lower().replace(" ", "-").replace(":", "")
        output.append(f"- [{doc_title}](#{anchor})\n")

    output.append("\n---\n\n")

    # Process each document
    for idx, doc in enumerate(documents, 1):
        print(f"Processing document {idx}/{len(documents)}: {doc['name']}")

        pdf_path = doc["path"]
        doc_title = doc.get("title", doc.get("name", "Unknown"))

        output.append(f"## {doc_title}\n\n")
        output.append(f"**Document:** {doc['name']}\n\n")
        output.append(f"**Pages:** {doc.get('pages', 'Unknown')}\n\n")

        # Extract content
        doc_content = extract_document_content(pdf_path)

        if "error" in doc_content:
            output.append(f"**Error:** {doc_content['error']}\n\n")
            continue

        # Extract key sections
        text_content = doc_content.get("text_content", "")

        if text_content:
            key_sections = extract_key_sections(text_content, doc['name'])

            # Add first 500 chars of content as scope
            first_section = text_content[:500].replace('\n', ' ').strip()
            output.append(f"### Scope\n\n")
            output.append(f"{first_section}...\n\n")

            # Requirements
            if key_sections["requirements"]:
                output.append(f"### Key Requirements\n\n")
                unique_reqs = list(set([r for r in key_sections["requirements"] if len(r) > 20]))[:10]
                for req in unique_reqs:
                    output.append(f"- {req}\n")
                output.append("\n")

            # Prohibited Features
            if key_sections["prohibited_features"]:
                output.append(f"### Prohibited Features\n\n")
                unique_prohibited = list(set([p for p in key_sections["prohibited_features"] if len(p) > 20]))[:8]
                for prohibited in unique_prohibited:
                    output.append(f"- {prohibited}\n")
                output.append("\n")

            # Required Features
            if key_sections["required_features"]:
                output.append(f"### Required Features\n\n")
                unique_required = list(set([r for r in key_sections["required_features"] if len(r) > 20]))[:8]
                for required in unique_required:
                    output.append(f"- {required}\n")
                output.append("\n")

            # Validation Rules
            if key_sections["validation_rules"]:
                output.append(f"### Validation Rules for Preflight\n\n")
                unique_rules = list(set([r for r in key_sections["validation_rules"] if len(r) > 15]))[:10]
                for rule in unique_rules:
                    output.append(f"- {rule}\n")
                output.append("\n")

            # Tables
            if doc_content["tables"]:
                output.append(f"### Reference Tables\n\n")
                output.append(f"*Found {len(doc_content['tables'])} table(s) in document*\n\n")

        output.append("---\n\n")

    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output)

    print(f"\nReport written to: {output_path}")


if __name__ == "__main__":
    output_file = "/sessions/adoring-peaceful-noether/mnt/grounded/grounded-research/specs/pdfua-and-supplements.md"

    print(f"Extracting content from {len(DOCUMENTS)} PDF documents...")
    print(f"Output will be written to: {output_file}\n")

    generate_markdown_report(DOCUMENTS, output_file)

    print("Extraction complete!")
