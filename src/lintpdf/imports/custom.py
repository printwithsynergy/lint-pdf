"""Tenant-defined custom preflight report parser.

Proprietary or in-house preflight tools produce XML or JSON in shapes
the built-in parsers (PitStop / callas / Acrobat / LintPDF-native)
don't cover. Rather than ship a new parser for every vendor, tenants
define a **mapping**: a small JSON config that tells
:class:`CustomMappingParser` where each field lives in their payload.

Mapping shape
-------------

``format`` — ``"xml"`` or ``"json"``.

``item_selector`` — the location of each finding. For XML it's an
ElementTree-compatible path (e.g. ``"Results/Issue"`` or ``".//Hit"``).
Namespaces are handled by localname, so ``"Results/Issue"`` also
matches ``<ns:Results xmlns:ns="..."><ns:Issue/></ns:Results>``.
For JSON it's a simple dotted path with optional ``[*]`` for array
wildcards and ``[n]`` for a specific index (e.g.
``"results[*].issues[*]"``).

``fields`` — map from canonical finding field to a sub-selector
*relative to each item*. Supported fields:

* ``severity`` — free-form; run through ``severity_map`` then
  :func:`normalize_severity`.
* ``message`` — required; if missing, the finding is dropped.
* ``page`` — integer; non-integers default to ``0``.
* ``bbox`` — list of 4 numbers or a space-separated string.
* ``check_id`` — surfaces in the inspection_id prefix.
* ``object_id`` / ``object_type`` — plumbed straight through.
* ``category``, ``iso_clause`` — optional metadata.

Selector syntax
~~~~~~~~~~~~~~~

* ``"@attr"`` — XML attribute (custom shorthand).
* ``"child/grandchild"`` — XML path relative to item.
* ``"text()"`` — item's own text content.
* ``"key.subkey"`` — JSON dotted path relative to item.
* ``"."`` — the item itself (stringified).

``severity_map`` — dict mapping raw severity values (case-insensitive)
to canonical ``error|warning|advisory``. Unmapped values fall through
to :func:`normalize_severity`.

``default_severity`` — used when no severity field is found at all.
"""

from __future__ import annotations

import contextlib
import json
import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any

from ..analyzers.finding import Finding, Severity
from .base import ExternalReportParser, ImportedReport, ParserError, normalize_severity

if TYPE_CHECKING:
    from collections.abc import Iterable

_CANONICAL_FIELDS: frozenset[str] = frozenset(
    {
        "severity",
        "message",
        "page",
        "bbox",
        "check_id",
        "object_id",
        "object_type",
        "category",
        "iso_clause",
    }
)


