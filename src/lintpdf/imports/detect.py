"""Auto-detect the format of an uploaded third-party preflight report.

Used when the caller doesn't set ``external_format`` explicitly on a
submission. Sniffs the first few bytes / root element of the payload
and dispatches to the matching parser.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

from .acrobat import AcrobatXmlParser
from .base import ExternalReportParser, ImportedReport, ParserError
from .callas import CallasJsonParser, CallasXmlParser
from .lintpdf_native import LintpdfNativeParser
from .pitstop import PitStopXmlParser

_XML_SIGNATURES = {
    "preflight": AcrobatXmlParser,  # <Preflight>
    "acrobatreport": AcrobatXmlParser,
    "enfocusreport": PitStopXmlParser,  # <EnfocusReport>
    "pitstopreport": PitStopXmlParser,  # <PitStopReport>
    "pitstopprofile": PitStopXmlParser,
    "reports": PitStopXmlParser,  # PitStop often nests under <Reports>
    "preflight_report": CallasXmlParser,  # callas <preflight_report>
    "callasreport": CallasXmlParser,
    "callas": CallasXmlParser,
}


def detect_format(payload: bytes) -> str:
    """Identify the format of a preflight payload.

    Returns the format token (same value persisted to
    ``Job.external_format``). Raises :class:`ParserError` when the
    payload doesn't match any known format.
    """
    stripped = payload.lstrip()
    if not stripped:
        raise ParserError("Preflight report is empty")

    if stripped[:1] == b"{" or stripped[:1] == b"[":
        # JSON — inspect shape to tell callas from LintPDF-native.
        try:
            data = json.loads(stripped.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ParserError(f"JSON preflight report is invalid: {exc}") from exc
        if isinstance(data, dict):
            if "schema_version" in data and "findings" in data:
                return LintpdfNativeParser.format
            if any(k in data for k in ("hits", "results")) and (
                "pdfToolboxVersion" in data or "profile" in data or "profile_name" in data
            ):
                return CallasJsonParser.format
            # Fall back: if it looks like a findings envelope, assume native.
            if "findings" in data or "capabilities" in data:
                return LintpdfNativeParser.format
        raise ParserError("Unrecognised JSON preflight report shape")

    if stripped[:1] == b"<":
        try:
            root = ET.fromstring(stripped)
        except ET.ParseError as exc:
            raise ParserError(f"XML preflight report is not well-formed: {exc}") from exc
        tag = root.tag.rsplit("}", 1)[-1] if "}" in root.tag else root.tag
        match = _XML_SIGNATURES.get(tag.lower())
        if match is not None:
            return match.format
        # Heuristic fallback: look for signature child nodes.
        if root.find(".//Hit") is not None or root.find(".//ResultItem") is not None:
            return PitStopXmlParser.format
        if root.find(".//hit") is not None:
            return CallasXmlParser.format
        if root.find(".//Problem") is not None:
            return AcrobatXmlParser.format
        raise ParserError(f"Unrecognised XML preflight root element: <{tag}>")

    raise ParserError("Preflight report is neither JSON nor XML")


_PARSERS: dict[str, type[ExternalReportParser]] = {
    PitStopXmlParser.format: PitStopXmlParser,
    CallasJsonParser.format: CallasJsonParser,
    CallasXmlParser.format: CallasXmlParser,
    AcrobatXmlParser.format: AcrobatXmlParser,
    LintpdfNativeParser.format: LintpdfNativeParser,
}


def parser_for_format(fmt: str) -> ExternalReportParser:
    """Return a parser instance for the given format token."""
    try:
        return _PARSERS[fmt]()
    except KeyError as exc:
        raise ParserError(f"Unsupported external_format {fmt!r}") from exc


def parse_external_report(payload: bytes, fmt: str | None = None) -> tuple[ImportedReport, str]:
    """Parse a third-party preflight report, auto-detecting format if needed.

    Returns ``(imported_report, resolved_format)``. ``resolved_format`` is
    the caller-supplied ``fmt`` if provided, otherwise the auto-detected
    format token; either way it's what gets persisted to
    ``Job.external_format`` and ``JobImportedReport.format``.
    """
    resolved = fmt or detect_format(payload)
    parser = parser_for_format(resolved)
    report = parser.parse(payload)
    return report, resolved
