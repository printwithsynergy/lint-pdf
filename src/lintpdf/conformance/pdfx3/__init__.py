"""PDF/X-3 Conformance Validator (ISO 15930-6:2003).

PDF/X-3 allows ICC-based color management including ICC-based RGB.
Unlike PDF/X-1a, Lab color space is also permitted.
Transparency is still prohibited (same as X-1a).

Usage:
    validator = PdfX3Validator()
    findings = validator.validate(document, events)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.conformance.base import BaseConformanceValidator
from lintpdf.conformance.pdfx3._color import validate_color
from lintpdf.conformance.pdfx3._font import validate_fonts
from lintpdf.conformance.pdfx3._metadata import validate_metadata
from lintpdf.conformance.pdfx3._output_intent import validate_output_intent
from lintpdf.conformance.pdfx3._restrictions import validate_restrictions
from lintpdf.conformance.pdfx3._transparency import validate_transparency

if TYPE_CHECKING:
    from lintpdf.analyzers.finding import Finding
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


class PdfX3Validator(BaseConformanceValidator):
    """PDF/X-3 (ISO 15930-6:2003) conformance validator.

    Runs all sub-validators and aggregates findings.
    """

    def validate(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        analyzer_findings: list[Finding] | None = None,
    ) -> list[Finding]:
        """Run all PDF/X-3 conformance checks."""
        findings: list[Finding] = []
        findings.extend(validate_metadata(document))
        findings.extend(validate_output_intent(document))
        findings.extend(validate_color(document, events))
        findings.extend(validate_fonts(document))
        findings.extend(validate_transparency(document, events))
        findings.extend(validate_restrictions(document, events))
        return findings