class CustomMappingParser(ExternalReportParser):
    """Parse a tenant-defined preflight report via a mapping config."""

    format = "custom"
    version = "1"

    def __init__(self, mapping: dict[str, Any], *, mapping_id: str | None = None):
        self.mapping = mapping
        self.mapping_id = mapping_id or "custom"
        if not isinstance(mapping, dict):
            raise ParserError("Custom mapping must be a JSON object")
        fmt = str(mapping.get("format", "xml")).lower()
        if fmt not in ("xml", "json"):
            raise ParserError(f"Unsupported custom mapping format: {fmt!r}")
        self.payload_format = fmt
        self.item_selector = str(mapping.get("item_selector", "")).strip()
        if not self.item_selector:
            raise ParserError("Custom mapping requires a non-empty 'item_selector'")
        fields = mapping.get("fields") or {}
        if not isinstance(fields, dict):
            raise ParserError("Custom mapping 'fields' must be an object")
        self.fields: dict[str, dict[str, Any]] = {}
        for key, spec in fields.items():
            if key not in _CANONICAL_FIELDS:
                # Ignore unknown field keys — forward-compat with newer UIs.
                continue
            if isinstance(spec, str):
                self.fields[key] = {"selector": spec}
            elif isinstance(spec, dict):
                self.fields[key] = {"selector": str(spec.get("selector", "")).strip(), **spec}
            else:
                raise ParserError(f"Custom mapping field {key!r} must be a string or object")
        self.severity_map: dict[str, str] = {
            str(k).lower(): str(v).lower() for k, v in (mapping.get("severity_map") or {}).items()
        }
        self.default_severity = str(mapping.get("default_severity", "warning")).lower()

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def parse(self, payload: bytes) -> ImportedReport:
        report = self._new_report()
        report.mark_capability("findings", True)
        report.mark_capability("metadata", True)
        report.source_metadata["tool"] = str(self.mapping.get("source_tool") or "Custom Mapping")
        report.source_metadata["mapping_id"] = self.mapping_id

        if self.payload_format == "xml":
            items = self._iter_xml_items(payload)
        else:
            items = self._iter_json_items(payload)

        for item in items:
            finding = self._build_finding(item)
            if finding is not None:
                report.findings.append(finding)

        return report

    # ------------------------------------------------------------------
    # XML
    # ------------------------------------------------------------------

    def _iter_xml_items(self, payload: bytes) -> Iterable[Any]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise ParserError(f"Custom XML report is not well-formed: {exc}") from exc

        # ElementTree's own findall doesn't match namespaced elements unless
        # the selector uses ``{uri}local``. We implement a lightweight
        # localname-matching walker so tenants can write selectors without
        # caring about namespaces.
        segments = _split_xml_path(self.item_selector)
        current: list[ET.Element] = [root]
        for i, seg in enumerate(segments):
            if seg == "":
                # Leading "//": treat as descendant-or-self.
                descendant: list[ET.Element] = []
                for node in current:
                    descendant.extend(node.iter())
                current = descendant
                continue
            nxt: list[ET.Element] = []
            for node in current:
                # First segment can match the root itself when the selector
                # starts with the root tag.
                if i == 0 and _localname(node.tag) == seg:
                    nxt.append(node)
                for child in node:
                    if _localname(child.tag) == seg:
                        nxt.append(child)
            current = nxt
            if not current:
                break
        return current

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def _iter_json_items(self, payload: bytes) -> Iterable[Any]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParserError(f"Custom JSON report is invalid: {exc}") from exc
        return _json_select(data, self.item_selector)

    # ------------------------------------------------------------------
    # Field extraction
    # ------------------------------------------------------------------

    def _build_finding(self, item: Any) -> Finding | None:
        message = self._pick(item, "message")
        if not message:
            return None
        message = message.strip()
        if not message:
            return None

        raw_severity = self._pick(item, "severity") or ""
        severity_str = self.severity_map.get(raw_severity.lower())
        if severity_str is None:
            if raw_severity:
                severity_str = normalize_severity(raw_severity)
            else:
                severity_str = normalize_severity(self.default_severity)
        try:
            severity = Severity(severity_str)
        except ValueError:
            severity = Severity.WARNING

        page_raw = self._pick(item, "page")
        page_num = _coerce_int(page_raw, default=0)

        bbox = _parse_bbox(self._pick(item, "bbox"))

        check_id = self._pick(item, "check_id") or ""
        inspection_id = (
            f"EXT-CUSTOM-{check_id[:40]}"
            if check_id
            else f"EXT-CUSTOM-{abs(hash(message)) % 100000:05d}"
        )

        return Finding(
            inspection_id=inspection_id,
            severity=severity,
            message=message,
            page_num=page_num,
            details={},
            iso_clause=self._pick(item, "iso_clause") or "",
            object_id=self._pick(item, "object_id") or None,
            object_type=self._pick(item, "object_type") or None,
            bbox=bbox,
            source="external:custom",
            category=self._pick(item, "category") or "",
        )

    def _pick(self, item: Any, field: str) -> str | None:
        spec = self.fields.get(field)
        if not spec:
            return None
        selector = spec.get("selector") or ""
        if not selector:
            return None
        if self.payload_format == "xml":
            return _xml_select_text(item, selector)
        return _json_select_text(item, selector)


# ----------------------------------------------------------------------
# XML helpers
# ----------------------------------------------------------------------


def _localname(tag: str) -> str:
    """Return the XML local name, stripping any ``{namespace}`` prefix."""
    if tag.startswith("{"):
        return tag.rsplit("}", 1)[-1]
    return tag


def _split_xml_path(selector: str) -> list[str]:
    """Split an XML item selector into path segments.

    Strips a leading ``"./"`` (self-relative) and turns ``"//"`` into an
    empty segment so the walker knows to do descendant-or-self.
    """
    s = selector.strip()
    if s.startswith("./"):
        s = s[2:]
    s = s.replace("//", "/__DESC__/")
    parts = [p for p in s.split("/") if p != ""]
    # Map our marker back to the empty-segment descendant sentinel.
    out: list[str] = []
    for p in parts:
        if p == "__DESC__":
            out.append("")
        else:
            out.append(p)
    # A selector that starts with "//" should begin with the descendant
    # sentinel so the walker descends from the root.
    if selector.strip().startswith("//") and (not out or out[0] != ""):
        out.insert(0, "")
    return out


_XML_ATTR_RE = re.compile(r"^@([A-Za-z_][\w\-\.]*)$")


