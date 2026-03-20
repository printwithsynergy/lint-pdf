"""PDF/X-4 Conformance Validator (ISO 15930-7:2010).

Validates a PDF document against the PDF/X-4 standard requirements.
The validator is decomposed into sub-modules by domain, each responsible
for a subset of the ~92 conformance checks.

Usage:
    validator = PdfX4Validator()
    findings = validator.validate(document, events)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.conformance.base import BaseConformanceValidator
from grounded.conformance.pdfx4._annotations import validate_annotations
from grounded.conformance.pdfx4._boxes import validate_boxes
from grounded.conformance.pdfx4._color import validate_color
from grounded.conformance.pdfx4._file_structure import validate_file_structure
from grounded.conformance.pdfx4._font import validate_fonts
from grounded.conformance.pdfx4._images import validate_images
from grounded.conformance.pdfx4._metadata import validate_metadata
from grounded.conformance.pdfx4._optional_content import validate_optional_content
from grounded.conformance.pdfx4._output_intent import validate_output_intent
from grounded.conformance.pdfx4._resources import validate_resources
from grounded.conformance.pdfx4._restricted_features import validate_restricted_features
from grounded.conformance.pdfx4._security import validate_security
from grounded.conformance.pdfx4._transparency import validate_transparency

if TYPE_CHECKING:
    from grounded.analyzers.finding import Finding
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument


class PdfX4Validator(BaseConformanceValidator):
    """PDF/X-4 (ISO 15930-7:2010) conformance validator.

    Runs all sub-validators and aggregates findings.
    """

    def validate(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        analyzer_findings: list[Finding] | None = None,
    ) -> list[Finding]:
        """Run all PDF/X-4 conformance checks."""
        findings: list[Finding] = []
        findings.extend(validate_file_structure(document))
        findings.extend(validate_security(document))
        findings.extend(validate_metadata(document))
        findings.extend(validate_output_intent(document))
        findings.extend(validate_color(document, events))
        findings.extend(validate_fonts(document))
        findings.extend(validate_boxes(document))
        findings.extend(validate_annotations(document))
        findings.extend(validate_transparency(document, events))
        findings.extend(validate_images(document, events))
        findings.extend(validate_optional_content(document))
        findings.extend(validate_restricted_features(document, events))
        findings.extend(validate_resources(document))
        return findings
