"""AnnotationAnalyzer — detect annotations that affect printability.

Inspects PdfAnnotation objects on each page to flag annotations that
would render in print, contain multimedia, or are informational.

Check IDs:
    LPDF_ANNOT_001 — Printable annotation inside trim area
    LPDF_ANNOT_002 — Multimedia annotation (Sound/Movie/RichMedia)
    LPDF_ANNOT_003 — Link annotation detected
    LPDF_ANNOT_004 — Stamp annotation detected
    LPDF_ANNOT_005 — Non-printing annotation in trim area
    LPDF_ANNOT_006 — TrapNet annotation detected
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import PdfAnnotation, PdfBox, SemanticDocument, SemanticPage

_MULTIMEDIA_SUBTYPES = frozenset({"Sound", "Movie", "RichMedia", "3D"})


class AnnotationAnalyzer(BaseAnalyzer):
    """Analyzer for annotation-related preflight issues."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze annotations across all pages."""
        findings: list[Finding] = []

        for page in document.pages:
            for annot in page.annotations:
                findings.extend(self._check_annotation(annot, page))

        return findings

    def _check_annotation(
        self, annot: PdfAnnotation, page: SemanticPage
    ) -> list[Finding]:  # skipcq: PY-R1000
        """Check a single annotation."""
        findings: list[Finding] = []

        # LPDF_ANNOT_006: TrapNet annotation detected
        if annot.subtype == "TrapNet":
            findings.append(
                Finding(
                    inspection_id="LPDF_ANNOT_006",
                    severity=Severity.ADVISORY,
                    message=(
                        f"TrapNet annotation on page {annot.page_num} "
                        f"(embedded trapping may conflict with RIP trapping settings)"
                    ),
                    page_num=annot.page_num,
                    details={"subtype": "TrapNet"},
                    iso_clause="ISO 32000-2:2020 14.11.6",
                )
            )
            return findings

        # LPDF_ANNOT_002: Multimedia annotations
        if annot.subtype in _MULTIMEDIA_SUBTYPES:
            findings.append(
                Finding(
                    inspection_id="LPDF_ANNOT_002",
                    severity=Severity.ERROR,
                    message=(f"Multimedia annotation ({annot.subtype}) on page {annot.page_num}"),
                    page_num=annot.page_num,
                    details={"subtype": annot.subtype},
                    iso_clause="ISO 15930-7:2010 6.2.8",
                )
            )
            return findings

        # LPDF_ANNOT_003: Link annotations
        if annot.subtype == "Link":
            findings.append(
                Finding(
                    inspection_id="LPDF_ANNOT_003",
                    severity=Severity.ADVISORY,
                    message=f"Link annotation on page {annot.page_num}",
                    page_num=annot.page_num,
                    details={"subtype": "Link"},
                )
            )
            return findings

        # LPDF_ANNOT_004: Stamp annotations
        if annot.subtype == "Stamp":
            findings.append(
                Finding(
                    inspection_id="LPDF_ANNOT_004",
                    severity=Severity.ADVISORY,
                    message=f"Stamp annotation on page {annot.page_num}",
                    page_num=annot.page_num,
                    details={"subtype": "Stamp"},
                )
            )

        trim = page.trim_box or page.crop_box or page.media_box
        in_trim = annot.rect is not None and self._rect_overlaps(annot.rect, trim)

        # LPDF_ANNOT_001: Printable annotation in trim area
        if annot.is_printable and in_trim:
            findings.append(
                Finding(
                    inspection_id="LPDF_ANNOT_001",
                    severity=Severity.WARNING,
                    message=(
                        f"Printable {annot.subtype} annotation "
                        f"inside trim area on page {annot.page_num}"
                    ),
                    page_num=annot.page_num,
                    details={
                        "subtype": annot.subtype,
                        "flags": annot.flags,
                    },
                    iso_clause="ISO 32000-2:2020 12.5.3",
                )
            )

        # LPDF_ANNOT_005: Non-printing annotation in trim area
        if (
            not annot.is_printable
            and not annot.is_hidden
            and in_trim
            and annot.subtype not in ("Link", "Popup")
        ):
            findings.append(
                Finding(
                    inspection_id="LPDF_ANNOT_005",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Non-printing {annot.subtype} annotation "
                        f"in trim area on page {annot.page_num}"
                    ),
                    page_num=annot.page_num,
                    details={
                        "subtype": annot.subtype,
                        "flags": annot.flags,
                    },
                )
            )

        return findings

    @staticmethod
    def _rect_overlaps(rect: PdfBox, box: PdfBox) -> bool:
        """Check if an annotation rect overlaps with a page box."""
        return rect.x0 < box.x1 and rect.x1 > box.x0 and rect.y0 < box.y1 and rect.y1 > box.y0
