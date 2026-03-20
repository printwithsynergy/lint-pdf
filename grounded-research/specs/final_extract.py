#!/usr/bin/env python3
"""
Final optimized extraction of PDF/UA specifications for preflight analysis.
"""

import pdfplumber
import os
import re
from typing import Dict, List, Set

DOCUMENTS = [
    ("ISO-14289-1-2014-sponsored.pdf", "ISO 14289-1:2014", "PDF/UA-1: Universal Accessibility"),
    ("ISO-14289-2-2024-sponsored.pdf", "ISO 14289-2:2024", "PDF/UA-2: Universal Accessibility"),
    ("ISO-TS-32005-2023-sponsored.pdf", "ISO TS 32005:2023", "Structure Namespace and Role Mapping"),
    ("ISO_TS_32001-2022_sponsored.pdf", "ISO TS 32001:2022", "PDF/UA Reference - Logical Structure"),
    ("ISO_TS_32002-2022_sponsored.pdf", "ISO TS 32002:2022", "PDF/UA Reference - Artifacts & Role Mapping"),
    ("ISO_TS_32003-2023_sponsored.pdf", "ISO TS 32003:2023", "PDF/UA Reference - Marked Content"),
    ("ISO-TS-32004-2024_sponsored.pdf", "ISO TS 32004:2024", "PDF/UA Reference - Conformance & Testing"),
    ("Well-Tagged-PDF-WTPDF-1.0.pdf", "WTPDF 1.0", "Well-Tagged PDF Specification"),
    ("Tagged-PDF-Best-Practice-Guide.pdf", "Best Practice Guide", "Tagged PDF Best Practices"),
    ("PDF-Declarations.pdf", "PDF Declarations", "PDF Metadata Declarations"),
    ("PDF20_AN001-BPC.pdf", "PDF 2.0 AN001", "Best Practice Contents"),
    ("PDF20_AN002-AF.pdf", "PDF 2.0 AN002", "Associated Files"),
    ("PDF20_AN003-ObjectMetadataLocations.pdf", "PDF 2.0 AN003", "Object Metadata Locations"),
]

BASE_PATH = "/sessions/adoring-peaceful-noether/mnt/uploads"


def extract_text_limited(filename, max_kb=80):
    """Extract text from PDF, limited to max_kb."""
    path = os.path.join(BASE_PATH, filename)
    if not os.path.exists(path):
        return ""

    try:
        with pdfplumber.open(path) as pdf:
            text = ""
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
                if len(text) > max_kb * 1024:
                    break
            return text
    except Exception as e:
        print(f"  Error: {e}")
        return ""


def parse_requirements(text):
    """Extract requirement statements."""
    reqs = {
        "must_have": [],
        "must_not": [],
        "should": [],
        "validation": [],
        "tags": [],
        "metadata": [],
    }

    lines = text.split('\n')
    for line in lines:
        clean = line.strip()
        if not clean or len(clean) < 20 or len(clean) > 400:
            continue

        lower = clean.lower()

        # Categorize
        if 'shall not' in lower or 'must not' in lower or 'prohibited' in lower:
            reqs["must_not"].append(clean)
        elif any(kw in lower for kw in ['shall ', 'must ', 'required']):
            reqs["must_have"].append(clean)
        elif 'should' in lower or 'recommended' in lower:
            reqs["should"].append(clean)

        if any(kw in lower for kw in ['check ', 'validate ', 'verify ', 'test ']):
            reqs["validation"].append(clean)

        if any(kw in lower for kw in ['tag', 'structure', 'logical structure']):
            if any(req in lower for req in ['must', 'shall', 'required']):
                reqs["tags"].append(clean)

        if any(kw in lower for kw in ['metadata', 'xmp', 'catalog']):
            if any(req in lower for req in ['must', 'shall', 'required']):
                reqs["metadata"].append(clean)

    # Deduplicate and limit
    for key in reqs:
        reqs[key] = list(dict.fromkeys(reqs[key]))[:12]

    return reqs


