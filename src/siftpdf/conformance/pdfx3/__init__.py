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

from siftpdf.conformance.base import BaseConformanceValidator
from siftpdf.conformance.pdfx3._color import validate_color
from siftpdf.conformance.pdfx3._font import validate_fonts
from siftpdf.conformance.pdfx3._metadata import validate_metadata
from siftpdf.conformance.pdfx3._output_intent import validate_output_intent
from siftpdf.conformance.pdfx3._restrictions import validate_restrictions
from siftpdf.conformance.pdfx3._transparency import validate_transparency

if TYPE_CHECKING:
    from siftpdf.analyzers.finding import Finding
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument


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
