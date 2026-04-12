"""Tests for the Enfocus PitStop XML parser."""

from __future__ import annotations

import pytest

from lintpdf.imports.base import ParserError
from lintpdf.imports.pitstop import PitStopXmlParser


PITSTOP_REPORT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<PitStopReport>
  <Header>
    <Profile>PDF/X-4 Sheetfed</Profile>
    <PitStopVersion>2024.1</PitStopVersion>
    <FileName>brochure.pdf</FileName>
  </Header>
  <Results>
    <Error>
      <CheckID>IMG_LOWRES</CheckID>
      <Description>Image resolution below 300 dpi</Description>
      <Category>Images</Category>
      <Page>2</Page>
      <BBox>72 72 216 216</BBox>
      <ObjectID>Im4</ObjectID>
      <ObjectType>image</ObjectType>
      <ISO>PDF/X-4 6.2.3</ISO>
    </Error>
    <Warning>
      <CheckID>FONT_NOEMBED</CheckID>
      <Description>Font not embedded</Description>
      <Page>1</Page>
    </Warning>
    <Info>
      <CheckID>OK</CheckID>
      <Description>Profile applied successfully</Description>
    </Info>
    <Error>
      <!-- Empty/grouping row — must be skipped. -->
    </Error>
  </Results>
</PitStopReport>
"""


def test_parses_enfocus_report() -> None:
    report = PitStopXmlParser().parse(PITSTOP_REPORT_XML)

    assert len(report.findings) == 3  # empty row skipped

    err = report.findings[0]
    assert err.severity.value == "error"
    assert "300 dpi" in err.message
    assert err.page_num == 2
    assert err.bbox == (72.0, 72.0, 216.0, 216.0)
    assert err.object_id == "Im4"
    assert err.object_type == "image"
    assert err.iso_clause == "PDF/X-4 6.2.3"
    assert err.source == "external:pitstop"
    assert err.inspection_id.startswith("EXT-PS-")
    assert "IMG_LOWRES" in err.inspection_id
    assert err.category == "Images"

    warn = report.findings[1]
    assert warn.severity.value == "warning"
    assert warn.page_num == 1

    info = report.findings[2]
    assert info.severity.value == "advisory"

    assert report.capabilities["findings"] is True
    assert report.source_metadata["tool"] == "Enfocus PitStop"
    assert report.source_metadata["Profile"] == "PDF/X-4 Sheetfed"
    assert report.source_metadata["FileName"] == "brochure.pdf"


def test_bbox_attribute_form() -> None:
    xml = b"""<?xml version="1.0"?>
    <Results>
      <Error>
        <Description>Box attr form</Description>
        <Page>1</Page>
        <BBox llx="10" lly="20" urx="100" ury="200"/>
      </Error>
    </Results>"""
    report = PitStopXmlParser().parse(xml)
    assert len(report.findings) == 1
    assert report.findings[0].bbox == (10.0, 20.0, 100.0, 200.0)


def test_malformed_xml_raises_parser_error() -> None:
    with pytest.raises(ParserError):
        PitStopXmlParser().parse(b"<not-closed>")


def test_xml_with_namespace_is_handled() -> None:
    xml = b"""<?xml version="1.0"?>
    <ns:PitStopReport xmlns:ns="urn:enfocus">
      <ns:Results>
        <ns:Error>
          <ns:CheckID>NS_RULE</ns:CheckID>
          <ns:Description>Namespaced rule</ns:Description>
          <ns:Page>4</ns:Page>
        </ns:Error>
      </ns:Results>
    </ns:PitStopReport>"""
    report = PitStopXmlParser().parse(xml)
    assert len(report.findings) == 1
    assert report.findings[0].page_num == 4
    assert "Namespaced rule" in report.findings[0].message
