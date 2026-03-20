#!/usr/bin/env python3
"""
Comprehensive extraction of preflight-relevant content from PDF/UA specifications.
Focuses on requirements, validation rules, and conformance criteria.
"""

import pdfplumber
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

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


class SpecificationExtractor:
    def __init__(self):
        self.all_requirements = defaultdict(list)
        self.all_validation_rules = defaultdict(list)
        self.all_tables = defaultdict(list)
        self.doc_summaries = {}

    def extract_full_text(self, pdf_path: str) -> str:
        """Extract all text from PDF."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text_parts.append(extracted)
                return "\n".join(text_parts)
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return ""

    def extract_requirement_statements(self, text: str) -> List[str]:
        """Extract explicit requirement statements."""
        requirements = []

        # Patterns for requirements
        patterns = [
            r'(?:SHALL|SHALL NOT|Must|MUST|MUST NOT|Required|Requirement|shall|must)[^.!?]*[.!?]',
            r'shall.*?(?=\n|$)',
            r'must.*?(?=\n|$)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                stmt = match.group(0).strip()
                if len(stmt) > 20 and len(stmt) < 500:
                    requirements.append(stmt)

        return list(set(requirements))

    def extract_validation_hints(self, text: str) -> List[str]:
        """Extract validation and testing hints."""
        hints = []

        patterns = [
            r'(?:test|check|verify|validate|detect|identify|ensure|confirm)[^.!?]*(?:must|shall|should|can)[^.!?]*[.!?]',
            r'(?:PDF|Tag|Structure|Metadata|Declaration)[^.!?]*(?:must|shall|should)[^.!?]*[.!?]',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                hint = match.group(0).strip()
                if len(hint) > 25 and len(hint) < 500:
                    hints.append(hint)

        return list(set(hints))

    def extract_features_and_elements(self, text: str) -> Tuple[Set[str], Set[str]]:
        """Extract required and prohibited features."""
        required = set()
        prohibited = set()

        # Look for feature mentions
        feature_pattern = r'(?:Logical Structure Tree|Document Structure|Tags?|Marked Content|Metadata|XMP|Declarations?|Role Mapping|Artifacts?|Annotation|Form Fields?|Media Clips?|Sound|Movie|Launch Action|JavaScript|XFA)'

        for match in re.finditer(feature_pattern, text):
            feature = match.group(0)
            # Check context
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end].lower()

            if any(word in context for word in ['required', 'shall', 'must', 'mandatory']):
                required.add(feature)
            if any(word in context for word in ['prohibited', 'forbidden', 'shall not', 'must not', 'not allowed']):
                prohibited.add(feature)

        return required, prohibited

    def extract_tables(self, pdf_path: str) -> List[Dict]:
        """Extract tables from PDF."""
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    if page.tables:
                        for table_idx, table in enumerate(page.tables):
                            try:
                                data = page.extract_table()
                                if data:
                                    tables.append({
                                        "page": page_num,
                                        "table_idx": table_idx,
                                        "rows": len(data),
                                        "cols": len(data[0]) if data else 0,
                                    })
                            except:
                                pass
        except Exception as e:
            pass
        return tables

    def process_document(self, doc_info: Dict) -> Dict:
        """Process a single document."""
        print(f"Processing: {doc_info['name']}")

        path = doc_info['path']
        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}

        # Extract full text
        full_text = self.extract_full_text(path)
        if not full_text:
            return {"error": "No text extracted"}

        # Extract various elements
        requirements = self.extract_requirement_statements(full_text)
        validation_hints = self.extract_validation_hints(full_text)
        required_features, prohibited_features = self.extract_features_and_elements(full_text)
        tables = self.extract_tables(path)

        # First non-empty paragraph as scope
        paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip() and len(p) > 100]
        scope = paragraphs[5] if len(paragraphs) > 5 else (paragraphs[0] if paragraphs else "")

        result = {
            "name": doc_info['name'],
            "title": doc_info['title'],
            "text_length": len(full_text),
            "scope": scope[:300] + "..." if len(scope) > 300 else scope,
            "requirements": requirements[:15],
            "validation_hints": validation_hints[:15],
            "required_features": list(required_features)[:10],
            "prohibited_features": list(prohibited_features)[:10],
            "tables": tables,
        }

        # Store for consolidated view
        self.all_requirements[doc_info['name']] = requirements
        self.all_validation_rules[doc_info['name']] = validation_hints

        return result

    def generate_markdown(self, output_path: str):
        """Generate comprehensive markdown report."""
        output = []

        output.append("# PDF/UA Specifications - Comprehensive Preflight Analysis\n\n")
        output.append(f"**Generated:** 2026-03-11\n\n")
        output.append("This document provides detailed extraction of preflight-relevant requirements, ")
        output.append("validation rules, and conformance criteria from PDF/UA specifications and ")
        output.append("technical supplements.\n\n")

        output.append("## Executive Summary\n\n")
        output.append("The following PDF/UA documents have been analyzed for preflight engines:\n\n")

        # Process all documents
        doc_results = []
        for doc in DOCUMENTS:
            result = self.process_document(doc)
            doc_results.append(result)

        output.append("## Document Index\n\n")
        for result in doc_results:
            if "error" not in result:
                output.append(f"- [{result['title']}](#{result['name'].replace(':', '').replace(' ', '-')})\n")

        output.append("\n---\n\n")

        # Detailed sections for each document
        for result in doc_results:
            if "error" in result:
                continue

            name = result['name']
            title = result['title']

            anchor_id = name.replace(':', '').replace(' ', '-').lower()
            output.append(f"## {title}\n\n")
            output.append(f"**Standard:** {name}\n\n")
            output.append(f"**Text Size:** {result['text_length']:,} characters\n\n")

            if result['scope']:
                output.append(f"### Overview\n\n{result['scope']}\n\n")

            # Requirements Section
            if result['requirements']:
                output.append(f"### Key Requirements ({len(result['requirements'])} extracted)\n\n")
                for idx, req in enumerate(result['requirements'], 1):
                    clean_req = req.replace('\n', ' ').strip()
                    output.append(f"{idx}. {clean_req}\n\n")

            # Validation Hints
            if result['validation_hints']:
                output.append(f"### Validation Rules for Preflight ({len(result['validation_hints'])} extracted)\n\n")
                for idx, hint in enumerate(result['validation_hints'], 1):
                    clean_hint = hint.replace('\n', ' ').strip()
                    output.append(f"{idx}. {clean_hint}\n\n")

            # Required Features
            if result['required_features']:
                output.append(f"### Required Features\n\n")
                for feature in result['required_features']:
                    output.append(f"- {feature}\n")
                output.append("\n")

            # Prohibited Features
            if result['prohibited_features']:
                output.append(f"### Prohibited Features\n\n")
                for feature in result['prohibited_features']:
                    output.append(f"- {feature}\n")
                output.append("\n")

            # Tables
            if result['tables']:
                output.append(f"### Reference Tables ({len(result['tables'])} found)\n\n")
                for table_info in result['tables']:
                    output.append(f"- Page {table_info['page']}, Table {table_info['table_idx']}: ")
                    output.append(f"{table_info['rows']} rows × {table_info['cols']} columns\n")
                output.append("\n")

            output.append("---\n\n")

        # Consolidated Requirements Section
        output.append("## Consolidated Preflight Requirements\n\n")
        output.append("### All Unique Requirements Across Standards\n\n")

        all_reqs = set()
        for reqs in self.all_requirements.values():
            all_reqs.update(reqs)

        if all_reqs:
            for idx, req in enumerate(sorted(all_reqs), 1):
                if len(req) > 30:
                    output.append(f"{idx}. {req}\n\n")

        # Consolidated Validation Rules
        output.append("## Consolidated Validation Rules\n\n")
        output.append("### All Unique Validation Hints\n\n")

        all_rules = set()
        for rules in self.all_validation_rules.values():
            all_rules.update(rules)

        if all_rules:
            for idx, rule in enumerate(sorted(all_rules), 1):
                if len(rule) > 30:
                    output.append(f"{idx}. {rule}\n\n")

        # Write output
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(output)

        print(f"\nReport written to: {output_path}")
        print(f"Total requirements extracted: {len(all_reqs)}")
        print(f"Total validation rules extracted: {len(all_rules)}")


if __name__ == "__main__":
    output_path = "/sessions/adoring-peaceful-noether/mnt/grounded/grounded-research/specs/pdfua-and-supplements.md"

    print(f"Extracting from {len(DOCUMENTS)} PDF documents...")
    print()

    extractor = SpecificationExtractor()
    extractor.generate_markdown(output_path)

    print("\nExtraction complete!")
