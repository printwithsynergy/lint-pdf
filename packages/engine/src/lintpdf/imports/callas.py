"""Parsers for callas pdfToolbox preflight reports (JSON and XML).

pdfToolbox supports several export formats; the two most common are:

- **JSON report** — emitted by ``pdfToolbox --report=JSON``. Top-level
  object with ``hits`` (or ``results``) array. Each hit carries
  ``severity``, ``comment`` / ``message``, ``rule_id``, ``page``
  (1-indexed), and ``geometry.bbox`` (``[x0, y0, x1, y1]`` in PDF points).

- **XML report** — ``<preflight_report>`` root with ``<hit>`` children
  following the same field layout under XML element names.

Both parsers share the finding-building helper
:meth:`_build_finding` below to keep behaviour consistent.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any

from ..analyzers.finding import Finding, Severity
from .base import ExternalReportParser, ImportedReport, ParserError, normalize_severity


class CallasJsonParser(ExternalReportParser):
    """Parse callas pdfToolbox JSON preflight reports."""

    format = "callas_json"
    version = "1"

    def parse(self, payload: bytes) -> ImportedReport:  # noqa: D401
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParserError(f"callas JSON report is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ParserError("callas JSON report must be a JSON object")

        report = self._new_report()
        report.mark_capability("findings", True)
        report.mark_capability("metadata", True)
        report.source_metadata = {
            "tool": "callas pdfToolbox",
            "version": _as_str(data.get("version") or data.get("pdfToolboxVersion")),
            "profile": _as_str(data.get("profile") or data.get("profile_name")),
            "report_date": _as_str(data.get("report_date") or data.get("date")),
        }

        hits: list[Any] = (
            data.get("hits")
            or data.get("results")
            or data.get("findings")
            or []
        )
        if not isinstance(hits, list):
            raise ParserError("callas JSON: 'hits' must be an array")

        for hit in hits:
            if not isinstance(hit, dict):
                continue
            finding = _build_finding_from_dict(hit)
            if finding is not None:
                report.findings.append(finding)

        # callas reports frequently include a summary of separations.
        if any(k in data for k in ("separations", "inks", "colorants")):
            report.mark_capability("separations", True)

        return report


class CallasXmlParser(ExternalReportParser):
    """Parse callas pdfToolbox XML preflight reports."""

    format = "callas_xml"
    version = "1"

    def parse(self, payload: bytes) -> ImportedReport:  # noqa: D401
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise ParserError(f"callas XML report is not well-formed: {exc}") from exc

        report = self._new_report()
        report.mark_capability("findings", True)
        report.mark_capability("metadata", True)

        meta: dict[str, str] = {"tool": "callas pdfToolbox"}
        for key in ("version", "profile", "report_date", "file_name"):
            node = root.find(f".//{key}")
            if node is not None and node.text:
                meta[key] = node.text.strip()
        report.source_metadata = meta

        for hit in root.iter("hit"):
            finding = _build_finding_from_element(hit)
            if finding is not None:
                report.findings.append(finding)

        # Some callas XML profiles emit a ``<separations>`` block.
        if root.find(".//separations") is not None or root.find(".//inks") is not None:
            report.mark_capability("separations", True)

        return report


# ---------------------------------------------------------------------------


def _build_finding_from_dict(hit: dict[str, Any]) -> Finding | None:
    severity_raw = hit.get("severity") or hit.get("level") or hit.get("type")
    severity = Severity(normalize_severity(severity_raw))

    message = _as_str(
        hit.get("comment")
        or hit.get("message")
        or hit.get("description")
        or hit.get("text")
    )
    if not message:
        return None

    rule_id = _as_str(hit.get("rule_id") or hit.get("id") or hit.get("check_id"))
    inspection_id = f"EXT-CALLAS-{rule_id or f'{abs(hash(message)) % 100000:05d}'}"

    page_num = 0
    for key in ("page", "pageNumber", "page_number"):
        value = hit.get(key)
        if isinstance(value, int):
            page_num = value
            break
        if isinstance(value, str) and value.strip().isdigit():
            page_num = int(value.strip())
            break

    bbox = _bbox_from_dict(hit.get("geometry"))
    if bbox is None:
        bbox = _bbox_from_dict(hit.get("bbox"))
    if bbox is None and isinstance(hit.get("box"), list):
        bbox = _bbox_from_list(hit["box"])

    object_id = _as_str(hit.get("object_id") or hit.get("pdf_object_id"))
    object_type = _as_str(hit.get("object_type"))
    iso_clause = _as_str(hit.get("iso") or hit.get("iso_clause")) or ""
    category = _as_str(hit.get("category")) or "callas"

    return Finding(
        inspection_id=inspection_id,
        severity=severity,
        message=message,
        page_num=page_num,
        details={"callas_raw_severity": _as_str(severity_raw) or ""},
        iso_clause=iso_clause,
        object_id=object_id,
        object_type=object_type,
        bbox=bbox,
        source="external:callas",
        category=category,
    )


def _build_finding_from_element(hit: ET.Element) -> Finding | None:
    def text(tag: str) -> str | None:
        node = hit.find(tag)
        if node is not None and node.text:
            return node.text.strip()
        return None

    message = text("comment") or text("message") or text("description")
    if not message:
        return None

    severity = Severity(normalize_severity(text("severity") or hit.get("severity")))
    rule_id = text("rule_id") or text("id") or hit.get("id") or ""
    inspection_id = f"EXT-CALLAS-{rule_id or f'{abs(hash(message)) % 100000:05d}'}"

    page_num = 0
    page_node = hit.find("page")
    if page_node is None:
        page_node = hit.find("pageNumber")
    if page_node is not None and page_node.text:
        try:
            page_num = int(page_node.text.strip())
        except ValueError:
            page_num = 0

    bbox: tuple[float, float, float, float] | None = None
    bbox_node = hit.find("bbox")
    if bbox_node is None:
        bbox_node = hit.find("geometry/bbox")
    if bbox_node is not None:
        if bbox_node.text:
            parts = bbox_node.text.split()
            if len(parts) == 4:
                try:
                    bbox = tuple(float(p) for p in parts)  # type: ignore[assignment]
                except ValueError:
                    bbox = None
        if bbox is None and bbox_node.get("x0") is not None:
            try:
                bbox = (
                    float(bbox_node.get("x0", 0)),
                    float(bbox_node.get("y0", 0)),
                    float(bbox_node.get("x1", 0)),
                    float(bbox_node.get("y1", 0)),
                )
            except ValueError:
                bbox = None

    return Finding(
        inspection_id=inspection_id,
        severity=severity,
        message=message,
        page_num=page_num,
        details={},
        iso_clause=text("iso") or "",
        object_id=text("object_id"),
        object_type=text("object_type"),
        bbox=bbox,
        source="external:callas",
        category=text("category") or "callas",
    )


def _bbox_from_dict(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, dict):
        return None
    if "bbox" in value and isinstance(value["bbox"], list):
        return _bbox_from_list(value["bbox"])
    if all(k in value for k in ("x0", "y0", "x1", "y1")):
        try:
            return (
                float(value["x0"]),
                float(value["y0"]),
                float(value["x1"]),
                float(value["y1"]),
            )
        except (TypeError, ValueError):
            return None
    if all(k in value for k in ("x", "y", "width", "height")):
        try:
            x = float(value["x"])
            y = float(value["y"])
            w = float(value["width"])
            h = float(value["height"])
            return (x, y, x + w, y + h)
        except (TypeError, ValueError):
            return None
    return None


def _bbox_from_list(value: list[Any]) -> tuple[float, float, float, float] | None:
    if len(value) != 4:
        return None
    try:
        return (float(value[0]), float(value[1]), float(value[2]), float(value[3]))
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None
