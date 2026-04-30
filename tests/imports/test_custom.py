"""Tests for the tenant-defined custom mapping parser."""

from __future__ import annotations

import pytest

from lintpdf.imports.base import ParserError
from lintpdf.imports.custom import CustomMappingParser

# ----------------------------------------------------------------------
# XML mappings
# ----------------------------------------------------------------------


XML_PROPRIETARY = b"""<?xml version="1.0" encoding="UTF-8"?>
<PreflightLog>
  <Issues>
    <Issue level="HIGH" page="2" ruleId="IMG_DPI">
      <Description>Image below 300 dpi</Description>
      <Geometry>
        <Box>72 72 216 216</Box>
      </Geometry>
      <Object kind="image">Im3</Object>
      <Category>Images</Category>
    </Issue>
    <Issue level="LOW" page="1" ruleId="FONT_EMBED">
      <Description>Font not embedded</Description>
    </Issue>
    <Issue level="HIGH" page="3">
      <!-- description missing, should be dropped -->
    </Issue>
  </Issues>
</PreflightLog>
"""


def _xml_mapping() -> dict:
    return {
        "format": "xml",
        "item_selector": "Issues/Issue",
        "fields": {
            "severity": {"selector": "@level"},
            "message": {"selector": "Description"},
            "page": {"selector": "@page"},
            "bbox": {"selector": "Geometry/Box"},
            "check_id": {"selector": "@ruleId"},
            "object_id": {"selector": "Object"},
            "object_type": {"selector": "Object/@kind"},
            "category": {"selector": "Category"},
        },
        "severity_map": {"high": "error", "low": "advisory"},
        "default_severity": "warning",
    }


def test_xml_mapping_parses_all_valid_findings() -> None:
    parser = CustomMappingParser(_xml_mapping(), mapping_id="map1")
    report = parser.parse(XML_PROPRIETARY)

    assert len(report.findings) == 2  # third row dropped (no message)

    first = report.findings[0]
    assert first.severity.value == "error"
    assert "300 dpi" in first.message
    assert first.page_num == 2
    assert first.bbox == (72.0, 72.0, 216.0, 216.0)
    assert first.object_id == "Im3"
    assert first.object_type == "image"
    assert first.category == "Images"
    assert first.source == "external:custom"
    assert first.inspection_id.startswith("EXT-CUSTOM-")
    assert "IMG_DPI" in first.inspection_id

    second = report.findings[1]
    assert second.severity.value == "advisory"
    assert second.page_num == 1
    assert second.bbox is None

    assert report.source_metadata["mapping_id"] == "map1"
    assert report.capabilities["findings"] is True


def test_xml_mapping_handles_namespaced_payload() -> None:
    xml = b"""<?xml version="1.0"?>
    <ns:PreflightLog xmlns:ns="urn:example">
      <ns:Issues>
        <ns:Issue level="HIGH" page="4">
          <ns:Description>Namespaced finding</ns:Description>
        </ns:Issue>
      </ns:Issues>
    </ns:PreflightLog>"""
    parser = CustomMappingParser(_xml_mapping())
    report = parser.parse(xml)
    assert len(report.findings) == 1
    assert report.findings[0].message == "Namespaced finding"
    assert report.findings[0].page_num == 4


def test_xml_mapping_with_descendant_selector() -> None:
    xml = b"""<?xml version="1.0"?>
    <root>
      <wrap><nest>
        <Issue level="HIGH"><Description>Deep finding</Description></Issue>
      </nest></wrap>
    </root>"""
    mapping = _xml_mapping()
    mapping["item_selector"] = "//Issue"
    parser = CustomMappingParser(mapping)
    report = parser.parse(xml)
    assert len(report.findings) == 1
    assert report.findings[0].message == "Deep finding"


def test_xml_mapping_rejects_bad_xml() -> None:
    parser = CustomMappingParser(_xml_mapping())
    with pytest.raises(ParserError):
        parser.parse(b"<not-closed>")