def main():
    output_path = "/sessions/adoring-peaceful-noether/mnt/grounded/grounded-research/specs/pdfua-and-supplements.md"

    output = []
    output.append("# PDF/UA Specifications and Technical Supplements\n")
    output.append("## Preflight-Relevant Requirements Analysis\n\n")
    output.append(f"**Analysis Date:** 2026-03-11\n")
    output.append(f"**Documents Analyzed:** {len(DOCUMENTS)}\n\n")

    output.append("## Overview\n\n")
    output.append("This document consolidates preflight validation requirements extracted from ")
    output.append("PDF/UA specifications and technical supplements. Requirements are categorized ")
    output.append("by type to support implementation in a preflight validation engine.\n\n")

    # Collect all requirements
    all_reqs = {
        "must_have": set(),
        "must_not": set(),
        "should": set(),
        "validation": set(),
        "tags": set(),
        "metadata": set(),
    }

    doc_summaries = []

    print(f"Processing {len(DOCUMENTS)} documents...\n")

    # First pass - extract from all documents
    for filename, standard, title in DOCUMENTS:
        print(f"  {standard}")
        text = extract_text_limited(filename)
        if not text:
            continue

        reqs = parse_requirements(text)

        # Accumulate
        for key in all_reqs:
            all_reqs[key].update(reqs[key])

        doc_summaries.append({
            "standard": standard,
            "title": title,
            "requirements": reqs,
        })

    print("\nGenerating report...")

    # Table of Contents
    output.append("## Table of Contents\n\n")
    for _, standard, title in DOCUMENTS:
        anchor = standard.lower().replace(':', '').replace(' ', '-')
        output.append(f"- [{title}](#{anchor})\n")
    output.append("\n---\n\n")

    # Consolidated Requirements Section
    output.append("## Consolidated Preflight Requirements\n\n")

    output.append("### Critical Requirements (Must-Have)\n\n")
    output.append("These requirements MUST be satisfied for PDF/UA conformance:\n\n")
    for idx, req in enumerate(sorted(all_reqs["must_have"]), 1):
        output.append(f"{idx}. {req}\n\n")

    output.append("### Prohibited Features (Must-Not-Have)\n\n")
    output.append("These features MUST NOT be present:\n\n")
    for idx, req in enumerate(sorted(all_reqs["must_not"]), 1):
        output.append(f"{idx}. {req}\n\n")

    output.append("### Recommended Features\n\n")
    output.append("These features are recommended:\n\n")
    for idx, req in enumerate(sorted(all_reqs["should"]), 1):
        output.append(f"{idx}. {req}\n\n")

    output.append("### Tag and Structure Requirements\n\n")
    output.append("Specific requirements for PDF structure and tags:\n\n")
    for idx, req in enumerate(sorted(all_reqs["tags"]), 1):
        output.append(f"{idx}. {req}\n\n")

    output.append("### Metadata Requirements\n\n")
    output.append("Specific requirements for PDF metadata:\n\n")
    for idx, req in enumerate(sorted(all_reqs["metadata"]), 1):
        output.append(f"{idx}. {req}\n\n")

    output.append("### Validation Rules\n\n")
    output.append("Rules for preflight validation checks:\n\n")
    for idx, rule in enumerate(sorted(all_reqs["validation"]), 1):
        output.append(f"{idx}. {rule}\n\n")

    output.append("---\n\n")

    # Detailed document sections
    output.append("## Detailed Requirements by Document\n\n")

    for summary in doc_summaries:
        standard = summary["standard"]
        title = summary["title"]
        reqs = summary["requirements"]

        anchor = standard.lower().replace(':', '').replace(' ', '-')
        output.append(f"## {title}\n\n")
        output.append(f"**Standard:** {standard}\n\n")

        if reqs["must_have"]:
            output.append(f"### Must-Have Requirements ({len(reqs['must_have'])})\n\n")
            for req in list(reqs["must_have"])[:8]:
                output.append(f"- {req}\n")
            output.append("\n")

        if reqs["must_not"]:
            output.append(f"### Prohibited Features ({len(reqs['must_not'])})\n\n")
            for req in list(reqs["must_not"])[:8]:
                output.append(f"- {req}\n")
            output.append("\n")

        if reqs["tags"]:
            output.append(f"### Tag Requirements ({len(reqs['tags'])})\n\n")
            for req in list(reqs["tags"])[:5]:
                output.append(f"- {req}\n")
            output.append("\n")

        if reqs["metadata"]:
            output.append(f"### Metadata Requirements ({len(reqs['metadata'])})\n\n")
            for req in list(reqs["metadata"])[:5]:
                output.append(f"- {req}\n")
            output.append("\n")

        output.append("---\n\n")

    # Summary
    output.append("## Summary Statistics\n\n")
    output.append(f"**Critical Must-Have Requirements:** {len(all_reqs['must_have'])}\n\n")
    output.append(f"**Prohibited Features:** {len(all_reqs['must_not'])}\n\n")
    output.append(f"**Recommended Features:** {len(all_reqs['should'])}\n\n")
    output.append(f"**Tag Requirements:** {len(all_reqs['tags'])}\n\n")
    output.append(f"**Metadata Requirements:** {len(all_reqs['metadata'])}\n\n")
    output.append(f"**Validation Rules:** {len(all_reqs['validation'])}\n\n")

    # Write file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output)

    print(f"Report written to: {output_path}")
    print(f"\nRequirements Summary:")
    print(f"  Must-Have: {len(all_reqs['must_have'])}")
    print(f"  Prohibited: {len(all_reqs['must_not'])}")
    print(f"  Recommended: {len(all_reqs['should'])}")
    print(f"  Tag-specific: {len(all_reqs['tags'])}")
    print(f"  Metadata-specific: {len(all_reqs['metadata'])}")
    print(f"  Validation Rules: {len(all_reqs['validation'])}")


if __name__ == "__main__":
    main()
