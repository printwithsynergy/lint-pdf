"""PDF/X-1a Conformance Validator (ISO 15930-4:2003).

Validates a PDF document against PDF/X-1a requirements.
PDF/X-1a is the most restrictive PDF/X standard — no transparency,
no RGB, CMYK+Gray+Spot only, all fonts embedded.

Usage:
    validator = PdfX1aValidator()
    findings = validator.validate(document, events)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.conformance.base import BaseConformanceValidator
from lintpdf.conformance.pdfx1a._color import validate_color
from lintpdf.conformance.pdfx1a._font import validate_fonts
from lintpdf.conformance.pdfx1a._metadata import validate_metadata
from lintpdf.conformance.pdfx1a._output_intent import validate_output_intent
from lintpdf.conformance.pdfx1a._restrictions import validate_restrictions
from lintpdf.conformance.pdfx1a._transparency import validate_transparency

if TYPE_CHECKING:
    from lintpdf.analyzers.finding import Finding
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


class PdfX1aValidator(BaseConformanceValidator):
    """PDF/X-1a (ISO 15930-4:2003) conformance validator."""

    def validate(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        analyzer_findings: list[Finding] | None = None,
    ) -> list[Finding]:
        """Run all PDF/X-1a conformance checks."""
        findings: list[Finding] = []
        findings.extend(validate_metadata(document))
        findings.extend(validate_output_intent(document))
        findings.extend(validate_color(document, events))
        findings.extend(validate_fonts(document))
        findings.extend(validate_transparency(document, events))
        findings.extend(validate_restrictions(document, events))
        return findings
