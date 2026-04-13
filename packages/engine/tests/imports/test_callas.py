"""Tests for the callas pdfToolbox parsers (JSON + XML)."""

from __future__ import annotations

import json

import pytest

from lintpdf.imports.base import ParserError
from lintpdf.imports.callas import CallasJsonParser, CallasXmlParser

CALLAS_JSON = json.dumps(
    {
        "pdfToolboxVersion": "13.2",
        "profile": "PDF/X-4:2010",
        "report_date": "2026-04-12T00:00:00Z",
        "hits": [
            {
                "rule_id": "CALLAS_IMG_LOWRES",
                "severity": "error",
                "comment": "Image effective resolution 120 dpi",
                "page": 5,
                "geometry": {"bbox": [100, 200, 300, 400]},
                "object_id": "Im2",
                "object_type": "image",
            },
            {
                "rule_id": "CALLAS_FONT_MISSING",
                "severity": "warning",
                "message": "Font may be missing glyphs",
                "page": 1,
            },
        ],
        "separations": ["Cyan", "Magenta", "Yellow", "Black", "PANTONE 185 C"],
    }
).encode("utf-8")


def test_callas_json_full_report() -> None:
    report = CallasJsonParser().parse(CALLAS_JSON)
    assert len(report.findings) == 2

    hit = report.findings[0]
    assert hit.severity.value == "error"
    assert hit.page_num == 5
    assert hit.bbox == (100.0, 200.0, 300.0, 400.0)
    assert hit.object_id == "Im2"
    assert hit.object_type == "image"
    assert hit.source == "external:callas"
    assert hit.inspection_id.startswith("EXT-CALLAS-")
    assert "CALLAS_IMG_LOWRES" in hit.inspection_id

    # Separations presence flips the capability flag.
    assert report.capabilities["separations"] is True
    assert report.capabilities["findings"] is True
    assert report.source_metadata["tool"] == "callas pdfToolbox"
    assert report.source_metadata["version"] == "13.2"


def test_callas_json_invalid_root_type() -> None:
    with pytest.raises(ParserError):
        CallasJsonParser().parse(b"[1, 2, 3]")


def test_callas_json_requires_array_hits() -> None:
    with pytest.raises(ParserError):
        CallasJsonParser().parse(json.dumps({"hits": {"nope": 1}}).encode("utf-8"))


CALLAS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<preflight_report>
  <profile>PDF/X-4</profile>
  <pdfToolboxVersion>13.2</pdfToolboxVersion>
  <hit>
    <rule_id>CALLAS_PX_4</rule_id>
    <severity>error</severity>
    <comment>Output intent missing</comment>
    <page>0</page>
  </hit>
  <hit>
    <rule_id>CALLAS_WARN</rule_id>
    <severity>warning</severity>
    <comment>Trim box not set</comment>
    <page>1</page>
    <geometry>
      <bbox>0 0 612 792</bbox>
    </geometry>
  </hit>
</preflight_report>
"""


def test_callas_xml_full_report() -> None:
    report = CallasXmlParser().parse(CALLAS_XML)
    assert len(report.findings) == 2

    err = report.findings[0]
    assert err.severity.value == "error"
    assert err.page_num == 0  # document-level

    warn = report.findings[1]
    assert warn.severity.value == "warning"
    assert warn.page_num == 1
    assert warn.bbox == (0.0, 0.0, 612.0, 792.0)

    assert report.capabilities["findings"] is True


def test_callas_xml_malformed() -> None:
    with pytest.raises(ParserError):
        CallasXmlParser().parse(b"<preflight_report><hit><severity>")