def _xml_select_text(node: ET.Element, selector: str) -> str | None:
    """Extract a text value from an XML element using a small selector DSL.

    Supported forms::

        .            -> node's own text
        text()       -> node's own text
        @attr        -> attribute value
        child        -> text of first child with matching localname
        child/@attr  -> attribute on nested child
        child/grand  -> text of grandchild
    """
    s = selector.strip()
    if s in (".", "text()"):
        return _text(node)
    m = _XML_ATTR_RE.match(s)
    if m:
        return node.attrib.get(m.group(1))
    segments = _split_xml_path(s)
    current: list[ET.Element] = [node]
    attr: str | None = None
    for _i, seg in enumerate(segments):
        if seg == "":
            # Descendant sentinel.
            descendant: list[ET.Element] = []
            for n in current:
                descendant.extend(n.iter())
            current = descendant
            continue
        if seg.startswith("@"):
            attr = seg[1:]
            break
        nxt: list[ET.Element] = []
        for n in current:
            for child in n:
                if _localname(child.tag) == seg:
                    nxt.append(child)
                    break  # first match per node
        current = nxt
        if not current:
            break
    if not current:
        return None
    target = current[0]
    if attr is not None:
        return target.attrib.get(attr)
    return _text(target)


def _text(node: ET.Element) -> str | None:
    parts: list[str] = []
    if node.text:
        parts.append(node.text)
    for child in node:
        if child.tail:
            parts.append(child.tail)
    s = "".join(parts).strip()
    return s or None


# ----------------------------------------------------------------------
# JSON helpers
# ----------------------------------------------------------------------


_JSON_TOKEN_RE = re.compile(r"([A-Za-z_][\w\-]*)|\[(\*|-?\d+)\]")


def _tokenize_json_path(path: str) -> list[tuple[str, str]]:
    """Split a JSON dotted/bracketed path into ``(kind, value)`` tokens.

    ``kind`` is one of ``"key"``, ``"index"``, or ``"wildcard"``.
    Examples::

        "results[*].issues[0].text"
        -> [("key","results"),("wildcard","*"),("key","issues"),
            ("index","0"),("key","text")]
    """
    tokens: list[tuple[str, str]] = []
    pos = 0
    # Strip a leading "$" or "." if present.
    if path.startswith("$"):
        path = path[1:]
    if path.startswith("."):
        path = path[1:]
    while pos < len(path):
        if path[pos] == ".":
            pos += 1
            continue
        m = _JSON_TOKEN_RE.match(path, pos)
        if not m:
            raise ParserError(f"Custom JSON selector is malformed at: {path[pos:]!r}")
        if m.group(1):
            tokens.append(("key", m.group(1)))
        else:
            idx = m.group(2)
            tokens.append(("wildcard" if idx == "*" else "index", idx))
        pos = m.end()
    return tokens


def _json_select(data: Any, selector: str) -> list[Any]:
    """Return every value matching ``selector`` against ``data``."""
    s = selector.strip()
    if s in ("", "."):
        return [data]
    try:
        tokens = _tokenize_json_path(s)
    except ParserError:
        raise
    current: list[Any] = [data]
    for kind, val in tokens:
        nxt: list[Any] = []
        for node in current:
            if kind == "key":
                if isinstance(node, dict) and val in node:
                    nxt.append(node[val])
            elif kind == "index":
                if isinstance(node, list):
                    i = int(val)
                    with contextlib.suppress(IndexError):
                        nxt.append(node[i])
            elif kind == "wildcard":
                if isinstance(node, list):
                    nxt.extend(node)
                elif isinstance(node, dict):
                    nxt.extend(node.values())
        current = nxt
        if not current:
            break
    return current


def _json_select_text(item: Any, selector: str) -> str | None:
    """Return the first JSON-selected value, stringified."""
    results = _json_select(item, selector)
    if not results:
        return None
    v = results[0]
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    # A list of primitive numbers/strings is handed to downstream coercers
    # (e.g. ``_parse_bbox``) as a space-joined string so they can apply
    # their own validation. Nested structures keep JSON encoding so we
    # don't silently lose data.
    if isinstance(v, (list, tuple)):
        if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
            return " ".join(str(x) for x in v)
        return json.dumps(v)
    if isinstance(v, dict):
        return json.dumps(v)
    return str(v)


# ----------------------------------------------------------------------
# Value coercion helpers
# ----------------------------------------------------------------------


def _coerce_int(raw: Any, *, default: int = 0) -> int:
    if raw is None:
        return default
    if isinstance(raw, bool):  # bool is int subtype — reject explicitly
        return default
    if isinstance(raw, int):
        return raw
    s = str(raw).strip()
    if not s:
        return default
    # Pull the first integer out of the string (e.g. "Page 12" → 12).
    m = re.search(r"-?\d+", s)
    if not m:
        return default
    try:
        return int(m.group(0))
    except ValueError:
        return default


def _parse_bbox(raw: Any) -> tuple[float, float, float, float] | None:
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)) and len(raw) == 4:
        try:
            return tuple(float(v) for v in raw)  # type: ignore[return-value]
        except (TypeError, ValueError):
            return None
    s = str(raw).strip()
    if not s:
        return None
    # Allow comma- or whitespace-separated forms.
    parts = [p for p in re.split(r"[\s,]+", s) if p]
    if len(parts) != 4:
        return None
    try:
        return tuple(float(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        return None
