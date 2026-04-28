"""External preflight-report import package.

Parsers in this package translate third-party preflight output
(PitStop XML, callas JSON/XML, Acrobat Preflight XML, or the
LintPDF-native JSON schema) into the engine's internal
:class:`~lintpdf.analyzers.finding.Finding` objects, so imported
findings flow through the same report/viewer pipeline as
engine-produced findings.
"""

from __future__ import annotations

from .acrobat import AcrobatXmlParser
from .base import ExternalReportParser, ImportedReport, ParserError
from .callas import CallasJsonParser, CallasXmlParser
from .custom import CustomMappingParser
from .detect import detect_format, parse_external_report
from .lintpdf_native import LintpdfNativeParser
from .pitstop import PitStopXmlParser

__all__ = [
    "AcrobatXmlParser",
    "CallasJsonParser",
    "CallasXmlParser",
    "CustomMappingParser",
    "ExternalReportParser",
    "ImportedReport",
    "LintpdfNativeParser",
    "ParserError",
    "PitStopXmlParser",
    "detect_format",
    "parse_external_report",
]
