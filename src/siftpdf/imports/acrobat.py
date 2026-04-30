"""Parser for Adobe Acrobat Preflight XML reports.

Acrobat Preflight exports a ``<Preflight>`` XML document. Structure
(trimmed for clarity)::

    <Preflight>
      <Status>Error</Status>
      <Summary>
        <Profile>Prepress (PDF/X-1a)</Profile>
        <ReportDate>2024-01-02T10:00:00Z</ReportDate>
      </Summary>
      <Hits>
        <Hit severity="Error" page="3">
          <Description>Image resolution too low</Description>
          <Rule>IMG_RES_LOW</Rule>
          <BBox>72 72 144 144</BBox>
          <ObjectId>Im7</ObjectId>
        </Hit>
        ...
      </Hits>
    </Preflight>

Field names vary across Acrobat versions (older exports use ``<Problem>``
instead of ``<Hit>``). This parser tolerates both.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, ClassVar

from ..analyzers.finding import Finding, Severity
from .base import ExternalReportParser, ImportedReport, ParserError, normalize_severity

if TYPE_CHECKING:
    from collections.abc import Iterator


class AcrobatXmlParser(ExternalReportParser):
    """Parse Adobe Acrobat Preflight XML reports."""

    format = "acrobat_xml"
    version = "1"

    _HIT_TAGS: ClassVar[set[str]] = {"Hit", "Problem", "Issue", "Result"}

    def parse(self, payload: bytes) -> ImportedReport:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise ParserError(f"Acrobat Preflight XML is not well-formed: {exc}") from exc

        report = self._new_report()
        report.mark_capability("findings", True)
        report.mark_capability("metadata", True)

        meta: dict[str, str] = {"tool": "Adobe Acrobat Preflight"}
        for key in ("Profile", "ReportDate", "FileName", "AcrobatVersion"):
            node = root.find(f".//{key}")
            if node is not None and node.text:
                meta[key] = node.text.strip()
        report.source_metadata = meta

        for hit in self._iter_hits(root):
            finding = self._hit_to_finding(hit)
            if finding is not None:
                report.findings.append(finding)

        return report

    # ------------------------------------------------------------------
    def _iter_hits(self, root: ET.Element) -> Iterator[ET.Element]:
        for el in root.iter():
            tag = el.tag.rsplit("}", 1)[-1] if "}" in el.tag else el.tag
            if tag in self._HIT_TAGS:
                yield el

    def _hit_to_finding(self, hit: ET.Element) -> Finding | None:
        # Severity may be an attribute, a child element, or implied by the
        # parent category (<Errors>/<Warnings>/<Infos>).
        severity_raw = hit.get("severity")
        if not severity_raw:
            sev_node = hit.find("Severity")
            if sev_node is not None and sev_node.text:
                severity_raw = sev_node.text
        severity = Severity(normalize_severity(severity_raw))

        message = _first_text(hit, ("Description", "Message", "Text", "Summary"))
        if not message:
            return None

        rule = _first_text(hit, ("Rule", "RuleID", "CheckID", "Code")) or ""
        inspection_id = f"EXT-ACROBAT-{rule or f'{abs(hash(message)) % 100000:05d}'}"

        page_num = 0
        page_attr = hit.get("page")
        if page_attr and page_attr.strip().isdigit():
            page_num = int(page_attr.strip())
        else:
            page_node = hit.find("Page")
            if page_node is None:
                page_node = hit.find("PageNumber")
            if page_node is not None and page_node.text and page_node.text.strip().isdigit():
                page_num = int(page_node.text.strip())

        bbox = _parse_bbox(hit)

        return Finding(
            inspection_id=inspection_id,
            severity=severity,
            message=message,
            page_num=page_num,
            details={},
            iso_clause=_first_text(hit, ("ISO", "Standard")) or "",
            object_id=_first_text(hit, ("ObjectId", "ObjectID", "PDFObjectID")),
            object_type=_first_text(hit, ("ObjectType",)),
            bbox=bbox,
            source="external:acrobat",
            category=_first_text(hit, ("Category", "Group")) or "acrobat",
        )


def _first_text(item: ET.Element, tags: tuple[str, ...]) -> str | None:
    for tag in tags:
        node = item.find(f".//{tag}")
        if node is not None and node.text:
            text = node.text.strip()
            if text:
                return text
    return None


def _parse_bbox(item: ET.Element) -> tuple[float, float, float, float] | None:
    for tag in ("BBox", "BoundingBox", "Rect"):
        node = item.find(f".//{tag}")
        if node is None:
            continue
        if node.text:
            parts = node.text.strip().split()
            if len(parts) == 4:
                try:
                    return tuple(float(p) for p in parts)  # type: ignore[return-value]
                except ValueError:
                    continue
        if all(node.get(k) is not None for k in ("x0", "y0", "x1", "y1")):
            try:
                return (
                    float(node.get("x0", 0)),
                    float(node.get("y0", 0)),
                    float(node.get("x1", 0)),
                    float(node.get("y1", 0)),
                )
            except ValueError:
                continue
    return None
