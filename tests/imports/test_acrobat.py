"""Tests for the Adobe Acrobat Preflight XML parser."""

from __future__ import annotations

import pytest

from lintpdf.imports.acrobat import AcrobatXmlParser
from lintpdf.imports.base import ParserError

ACROBAT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Preflight>
  <Status>Error</Status>
  <Summary>
    <Profile>Prepress (PDF/X-1a)</Profile>
    <ReportDate>2026-04-12T10:00:00Z</ReportDate>
    <FileName>poster.pdf</FileName>
  </Summary>
  <Hits>
    <Hit severity="Error" page="3">
      <Description>Image resolution too low</Description>
      <Rule>IMG_RES_LOW</Rule>
      <BBox>72 72 144 144</BBox>
      <ObjectId>Im7</ObjectId>
    </Hit>
    <Hit severity="Warning" page="1">
      <Description>Trim box missing</Description>
      <Rule>TRIM_MISSING</Rule>
    </Hit>
    <Problem severity="Info">
      <Description>Legacy Problem-element row</Description>
      <Rule>LEGACY_OK</Rule>
    </Problem>
    <Hit severity="Error">
      <!-- message missing - should be dropped -->
    </Hit>
  </Hits>
</Preflight>
"""


def test_acrobat_report() -> None:
    report = AcrobatXmlParser().parse(ACROBAT_XML)

    assert len(report.findings) == 3

    first = report.findings[0]
    assert first.severity.value == "error"
    assert first.page_num == 3
    assert first.bbox == (72.0, 72.0, 144.0, 144.0)
    assert first.object_id == "Im7"
    assert first.source == "external:acrobat"
    assert first.inspection_id.startswith("EXT-ACROBAT-")
    assert "IMG_RES_LOW" in first.inspection_id

    warn = report.findings[1]
    assert warn.severity.value == "warning"
    assert warn.page_num == 1

    legacy = report.findings[2]
    assert legacy.severity.value == "advisory"
    assert "Legacy" in legacy.message

    assert report.source_metadata["tool"] == "Adobe Acrobat Preflight"
    assert report.source_metadata["Profile"].startswith("Prepress")


def test_bad_xml() -> None:
    with pytest.raises(ParserError):
        AcrobatXmlParser().parse(b"<Preflight><Hits><Hit")
