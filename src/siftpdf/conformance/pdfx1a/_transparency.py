"""PDF/X-1a transparency checks (PDFX1A-029-033).

Validates transparency restrictions per ISO 15930-4:2003 section 6.2.5.
PDF/X-1a completely prohibits ALL transparency — no soft masks,
no alpha, no blend modes, no transparency groups.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument

_PREFIX = "PDFX1A"


def validate_transparency(
    document: SemanticDocument, events: list[ContentStreamEvent]
) -> list[Finding]:  # skipcq: PY-R1000
    """Run transparency conformance checks."""
    from siftpdf.semantic.events import OpacityChangedEvent

    findings: list[Finding] = []
    transparency_detected = False

    for event in events:
        if not isinstance(event, OpacityChangedEvent):
            continue

        # PDFX1A-033: Alpha value < 1.0
        sa = event.stroking_alpha
        nsa = event.non_stroking_alpha
        if (sa is not None and sa < 1.0) or (nsa is not None and nsa < 1.0):
            transparency_detected = True
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-033",
                    severity=Severity.ERROR,
                    message=(
                        f"Alpha value < 1.0 detected on page {event.page_num} "
                        f"(transparency prohibited in PDF/X-1a)"
                    ),
                    page_num=event.page_num,
                    iso_clause="ISO 15930-4:2003 6.2.5",
                )
            )
            break  # One finding is enough

        # PDFX1A-032: Non-Normal blend mode
        if event.blend_mode and event.blend_mode not in ("Normal", "Compatible"):
            transparency_detected = True
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-032",
                    severity=Severity.ERROR,
                    message=(
                        f"Non-Normal blend mode '{event.blend_mode}' on page {event.page_num} "
                        f"(transparency prohibited in PDF/X-1a)"
                    ),
                    page_num=event.page_num,
                    iso_clause="ISO 15930-4:2003 6.2.5",
                )
            )
            break  # One finding is enough

    # PDFX1A-030: Page has transparency group
    for page in document.pages:
        group = page.transparency_group
        if group is not None:
            transparency_detected = True
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-030",
                    severity=Severity.ERROR,
                    message=(
                        f"Page {page.page_num} has a transparency group (prohibited in PDF/X-1a)"
                    ),
                    page_num=page.page_num,
                    iso_clause="ISO 15930-4:2003 6.2.5",
                )
            )

    # PDFX1A-031: Soft mask detected (check page resources for ExtGState with SMask)
    for page in document.pages:
        ext_gstate = page.resources.get("/ExtGState") or page.resources.get("ExtGState")
        if isinstance(ext_gstate, dict):
            for gs_name, gs_dict in ext_gstate.items():
                if isinstance(gs_dict, dict):
                    smask = gs_dict.get("/SMask") or gs_dict.get("SMask")
                    if smask is not None and smask != "None":
                        transparency_detected = True
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-031",
                                severity=Severity.ERROR,
                                message=(
                                    f"Soft mask '{gs_name}' on page {page.page_num} "
                                    f"(prohibited in PDF/X-1a)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 15930-4:2003 6.2.5",
                            )
                        )

    # PDFX1A-029: Transparency used (general top-level finding)
    if transparency_detected:
        findings.insert(
            0,
            Finding(
                inspection_id=f"{_PREFIX}-029",
                severity=Severity.ERROR,
                message="Transparency detected (completely prohibited in PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.2.5",
            ),
        )

    return findings
