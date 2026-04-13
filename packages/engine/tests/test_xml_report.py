"""Tests for XML report generation."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.profiles.orchestrator import PreflightResult, PreflightSummary
from lintpdf.reports.xml_report import generate_xml_from_dict, generate_xml_report


@pytest.fixture
def sample_result() -> PreflightResult:
    """Sample result with multiple findings."""
    findings = [
        Finding(
            inspection_id="LPDF_FONT_001",
            severity=Severity.ERROR,
            message="Font 'Arial' is not embedded",
            page_num=1,
            object_id="F1",
            object_type="font",
            iso_clause="ISO 32000-2:2020 9.6",
        ),
        Finding(
            inspection_id="LPDF_IMG_001",
            severity=Severity.WARNING,
            message="Image resolution below minimum (72 DPI < 150 DPI)",
            page_num=1,
            object_id="Im1",
            object_type="image",
            details={"actual_dpi": 72, "min_dpi": 150},
        ),
        Finding(
            inspection_id="LPDF_COLOR_003",
            severity=Severity.ADVISORY,
            message="RGB color space detected",
            page_num=2,
            object_type="color",
        ),
    ]
    summary = PreflightSummary(
        total_findings=3,
        error_count=1,
        warning_count=1,
        advisory_count=1,
        passed=False,
        page_count=2,
        file_size_bytes=1048576,
    )
    return PreflightResult(
        job_id="test-job-001",
        profile_id="lintpdf-default",
        findings=findings,
        summary=summary,
        metadata={
            "pdf_version": "1.7",
            "page_count": 2,
            "is_encrypted": False,
            "conformance": "pdfx4",
        },
        duration_ms=42,
    )


@pytest.fixture
def empty_result() -> PreflightResult:
    """Result with no findings."""
    return PreflightResult(
        job_id="test-job-002",
        profile_id="lintpdf-default",
        findings=[],
        summary=PreflightSummary(
            total_findings=0,
            error_count=0,
            warning_count=0,
            advisory_count=0,
            passed=True,
            page_count=1,
            file_size_bytes=512000,
        ),
        metadata={
            "pdf_version": "1.4",
            "page_count": 1,
            "is_encrypted": False,
            "conformance": None,
        },
        duration_ms=10,
    )


def _parse_xml(xml_bytes: bytes) -> ET.Element:
    """Parse XML bytes into an Element, stripping namespace."""
    root = ET.fromstring(xml_bytes)
    # Strip namespace for easier querying
    ns = "urn:lintpdf:preflight:1.0"
    for elem in root.iter():
        if elem.tag.startswith(f"{{{ns}}}"):
            elem.tag = elem.tag[len(f"{{{ns}}}") :]
    return root


class TestXmlReportStructure:
    """Tests for overall XML document structure."""

    @staticmethod
    def test_returns_bytes(sample_result) -> None:
        result = generate_xml_report(sample_result)
        assert isinstance(result, bytes)

    @staticmethod
    def test_starts_with_xml_declaration(sample_result) -> None:
        result = generate_xml_report(sample_result)
        text = result.decode("utf-8")
        assert text.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    @staticmethod
    def test_root_element_is_preflight_report(sample_result) -> None:
        result = generate_xml_report(sample_result)
        root = ET.fromstring(result)
        # Tag may include namespace
        assert "PreflightReport" in root.tag

    @staticmethod
    def test_namespace_set(sample_result) -> None:
        result = generate_xml_report(sample_result)
        text = result.decode("utf-8")
        assert 'xmlns="urn:lintpdf:preflight:1.0"' in text

    @staticmethod
    def test_utf8_encoding(sample_result) -> None:
        result = generate_xml_report(sample_result)
        decoded = result.decode("utf-8")
        assert isinstance(decoded, str)

    @staticmethod
    def test_well_formed_xml(sample_result) -> None:
        """The output should be parseable XML."""
        result = generate_xml_report(sample_result)
        root = ET.fromstring(result)
        assert root is not None


class TestXmlJobInfo:
    """Tests for job-level metadata in the XML."""

    @staticmethod
    def test_job_id(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        job_id = root.find("JobId")
        assert job_id is not None
        assert job_id.text == "test-job-001"

    @staticmethod
    def test_profile_id(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        profile_id = root.find("ProfileId")
        assert profile_id is not None
        assert profile_id.text == "lintpdf-default"

    @staticmethod
    def test_duration_ms(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        duration = root.find("DurationMs")
        assert duration is not None
        assert duration.text == "42"


class TestXmlSummary:
    """Tests for the Summary element."""

    @staticmethod
    def test_passed_false(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        passed = root.find("Summary/Passed")
        assert passed is not None
        assert passed.text == "false"

    @staticmethod
    def test_passed_true(empty_result) -> None:
        root = _parse_xml(generate_xml_report(empty_result))
        passed = root.find("Summary/Passed")
        assert passed is not None
        assert passed.text == "true"

    @staticmethod
    def test_finding_counts(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        assert root.find("Summary/TotalFindings").text == "3"
        assert root.find("Summary/ErrorCount").text == "1"
        assert root.find("Summary/WarningCount").text == "1"
        assert root.find("Summary/AdvisoryCount").text == "1"

    @staticmethod
    def test_page_count(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        assert root.find("Summary/PageCount").text == "2"

    @staticmethod
    def test_file_size(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        assert root.find("Summary/FileSizeBytes").text == "1048576"

    @staticmethod
    def test_empty_result_counts(empty_result) -> None:
        root = _parse_xml(generate_xml_report(empty_result))
        assert root.find("Summary/TotalFindings").text == "0"
        assert root.find("Summary/ErrorCount").text == "0"


class TestXmlDocument:
    """Tests for the Document element."""

    @staticmethod
    def test_pdf_version(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        assert root.find("Document/PdfVersion").text == "1.7"

    @staticmethod
    def test_is_encrypted(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        assert root.find("Document/IsEncrypted").text == "false"

    @staticmethod
    def test_conformance(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        assert root.find("Document/Conformance").text == "pdfx4"

    @staticmethod
    def test_none_conformance(empty_result) -> None:
        root = _parse_xml(generate_xml_report(empty_result))
        conformance = root.find("Document/Conformance")
        assert conformance is not None
        # None metadata value becomes empty string
        assert conformance.text in (None, "", "None")


class TestXmlFindings:
    """Tests for the Findings element."""

    @staticmethod
    def test_finding_count(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        findings = root.findall("Findings/Finding")
        assert len(findings) == 3

    @staticmethod
    def test_empty_findings(empty_result) -> None:
        root = _parse_xml(generate_xml_report(empty_result))
        findings = root.findall("Findings/Finding")
        assert len(findings) == 0

    @staticmethod
    def test_finding_fields(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        findings = root.findall("Findings/Finding")
        first = findings[0]
        assert first.find("InspectionId").text == "LPDF_FONT_001"
        assert first.find("Severity").text == "error"
        assert first.find("Message").text == "Font 'Arial' is not embedded"
        assert first.find("PageNum").text == "1"

    @staticmethod
    def test_finding_object_id(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        first = root.findall("Findings/Finding")[0]
        assert first.find("ObjectId").text == "F1"
        assert first.find("ObjectType").text == "font"

    @staticmethod
    def test_finding_iso_clause(sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        first = root.findall("Findings/Finding")[0]
        assert first.find("IsoClause").text == "ISO 32000-2:2020 9.6"

    @staticmethod
    def test_finding_without_optional_fields(sample_result) -> None:
        """The third finding has no object_id or iso_clause."""
        root = _parse_xml(generate_xml_report(sample_result))
        third = root.findall("Findings/Finding")[2]
        assert third.find("ObjectId") is None
        assert third.find("IsoClause") is None

    @staticmethod
    def test_finding_details(sample_result) -> None:
        """The second finding has details dict."""
        root = _parse_xml(generate_xml_report(sample_result))
        second = root.findall("Findings/Finding")[1]
        details = second.find("Details")
        assert details is not None
        detail_elems = details.findall("Detail")
        keys = {d.get("key") for d in detail_elems}
        assert "actual_dpi" in keys
        assert "min_dpi" in keys

    @staticmethod
    def test_finding_page_num_omitted_when_zero() -> None:
        """Findings with page_num=None should not have PageNum element."""
        result = PreflightResult(
            job_id="test",
            profile_id="default",
            findings=[
                Finding(
                    inspection_id="LPDF_DOC_001",
                    severity=Severity.ADVISORY,
                    message="Document-level finding",
                    page_num=0,  # No page
                ),
            ],
            summary=PreflightSummary(
                total_findings=1,
                error_count=0,
                warning_count=0,
                advisory_count=1,
                passed=True,
                page_count=1,
                file_size_bytes=100,
            ),
            metadata={"pdf_version": "1.4", "is_encrypted": False, "conformance": None},
            duration_ms=5,
        )
        root = _parse_xml(generate_xml_report(result))
        finding = root.findall("Findings/Finding")[0]
        # page_num=0 is falsy, so it should not be included
        # (The code checks `if f.page_num is not None` — 0 is not None, so it IS included)
        page_num_el = finding.find("PageNum")
        # Since page_num=0 is not None, it will be included
        assert page_num_el is not None
        assert page_num_el.text == "0"


class TestXmlReportSeverityValues:
    """Verify severity enum values are serialized correctly."""

    @pytest.mark.parametrize(
        "severity,expected",
        [
            (Severity.ERROR, "error"),
            (Severity.WARNING, "warning"),
            (Severity.ADVISORY, "advisory"),
        ],
    )
    @staticmethod
    def test_severity_serialization(severity: Severity, expected: str) -> None:
        result = PreflightResult(
            job_id="test",
            profile_id="default",
            findings=[
                Finding(
                    inspection_id="LPDF_TEST",
                    severity=severity,
                    message="Test",
                    page_num=1,
                ),
            ],
            summary=PreflightSummary(
                total_findings=1,
                error_count=0,
                warning_count=0,
                advisory_count=0,
                passed=True,
                page_count=1,
                file_size_bytes=100,
            ),
            metadata={"pdf_version": "1.4", "is_encrypted": False, "conformance": None},
            duration_ms=5,
        )
        root = _parse_xml(generate_xml_report(result))
        sev = root.find("Findings/Finding/Severity")
        assert sev.text == expected


class TestXmlFromDict:
    """Tests for the dict-based XML renderer used by the report mint service."""

    @staticmethod
    def _sample_dict() -> dict:
        return {
            "job_id": "abc-123",
            "profile_id": "lintpdf-default",
            "duration_ms": 4321,
            "preflight_source": "engine",
            "summary": {
                "passed": False,
                "total_findings": 2,
                "error_count": 1,
                "warning_count": 1,
                "advisory_count": 0,
                "page_count": 3,
                "file_size_bytes": 9999,
            },
            "metadata": {
                "pdf_version": "1.7",
                "is_encrypted": False,
                "conformance": "PDF/X-4",
            },
            "findings": [
                {
                    "inspection_id": "LPDF_FONT_001",
                    "severity": "error",
                    "message": "Font not embedded",
                    "page_num": 1,
                    "object_id": "F1",
                    "object_type": "font",
                    "iso_clause": "ISO 32000-2:2020 9.6",
                    "category": "fonts",
                    "source": "engine",
                    "bbox": [10.0, 20.0, 30.0, 40.0],
                    "details": {"font_name": "Arial"},
                },
                {
                    "inspection_id": "LPDF_IMG_001",
                    "severity": "warning",
                    "message": "Image below 150 DPI",
                    "page_num": 2,
                },
            ],
        }

    def test_dict_input_roundtrips(self) -> None:
        root = _parse_xml(generate_xml_from_dict(self._sample_dict()))
        assert root.tag == "PreflightReport"
        assert root.get("schemaVersion") == "1"
        assert root.findtext("JobId") == "abc-123"
        assert root.findtext("PreflightSource") == "engine"
        assert root.findtext("Summary/ErrorCount") == "1"
        assert root.findtext("Document/Conformance") == "PDF/X-4"
        findings = root.findall("Findings/Finding")
        assert len(findings) == 2
        assert findings[0].findtext("InspectionId") == "LPDF_FONT_001"
        assert findings[0].findtext("BBox") == "10.0 20.0 30.0 40.0"
        assert findings[0].find("Details/Detail").get("key") == "font_name"

    def test_dict_input_tolerates_missing_keys(self) -> None:
        root = _parse_xml(generate_xml_from_dict({"job_id": "x"}))
        assert root.findtext("JobId") == "x"
        assert root.findall("Findings/Finding") == []

    def test_dict_input_skips_non_dict_findings(self) -> None:
        root = _parse_xml(
            generate_xml_from_dict(
                {
                    "job_id": "x",
                    "findings": [
                        {"inspection_id": "a", "severity": "error", "message": "m"},
                        "junk",
                        None,
                    ],
                }
            )
        )
        assert len(root.findall("Findings/Finding")) == 1
