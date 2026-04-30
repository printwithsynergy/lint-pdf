"""XML report generation using defusedxml."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# nosemgrep: use-defused-xml — output-only XML generation, no parsing of external XML
from xml.etree.ElementTree import Element, SubElement, tostring

if TYPE_CHECKING:
    from siftpdf.profiles.orchestrator import PreflightResult


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
    root.set("xmlns", "urn:lintpdf:preflight:1.0")

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


def generate_xml_from_dict(result_json: dict[str, Any]) -> bytes:
    """Generate an XML report from a result_json dict.

    Mirror of :func:`generate_json_from_dict` for the legacy XML format.
    Same field taxonomy as the JSON report — Switch, MIS, and other
    XML-only consumers can ingest this directly.

    Args:
        result_json: Job result dict (see ``generate_json_from_dict``).

    Returns:
        UTF-8 encoded XML bytes with declaration.
    """
    summary = result_json.get("summary", {}) or {}
    metadata = result_json.get("metadata", {}) or {}
    findings_raw = result_json.get("findings", []) or []

    root = Element("PreflightReport")
    root.set("xmlns", "urn:lintpdf:preflight:1.0")
    root.set("schemaVersion", "1")

    _add_text_element(root, "JobId", str(result_json.get("job_id", "")))
    _add_text_element(root, "ProfileId", str(result_json.get("profile_id", "")))
    if result_json.get("duration_ms") is not None:
        _add_text_element(root, "DurationMs", str(result_json.get("duration_ms")))
    _add_text_element(root, "PreflightSource", str(result_json.get("preflight_source", "engine")))
    if result_json.get("external_format"):
        _add_text_element(root, "ExternalFormat", str(result_json.get("external_format")))

    summary_el = SubElement(root, "Summary")
    _add_text_element(summary_el, "Passed", str(summary.get("passed", "")).lower())
    _add_text_element(summary_el, "TotalFindings", str(summary.get("total_findings", 0)))
    _add_text_element(summary_el, "ErrorCount", str(summary.get("error_count", 0)))
    _add_text_element(summary_el, "WarningCount", str(summary.get("warning_count", 0)))
    _add_text_element(summary_el, "AdvisoryCount", str(summary.get("advisory_count", 0)))
    _add_text_element(
        summary_el,
        "PageCount",
        str(summary.get("page_count", metadata.get("page_count", 0))),
    )
    _add_text_element(summary_el, "FileSizeBytes", str(summary.get("file_size_bytes", 0)))

    doc_el = SubElement(root, "Document")
    _add_text_element(doc_el, "PdfVersion", str(metadata.get("pdf_version", "")))
    _add_text_element(doc_el, "IsEncrypted", str(metadata.get("is_encrypted", False)).lower())
    if metadata.get("conformance"):
        _add_text_element(doc_el, "Conformance", str(metadata.get("conformance")))

    findings_el = SubElement(root, "Findings")
    for f in findings_raw:
        if not isinstance(f, dict):
            continue
        finding_el = SubElement(findings_el, "Finding")
        _add_text_element(finding_el, "InspectionId", str(f.get("inspection_id", "")))
        _add_text_element(finding_el, "Severity", str(f.get("severity", "")))
        _add_text_element(finding_el, "Message", str(f.get("message", "")))
        if f.get("page_num") is not None:
            _add_text_element(finding_el, "PageNum", str(f.get("page_num")))
        if f.get("object_id"):
            _add_text_element(finding_el, "ObjectId", str(f.get("object_id")))
        if f.get("object_type"):
            _add_text_element(finding_el, "ObjectType", str(f.get("object_type")))
        if f.get("iso_clause"):
            _add_text_element(finding_el, "IsoClause", str(f.get("iso_clause")))
        if f.get("category"):
            _add_text_element(finding_el, "Category", str(f.get("category")))
        _add_text_element(finding_el, "Source", str(f.get("source") or "engine"))
        bbox = f.get("bbox")
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4 and all(b is not None for b in bbox):
            _add_text_element(finding_el, "BBox", " ".join(str(b) for b in bbox))
        details = f.get("details")
        if isinstance(details, dict) and details:
            details_el = SubElement(finding_el, "Details")
            for key, val in details.items():
                detail = SubElement(details_el, "Detail")
                detail.set("key", str(key))
                detail.text = str(val)

    xml_bytes = tostring(root, encoding="unicode", xml_declaration=False)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes).encode("utf-8")
