"""Parser for Enfocus PitStop Pro / Server preflight reports (XML).

PitStop XML has several variants across versions (``PitStopReport``,
``EnfocusReport``, action-list result summaries). All share a common
structure: a top-level ``<Results>`` section containing ``<Error>`` /
``<Warning>`` / ``<Info>`` or ``<ResultItem>`` entries, each with a
severity, message, affected object reference, and optional page + bbox.

This parser walks the tree tolerantly — unknown elements are ignored,
missing page/bbox are allowed, and the severity word is normalised via
:func:`~siftpdf.imports.base.normalize_severity`.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, ClassVar

from ..analyzers.finding import Finding, Severity
from .base import ExternalReportParser, ImportedReport, ParserError, normalize_severity

if TYPE_CHECKING:
    from collections.abc import Iterator


class PitStopXmlParser(ExternalReportParser):
    """Parse Enfocus PitStop Pro / Server XML preflight reports."""

    format = "pitstop_xml"
    version = "1"

    # Elements that we treat as "result" rows regardless of wrapper.
    _RESULT_TAGS: ClassVar[set[str]] = {
        "Error",
        "Warning",
        "Info",
        "Advisory",
        "ResultItem",
        "Result",
        "Hit",
        "Fix",
    }

    def parse(self, payload: bytes) -> ImportedReport:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise ParserError(f"PitStop XML is not well-formed: {exc}") from exc

        report = self._new_report()
        report.mark_capability("findings", True)
        report.mark_capability("metadata", True)

        # Document-level metadata commonly emitted by PitStop.
        meta: dict[str, str] = {}
        keys = ("Profile", "PitStopVersion", "ProfileVersion", "ReportDate", "FileName")
        remaining = set(keys)
        for el in root.iter():
            if not remaining:
                break
            local = self._localname(el.tag)
            if local in remaining and el.text and el.text.strip():
                meta[local] = el.text.strip()
                remaining.discard(local)
        if root.tag:
            meta["RootElement"] = root.tag
        report.source_metadata = {"tool": "Enfocus PitStop", **meta}

        for item in self._iter_result_items(root):
            finding = self._item_to_finding(item)
            if finding is not None:
                report.findings.append(finding)

        return report

    # ------------------------------------------------------------------
    def _iter_result_items(self, root: ET.Element) -> Iterator[ET.Element]:
        """Yield every element in the tree that represents a single result.

        Matches tags by localname so namespaced documents
        (e.g. ``{urn:enfocus}Results``) are handled the same as the plain
        ``<Results>`` variant.
        """
        wrapper_names = {"Results", "ResultSet", "ResultList"}
        results_parents = [el for el in root.iter() if self._localname(el.tag) in wrapper_names]
        if not results_parents:
            results_parents = [root]

        seen: set[int] = set()
        for parent in results_parents:
            for el in parent.iter():
                if id(el) in seen:
                    continue
                tag = self._localname(el.tag)
                if tag in self._RESULT_TAGS:
                    seen.add(id(el))
                    yield el

    def _item_to_finding(self, item: ET.Element) -> Finding | None:
        tag = self._localname(item.tag)
        # Derive severity either from the tag (``<Error>``) or a child
        # ``<Severity>`` element (``<ResultItem><Severity>error</Severity>``).
        severity_raw: str | None = None
        if tag in {"Error", "Warning", "Info", "Advisory"}:
            severity_raw = tag
        else:
            sev_node = item.find("Severity")
            if sev_node is None:
                sev_node = item.find("severity")
            severity_raw = sev_node.text if (sev_node is not None and sev_node.text) else None
        severity = Severity(normalize_severity(severity_raw))

        message = self._first_text(
            item,
            ("Description", "Message", "Text", "Label", "Title"),
        )
        if not message:
            # Unusable row — PitStop sometimes emits empty info rows for
            # grouping; skip silently rather than produce blank findings.
            return None

        inspection_id = (
            self._first_text(
                item,
                ("CheckID", "Check", "Code", "Id", "ID", "RuleID"),
            )
            or f"PITSTOP_{abs(hash(message)) % 100000:05d}"
        )

        category = self._first_text(item, ("Category", "Group")) or "pitstop"

        page_num = 0
        page_node = self._find_descendant(item, ("Page", "PageNumber"))
        if page_node is not None and page_node.text:
            try:
                page_num = int(page_node.text.strip())
            except ValueError:
                page_num = 0

        bbox = self._parse_bbox(item)

        object_id = self._first_text(
            item,
            ("ObjectID", "ObjectId", "PDFObjectID", "ObjectRef"),
        )
        object_type = self._first_text(
            item,
            ("ObjectType", "PDFObjectType", "Type"),
        )

        iso_clause = self._first_text(item, ("ISO", "ISOClause", "Standard")) or ""

        return Finding(
            inspection_id=f"EXT-PS-{inspection_id}",
            severity=severity,
            message=message,
            page_num=page_num,
            details={"raw_tag": tag},
            iso_clause=iso_clause,
            object_id=object_id,
            object_type=object_type,
            bbox=bbox,
            source="external:pitstop",
            category=category,
        )

    # ------------------------------------------------------------------
    def _first_text(self, item: ET.Element, tags: tuple[str, ...]) -> str | None:
        """Return the trimmed text of the first descendant whose localname
        matches one of ``tags``. Walks in caller-specified priority order
        and is namespace-aware."""
        for tag in tags:
            node = self._find_descendant(item, (tag,))
            if node is not None and node.text:
                text = node.text.strip()
                if text:
                    return text
        return None

    def _find_descendant(self, item: ET.Element, tags: tuple[str, ...]) -> ET.Element | None:
        """First descendant (preorder) whose localname matches ``tags``."""
        wanted = set(tags)
        for el in item.iter():
            if el is item:
                continue
            if self._localname(el.tag) in wanted:
                return el
        return None

    def _parse_bbox(self, item: ET.Element) -> tuple[float, float, float, float] | None:
        """Extract a bounding box from any of the common PitStop shapes.

        Supports:
        - ``<BBox>x0 y0 x1 y1</BBox>``
        - ``<BBox llx="0" lly="0" urx="100" ury="100"/>``
        - ``<Rect>0 0 100 100</Rect>``
        - Separate ``<X>``/``<Y>``/``<Width>``/``<Height>`` children.
        """
        for tag in ("BBox", "Rect", "BoundingBox"):
            node = self._find_descendant(item, (tag,))
            if node is None:
                continue
            # Attribute form
            if node.get("llx") is not None and node.get("urx") is not None:
                try:
                    return (
                        float(node.get("llx", 0)),
                        float(node.get("lly", 0)),
                        float(node.get("urx", 0)),
                        float(node.get("ury", 0)),
                    )
                except (TypeError, ValueError):
                    pass
            # Space-separated text form
            if node.text:
                parts = node.text.strip().split()
                if len(parts) == 4:
                    try:
                        return tuple(float(p) for p in parts)  # type: ignore[return-value]
                    except ValueError:
                        pass

        # Split child form
        try:
            x = float(self._first_text(item, ("X",)) or "nan")
            y = float(self._first_text(item, ("Y",)) or "nan")
            w = float(self._first_text(item, ("Width",)) or "nan")
            h = float(self._first_text(item, ("Height",)) or "nan")
        except ValueError:
            return None
        if all(v == v for v in (x, y, w, h)):  # NaN check
            return (x, y, x + w, y + h)
        return None

    @staticmethod
    def _localname(tag: str) -> str:
        """Strip XML namespace prefix from an element tag."""
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag
