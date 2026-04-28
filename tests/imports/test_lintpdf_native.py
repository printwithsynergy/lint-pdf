"""Tests for the LintPDF-native external report parser."""

from __future__ import annotations

import json

import pytest

from lintpdf.imports.base import ParserError
from lintpdf.imports.lintpdf_native import LintpdfNativeParser


def test_parses_full_example() -> None:
    payload = json.dumps(
        {
            "schema_version": "1",
            "source": {
                "tool": "Acme Preflight Pro",
                "version": "12.4.1",
                "profile": "PDF/X-4 Sheetfed CMYK",
            },
            "capabilities": {
                "findings": True,
                "separations": True,
                "tac": False,
                "fonts": True,
            },
            "findings": [
                {
                    "inspection_id": "ACME-IMG-LOWRES",
                    "severity": "error",
                    "message": "Image resolution below 300 dpi threshold",
                    "page_num": 3,
                    "bbox": [72.0, 72.0, 216.0, 216.0],
                    "object_id": "Im7",
                    "object_type": "image",
                    "iso_clause": "PDF/X-4 \u00a76.2.3",
                    "category": "image",
                    "details": {"effective_resolution_dpi": 144},
                },
                {
                    "inspection_id": "ACME-FONT-NOTEMBED",
                    "severity": "error",
                    "message": "Font 'Helvetica' is not embedded",
                    "page_num": 0,
                    "category": "font",
                    "details": {"font_name": "Helvetica"},
                },
            ],
        }
    ).encode("utf-8")

    report = LintpdfNativeParser().parse(payload)

    assert len(report.findings) == 2
    first = report.findings[0]
    assert first.severity.value == "error"
    assert first.page_num == 3
    assert first.bbox == (72.0, 72.0, 216.0, 216.0)
    assert first.object_id == "Im7"
    assert first.source == "external:lintpdf"
    assert first.inspection_id.startswith("EXT-LPDF-")
    assert "ACME-IMG-LOWRES" in first.inspection_id

    # Capabilities projected from the payload.
    assert report.capabilities["findings"] is True
    assert report.capabilities["separations"] is True
    assert report.capabilities["tac"] is False
    assert report.capabilities["fonts"] is True

    # Source metadata retained verbatim (with schema_version fallback).
    assert report.source_metadata["tool"] == "Acme Preflight Pro"
    assert report.source_metadata["schema_version"] == "1"


def test_empty_findings_still_marks_capability() -> None:
    payload = json.dumps({"schema_version": "1", "findings": []}).encode("utf-8")
    report = LintpdfNativeParser().parse(payload)
    assert report.findings == []
    assert report.capabilities["findings"] is True


def test_unknown_severity_falls_back_to_warning() -> None:
    payload = json.dumps(
        {
            "schema_version": "1",
            "findings": [
                {"severity": "fatal-ish", "message": "Something odd"},
            ],
        }
    ).encode("utf-8")
    report = LintpdfNativeParser().parse(payload)
    assert len(report.findings) == 1
    assert report.findings[0].severity.value == "warning"


def test_missing_message_drops_row() -> None:
    payload = json.dumps(
        {
            "findings": [
                {"severity": "error"},
                {"severity": "error", "message": "keep me"},
            ],
        }
    ).encode("utf-8")
    report = LintpdfNativeParser().parse(payload)
    assert len(report.findings) == 1
    assert report.findings[0].message == "keep me"


def test_non_object_root_rejected() -> None:
    with pytest.raises(ParserError):
        LintpdfNativeParser().parse(b"[]")


def test_invalid_json_rejected() -> None:
    with pytest.raises(ParserError):
        LintpdfNativeParser().parse(b"not-json")


def test_findings_must_be_array() -> None:
    payload = json.dumps({"findings": {}}).encode("utf-8")
    with pytest.raises(ParserError):
        LintpdfNativeParser().parse(payload)
