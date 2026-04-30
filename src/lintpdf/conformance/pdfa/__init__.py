"""PDF/A Conformance Validator (ISO 19005).

Supports PDF/A-1b, PDF/A-2b, and PDF/A-3b validation.

Usage:
    validator = PdfAValidator(level="1b")
    findings = validator.validate(document, events)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.conformance.base import BaseConformanceValidator

if TYPE_CHECKING:
    from lintpdf.analyzers.finding import Finding
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


class PdfAValidator(BaseConformanceValidator):
    """PDF/A conformance validator (ISO 19005)."""

    def __init__(self, level: str = "1b") -> None:
        self.level = level.lower()

    def validate(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        analyzer_findings: list[Finding] | None = None,
    ) -> list[Finding]:
        """Run PDF/A conformance checks for the configured level."""
        from lintpdf.conformance.pdfa._color import validate_color
        from lintpdf.conformance.pdfa._font import validate_fonts
        from lintpdf.conformance.pdfa._metadata import validate_metadata
        from lintpdf.conformance.pdfa._restrictions import validate_restrictions

        findings: list[Finding] = []
        findings.extend(validate_metadata(document, self.level))
        findings.extend(validate_color(document, events, self.level))
        findings.extend(validate_fonts(document, self.level))
        findings.extend(validate_restrictions(document, events, self.level))
        return findings
