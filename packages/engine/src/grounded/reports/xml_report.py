"""XML report generation using defusedxml."""

from __future__ import annotations

from typing import TYPE_CHECKING

# nosemgrep: use-defused-xml — output-only XML generation, no parsing of external XML
from xml.etree.ElementTree import Element, SubElement, tostring

if TYPE_CHECKING:
    from grounded.profiles.orchestrator import PreflightResult


def _add_text_element(parent: Element, tag: str, text: str) -> Element:
    """Add a child element with text content."""
    el = SubElement(parent, tag)
    el.text = str(text)
    return el


def generate_xml_report(result: PreflightResult) -> bytes:  # skipcq: PY-R1000
    """Generate an XML report from preflight results.

    Args:
        result: Preflight result to serialize.

    Returns:
        UTF-8 encoded XML bytes.
    """
    root = Element("PreflightReport")
    root.set("xmlns", "urn:grounded:preflight:1.0")

    # Job info
    _add_text_element(root, "JobId", result.job_id)
    _add_text_element(root, "ProfileId", result.profile_id)
    _add_text_element(root, "DurationMs", str(result.duration_ms))

    # Summary
    summary_el = SubElement(root, "Summary")
    _add_text_element(summary_el, "Passed", str(result.summary.passed).lower())
    _add_text_element(summary_el, "TotalFindings", str(result.summary.total_findings))
    _add_text_element(summary_el, "ErrorCount", str(result.summary.error_count))
    _add_text_element(summary_el, "WarningCount", str(result.summary.warning_count))
    _add_text_element(summary_el, "AdvisoryCount", str(result.summary.advisory_count))
    _add_text_element(summary_el, "PageCount", str(result.summary.page_count))
    _add_text_element(summary_el, "FileSizeBytes", str(result.summary.file_size_bytes))

    # Document metadata
    doc_el = SubElement(root, "Document")
    _add_text_element(doc_el, "PdfVersion", result.metadata.get("pdf_version", ""))
    _add_text_element(
        doc_el,
        "IsEncrypted",
        str(result.metadata.get("is_encrypted", False)).lower(),
    )
    _add_text_element(
        doc_el,
        "Conformance",
        result.metadata.get("conformance", ""),
    )

    # Findings
    findings_el = SubElement(root, "Findings")
    for f in result.findings:
        finding_el = SubElement(findings_el, "Finding")
        _add_text_element(
            finding_el,
            "InspectionId",
            f.inspection_id,
        )
        severity = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
        _add_text_element(finding_el, "Severity", severity)
        _add_text_element(finding_el, "Message", f.message)
        if f.page_num is not None:
            _add_text_element(finding_el, "PageNum", str(f.page_num))
        if f.object_id:
            _add_text_element(finding_el, "ObjectId", f.object_id)
        if f.object_type:
            _add_text_element(finding_el, "ObjectType", f.object_type)
        if f.iso_clause:
            _add_text_element(finding_el, "IsoClause", f.iso_clause)
        source = getattr(f, "source", "engine")
        _add_text_element(finding_el, "Source", source)
        category = getattr(f, "category", None)
        if category:
            _add_text_element(finding_el, "Category", category)
        if f.details:
            details_el = SubElement(finding_el, "Details")
            for key, val in f.details.items():
                detail = SubElement(details_el, "Detail")
                detail.set("key", str(key))
                detail.text = str(val)

    xml_bytes = tostring(root, encoding="unicode", xml_declaration=False)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes).encode("utf-8")
