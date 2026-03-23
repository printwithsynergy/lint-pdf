"""PDF/X-4 resource checks (PDFX4-088-092).

Validates that all referenced resources are present and valid.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX4"


def validate_resources(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
    """Run resource conformance checks."""
    findings: list[Finding] = []

    for page in document.pages:
        pn = page.page_num
        resources = page.resources

        # PDFX4-088: XObject resources present
        xobjects = resources.get("/XObject") or resources.get("XObject")
        if isinstance(xobjects, dict):
            for name, xobj in xobjects.items():
                if xobj is None:
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-088",
                            severity=Severity.ERROR,
                            message=f"XObject '{name}' on page {pn} references null object",
                            page_num=pn,
                            iso_clause="ISO 32000-2:2020 7.8.3",
                        )
                    )

        # PDFX4-089: Font resources present
        fonts = resources.get("/Font") or resources.get("Font")
        if isinstance(fonts, dict):
            for name, font in fonts.items():
                if font is None:
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-089",
                            severity=Severity.ERROR,
                            message=f"Font '{name}' on page {pn} references null object",
                            page_num=pn,
                            iso_clause="ISO 32000-2:2020 7.8.3",
                        )
                    )

        # PDFX4-090: ColorSpace resources present
        color_spaces = resources.get("/ColorSpace") or resources.get("ColorSpace")
        if isinstance(color_spaces, dict):
            for name, cs in color_spaces.items():
                if cs is None:
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-090",
                            severity=Severity.ERROR,
                            message=f"ColorSpace '{name}' on page {pn} references null object",
                            page_num=pn,
                            iso_clause="ISO 32000-2:2020 7.8.3",
                        )
                    )

        # PDFX4-091: ExtGState resources present
        ext_gstate = resources.get("/ExtGState") or resources.get("ExtGState")
        if isinstance(ext_gstate, dict):
            for name, gs in ext_gstate.items():
                if gs is None:
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-091",
                            severity=Severity.ERROR,
                            message=f"ExtGState '{name}' on page {pn} references null object",
                            page_num=pn,
                            iso_clause="ISO 32000-2:2020 7.8.3",
                        )
                    )

        # PDFX4-092: All resources valid (basic presence check)
        # Verify that page has at least a /ProcSet or /Font if content exists
        if page.content_stream and not fonts and not xobjects:
            # Page has content but no font or xobject resources — unusual but not always wrong
            proc_set = resources.get("/ProcSet") or resources.get("ProcSet")
            if proc_set is None:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-092",
                        severity=Severity.ADVISORY,
                        message=f"Page {pn} has content but no resource entries",
                        page_num=pn,
                        iso_clause="ISO 32000-2:2020 7.8.3",
                    )
                )

    return findings
