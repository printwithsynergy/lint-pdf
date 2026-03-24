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

from lintpdf.conformance.base import BaseConformanceValidator
from lintpdf.conformance.pdfx4._annotations import validate_annotations
from lintpdf.conformance.pdfx4._boxes import validate_boxes
from lintpdf.conformance.pdfx4._color import validate_color
from lintpdf.conformance.pdfx4._file_structure import validate_file_structure
from lintpdf.conformance.pdfx4._font import validate_fonts
from lintpdf.conformance.pdfx4._images import validate_images
from lintpdf.conformance.pdfx4._metadata import validate_metadata
from lintpdf.conformance.pdfx4._optional_content import validate_optional_content
from lintpdf.conformance.pdfx4._output_intent import validate_output_intent
from lintpdf.conformance.pdfx4._resources import validate_resources
from lintpdf.conformance.pdfx4._restricted_features import validate_restricted_features
from lintpdf.conformance.pdfx4._security import validate_security
from lintpdf.conformance.pdfx4._transparency import validate_transparency

if TYPE_CHECKING:
    from lintpdf.analyzers.finding import Finding
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


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
