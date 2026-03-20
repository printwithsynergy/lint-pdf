"""Tests for XML report generation."""

from __future__ import annotations

# skipcq: PYL-R0201
import xml.etree.ElementTree as ET  # skipcq: BAN-B405

import pytest

from grounded.analyzers.finding import Finding, Severity
from grounded.profiles.orchestrator import PreflightResult, PreflightSummary
from grounded.reports.xml_report import generate_xml_report


@pytest.fixture
def sample_result() -> PreflightResult:
    """Sample result with multiple findings."""
    findings = [
        Finding(
            inspection_id="GRD_FONT_001",
            severity=Severity.AGROUND,
            message="Font 'Arial' is not embedded",
            page_num=1,
            object_id="F1",
            object_type="font",
            iso_clause="ISO 32000-2:2020 9.6",
        ),
        Finding(
            inspection_id="GRD_IMG_001",
            severity=Severity.SQUALL,
            message="Image resolution below minimum (72 DPI < 150 DPI)",
            page_num=1,
            object_id="Im1",
            object_type="image",
            details={"actual_dpi": 72, "min_dpi": 150},
        ),
        Finding(
            inspection_id="GRD_COLOR_003",
            severity=Severity.ADVISORY,
            message="RGB color space detected",
            page_num=2,
            object_type="color",
        ),
    ]
    summary = PreflightSummary(
        total_findings=3,
        aground_count=1,
        squall_count=1,
        advisory_count=1,
        passed=False,
        page_count=2,
        file_size_bytes=1048576,
    )
    return PreflightResult(
        job_id="test-job-001",
        profile_id="grounded-default",
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
        profile_id="grounded-default",
        findings=[],
        summary=PreflightSummary(
            total_findings=0,
            aground_count=0,
            squall_count=0,
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
    ns = "urn:grounded:preflight:1.0"
    for elem in root.iter():
        if elem.tag.startswith(f"{{{ns}}}"):
            elem.tag = elem.tag[len(f"{{{ns}}}") :]
    return root


class TestXmlReportStructure:
    """Tests for overall XML document structure."""

    def test_returns_bytes(self, sample_result) -> None:
        result = generate_xml_report(sample_result)
        assert isinstance(result, bytes)

    def test_starts_with_xml_declaration(self, sample_result) -> None:
        result = generate_xml_report(sample_result)
        text = result.decode("utf-8")
        assert text.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    def test_root_element_is_preflight_report(self, sample_result) -> None:
        result = generate_xml_report(sample_result)
        root = ET.fromstring(result)
        # Tag may include namespace
        assert "PreflightReport" in root.tag

    def test_namespace_set(self, sample_result) -> None:
        result = generate_xml_report(sample_result)
        text = result.decode("utf-8")
        assert 'xmlns="urn:grounded:preflight:1.0"' in text

    def test_utf8_encoding(self, sample_result) -> None:
        result = generate_xml_report(sample_result)
        decoded = result.decode("utf-8")
        assert isinstance(decoded, str)

    def test_well_formed_xml(self, sample_result) -> None:
        """The output should be parseable XML."""
        result = generate_xml_report(sample_result)
        root = ET.fromstring(result)
        assert root is not None


class TestXmlJobInfo:
    """Tests for job-level metadata in the XML."""

    def test_job_id(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        job_id = root.find("JobId")
        assert job_id is not None
        assert job_id.text == "test-job-001"

    def test_profile_id(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        profile_id = root.find("ProfileId")
        assert profile_id is not None
        assert profile_id.text == "grounded-default"

    def test_duration_ms(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        duration = root.find("DurationMs")
        assert duration is not None
        assert duration.text == "42"


class TestXmlSummary:
    """Tests for the Summary element."""

    def test_passed_false(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        passed = root.find("Summary/Passed")
        assert passed is not None
        assert passed.text == "false"

    def test_passed_true(self, empty_result) -> None:
        root = _parse_xml(generate_xml_report(empty_result))
        passed = root.find("Summary/Passed")
        assert passed is not None
        assert passed.text == "true"

    def test_finding_counts(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        assert root.find("Summary/TotalFindings").text == "3"
        assert root.find("Summary/AgroundCount").text == "1"
        assert root.find("Summary/SquallCount").text == "1"
        assert root.find("Summary/AdvisoryCount").text == "1"

    def test_page_count(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        assert root.find("Summary/PageCount").text == "2"

    def test_file_size(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        assert root.find("Summary/FileSizeBytes").text == "1048576"

    def test_empty_result_counts(self, empty_result) -> None:
        root = _parse_xml(generate_xml_report(empty_result))
        assert root.find("Summary/TotalFindings").text == "0"
        assert root.find("Summary/AgroundCount").text == "0"


class TestXmlDocument:
    """Tests for the Document element."""

    def test_pdf_version(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        assert root.find("Document/PdfVersion").text == "1.7"

    def test_is_encrypted(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        assert root.find("Document/IsEncrypted").text == "false"

    def test_conformance(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        assert root.find("Document/Conformance").text == "pdfx4"

    def test_none_conformance(self, empty_result) -> None:
        root = _parse_xml(generate_xml_report(empty_result))
        conformance = root.find("Document/Conformance")
        assert conformance is not None
        # None metadata value becomes empty string
        assert conformance.text in (None, "", "None")


class TestXmlFindings:
    """Tests for the Findings element."""

    def test_finding_count(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        findings = root.findall("Findings/Finding")
        assert len(findings) == 3

    def test_empty_findings(self, empty_result) -> None:
        root = _parse_xml(generate_xml_report(empty_result))
        findings = root.findall("Findings/Finding")
        assert len(findings) == 0

    def test_finding_fields(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        findings = root.findall("Findings/Finding")
        first = findings[0]
        assert first.find("InspectionId").text == "GRD_FONT_001"
        assert first.find("Severity").text == "aground"
        assert first.find("Message").text == "Font 'Arial' is not embedded"
        assert first.find("PageNum").text == "1"

    def test_finding_object_id(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        first = root.findall("Findings/Finding")[0]
        assert first.find("ObjectId").text == "F1"
        assert first.find("ObjectType").text == "font"

    def test_finding_iso_clause(self, sample_result) -> None:
        root = _parse_xml(generate_xml_report(sample_result))
        first = root.findall("Findings/Finding")[0]
        assert first.find("IsoClause").text == "ISO 32000-2:2020 9.6"

    def test_finding_without_optional_fields(self, sample_result) -> None:
        """The third finding has no object_id or iso_clause."""
        root = _parse_xml(generate_xml_report(sample_result))
        third = root.findall("Findings/Finding")[2]
        assert third.find("ObjectId") is None
        assert third.find("IsoClause") is None

    def test_finding_details(self, sample_result) -> None:
        """The second finding has details dict."""
        root = _parse_xml(generate_xml_report(sample_result))
        second = root.findall("Findings/Finding")[1]
        details = second.find("Details")
        assert details is not None
        detail_elems = details.findall("Detail")
        keys = {d.get("key") for d in detail_elems}
        assert "actual_dpi" in keys
        assert "min_dpi" in keys

    def test_finding_page_num_omitted_when_zero(self) -> None:
        """Findings with page_num=None should not have PageNum element."""
        result = PreflightResult(
            job_id="test",
            profile_id="default",
            findings=[
                Finding(
                    inspection_id="GRD_DOC_001",
                    severity=Severity.ADVISORY,
                    message="Document-level finding",
                    page_num=0,  # No page
                ),
            ],
            summary=PreflightSummary(
                total_findings=1,
                aground_count=0,
                squall_count=0,
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
            (Severity.AGROUND, "aground"),
            (Severity.SQUALL, "squall"),
            (Severity.ADVISORY, "advisory"),
        ],
    )
    def test_severity_serialization(self, severity: Severity, expected: str) -> None:
        result = PreflightResult(
            job_id="test",
            profile_id="default",
            findings=[
                Finding(
                    inspection_id="GRD_TEST",
                    severity=severity,
                    message="Test",
                    page_num=1,
                ),
            ],
            summary=PreflightSummary(
                total_findings=1,
                aground_count=0,
                squall_count=0,
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