def test_xml_mapping_unknown_severity_falls_through_normalize() -> None:
    xml = b"""<?xml version="1.0"?>
    <PreflightLog><Issues>
      <Issue level="fatal"><Description>Fatal issue</Description></Issue>
      <Issue level="note"><Description>Note issue</Description></Issue>
      <Issue level="something-weird"><Description>Unknown severity</Description></Issue>
    </Issues></PreflightLog>"""
    parser = CustomMappingParser(_xml_mapping())
    report = parser.parse(xml)
    assert [f.severity.value for f in report.findings] == [
        "error",  # "fatal" -> normalize_severity -> error
        "advisory",  # "note"  -> normalize_severity -> advisory
        "warning",  # unknown -> normalize_severity fallback
    ]


# ----------------------------------------------------------------------
# JSON mappings
# ----------------------------------------------------------------------


JSON_PROPRIETARY = b"""{
  "scanId": "abc-123",
  "results": [
    {
      "issues": [
        {
          "sev": "blocker",
          "text": "Bleed box missing",
          "loc": {"page": 2, "box": [10, 20, 100, 200]},
          "rule": "BLEED_MISSING",
          "obj": {"id": "P1", "kind": "page"}
        },
        {
          "sev": "info",
          "text": "Color profile present",
          "loc": {"page": 0}
        }
      ]
    },
    {
      "issues": [
        {"sev": "blocker"}
      ]
    }
  ]
}"""


def _json_mapping() -> dict:
    return {
        "format": "json",
        "item_selector": "results[*].issues[*]",
        "fields": {
            "severity": "sev",
            "message": "text",
            "page": "loc.page",
            "bbox": "loc.box",
            "check_id": "rule",
            "object_id": "obj.id",
            "object_type": "obj.kind",
        },
        "severity_map": {"blocker": "error", "info": "advisory"},
    }


def test_json_mapping_extracts_findings() -> None:
    parser = CustomMappingParser(_json_mapping(), mapping_id="jmap")
    report = parser.parse(JSON_PROPRIETARY)

    # Third issue has no text -> dropped.
    assert len(report.findings) == 2

    first = report.findings[0]
    assert first.severity.value == "error"
    assert first.message == "Bleed box missing"
    assert first.page_num == 2
    assert first.bbox == (10.0, 20.0, 100.0, 200.0)
    assert first.object_id == "P1"
    assert first.object_type == "page"
    assert "BLEED_MISSING" in first.inspection_id

    second = report.findings[1]
    assert second.severity.value == "advisory"
    assert second.page_num == 0
    assert second.bbox is None


def test_json_mapping_with_specific_index() -> None:
    mapping = _json_mapping()
    # Only pick the first issue of each result array.
    mapping["item_selector"] = "results[*].issues[0]"
    parser = CustomMappingParser(mapping)
    report = parser.parse(JSON_PROPRIETARY)
    assert len(report.findings) == 1
    assert report.findings[0].message == "Bleed box missing"


def test_json_mapping_rejects_bad_json() -> None:
    parser = CustomMappingParser(_json_mapping())
    with pytest.raises(ParserError):
        parser.parse(b"{not-json")


def test_json_mapping_supports_dollar_prefix() -> None:
    mapping = _json_mapping()
    mapping["item_selector"] = "$.results[*].issues[*]"
    parser = CustomMappingParser(mapping)
    report = parser.parse(JSON_PROPRIETARY)
    assert len(report.findings) == 2


# ----------------------------------------------------------------------
# Mapping validation
# ----------------------------------------------------------------------


def test_mapping_must_be_dict() -> None:
    with pytest.raises(ParserError):
        CustomMappingParser("not a dict")  # type: ignore[arg-type]


def test_mapping_requires_item_selector() -> None:
    with pytest.raises(ParserError):
        CustomMappingParser({"format": "json", "fields": {"message": "msg"}})


def test_mapping_rejects_unknown_format() -> None:
    with pytest.raises(ParserError):
        CustomMappingParser({"format": "yaml", "item_selector": "a", "fields": {"message": "m"}})


def test_mapping_rejects_bad_fields_type() -> None:
    with pytest.raises(ParserError):
        CustomMappingParser({"format": "xml", "item_selector": "x", "fields": "bogus"})
