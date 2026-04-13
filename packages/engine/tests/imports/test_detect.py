"""Tests for external-report format auto-detection."""

from __future__ import annotations

import json

import pytest

from lintpdf.imports.base import ParserError
from lintpdf.imports.detect import detect_format, parse_external_report, parser_for_format


def test_detect_lintpdf_native() -> None:
    payload = json.dumps({"schema_version": "1", "findings": []}).encode("utf-8")
    assert detect_format(payload) == "lintpdf_json"


def test_detect_callas_json() -> None:
    payload = json.dumps(
        {
            "pdfToolboxVersion": "13.2",
            "profile": "PDF/X-4",
            "hits": [],
        }
    ).encode("utf-8")
    assert detect_format(payload) == "callas_json"


def test_detect_pitstop_by_root() -> None:
    assert (
        detect_format(b'<?xml version="1.0"?>\n<PitStopReport><Results/></PitStopReport>')
        == "pitstop_xml"
    )


def test_detect_pitstop_by_hit_fallback() -> None:
    assert (
        detect_format(b'<?xml version="1.0"?>\n<Root><Results><Hit/></Results></Root>')
        == "pitstop_xml"
    )


def test_detect_callas_xml() -> None:
    assert (
        detect_format(b'<?xml version="1.0"?>\n<preflight_report><hit/></preflight_report>')
        == "callas_xml"
    )


def test_detect_acrobat() -> None:
    assert detect_format(b'<?xml version="1.0"?>\n<Preflight><Hits/></Preflight>') == "acrobat_xml"


def test_detect_empty_payload_rejected() -> None:
    with pytest.raises(ParserError):
        detect_format(b"   ")


def test_detect_unrecognised_json() -> None:
    with pytest.raises(ParserError):
        detect_format(b'{"totally": "unknown shape"}')


def test_detect_unrecognised_xml() -> None:
    with pytest.raises(ParserError):
        detect_format(b'<?xml version="1.0"?>\n<Mystery><Node/></Mystery>')


def test_parser_for_format_unknown() -> None:
    with pytest.raises(ParserError):
        parser_for_format("bogus")


def test_parse_external_report_auto_detects_and_parses() -> None:
    payload = json.dumps(
        {
            "schema_version": "1",
            "findings": [{"severity": "error", "message": "hi"}],
        }
    ).encode("utf-8")
    report, fmt = parse_external_report(payload)
    assert fmt == "lintpdf_json"
    assert len(report.findings) == 1
    assert report.findings[0].message == "hi"


def test_parse_external_report_honors_explicit_format() -> None:
    payload = json.dumps(
        {
            "schema_version": "1",
            "findings": [{"severity": "error", "message": "hi"}],
        }
    ).encode("utf-8")
    report, fmt = parse_external_report(payload, fmt="lintpdf_json")
    assert fmt == "lintpdf_json"
    assert len(report.findings) == 1
