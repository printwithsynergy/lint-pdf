"""PDF/X-4 annotation checks (PDFX4-057-062).

Validates annotation restrictions per ISO 15930-7:2010 section 6.4.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.model import SemanticDocument

_PREFIX = "PDFX4"

# Annotation subtypes prohibited in PDF/X-4
_PROHIBITED_SUBTYPES = {"Sound", "Movie", "3D", "RichMedia", "Screen"}


def validate_annotations(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
    """Run annotation conformance checks."""
    findings: list[Finding] = []

    for page in document.pages:
        for annot in page.annotations:
            pn = page.page_num
            subtype = annot.subtype

            # PDFX4-057: No Sound annotations
            if subtype == "Sound":
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-057",
                        severity=Severity.ERROR,
                        message=f"Sound annotation on page {pn} (prohibited in PDF/X-4)",
                        page_num=pn,
                        iso_clause="ISO 15930-7:2010 6.4",
                    )
                )

            # PDFX4-058: No Movie annotations
            if subtype == "Movie":
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-058",
                        severity=Severity.ERROR,
                        message=f"Movie annotation on page {pn} (prohibited in PDF/X-4)",
                        page_num=pn,
                        iso_clause="ISO 15930-7:2010 6.4",
                    )
                )

            # PDFX4-059: No 3D annotations
            if subtype == "3D":
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-059",
                        severity=Severity.ERROR,
                        message=f"3D annotation on page {pn} (prohibited in PDF/X-4)",
                        page_num=pn,
                        iso_clause="ISO 15930-7:2010 6.4",
                    )
                )

            # PDFX4-060: No RichMedia/Screen annotations
            if subtype in ("RichMedia", "Screen"):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-060",
                        severity=Severity.ERROR,
                        message=f"RichMedia/Screen annotation on page {pn} (prohibited in PDF/X-4)",
                        page_num=pn,
                        iso_clause="ISO 15930-7:2010 6.4",
                    )
                )

            # PDFX4-061: PrinterMark valid (if present)
            if subtype == "PrinterMark" and not annot.is_printable:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-061",
                        severity=Severity.ADVISORY,
                        message=f"PrinterMark annotation on page {pn} is not set to print",
                        page_num=pn,
                        iso_clause="ISO 15930-7:2010 6.4.2",
                    )
                )

            # PDFX4-062: TrapNet valid (if present)
            if subtype == "TrapNet":
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-062",
                        severity=Severity.ADVISORY,
                        message=f"TrapNet annotation on page {pn} (verify trap network data)",
                        page_num=pn,
                        iso_clause="ISO 15930-7:2010 6.4.3",
                    )
                )

    return findings
