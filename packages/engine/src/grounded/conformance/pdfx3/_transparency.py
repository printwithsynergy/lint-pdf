"""PDF/X-3 transparency checks (PDFX3-027-031).

Transparency is completely prohibited in PDF/X-3.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX3"


def validate_transparency(
    document: SemanticDocument, events: list[ContentStreamEvent]
) -> list[Finding]:
    """Run transparency conformance checks."""
    from grounded.semantic.events import OpacityChangedEvent

    findings: list[Finding] = []

    for event in events:
        if isinstance(event, OpacityChangedEvent):
            sa = event.stroking_alpha
            nsa = event.non_stroking_alpha
            if (sa is not None and sa < 1.0) or (nsa is not None and nsa < 1.0):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-031",
                        severity=Severity.ERROR,
                        message="Transparency (alpha < 1.0) — prohibited in PDF/X-3",
                        page_num=event.page_num,
                        iso_clause="ISO 15930-6:2003 6.2.5",
                    )
                )
                break
            if event.blend_mode and event.blend_mode not in ("Normal", "Compatible"):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-030",
                        severity=Severity.ERROR,
                        message=f"Blend mode '{event.blend_mode}' — prohibited in PDF/X-3",
                        page_num=event.page_num,
                        iso_clause="ISO 15930-6:2003 6.2.5",
                    )
                )
                break

    for page in document.pages:
        if page.transparency_group is not None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-028",
                    severity=Severity.ERROR,
                    message=f"Page {page.page_num} has transparency group — prohibited in PDF/X-3",
                    page_num=page.page_num,
                    iso_clause="ISO 15930-6:2003 6.2.5",
                )
            )
            break

    for page in document.pages:
        ext_gstate = page.resources.get("/ExtGState") or page.resources.get("ExtGState")
        if not isinstance(ext_gstate, dict):
            continue
        for gs_name, gs_dict in ext_gstate.items():
            if not isinstance(gs_dict, dict):
                continue
            smask = gs_dict.get("/SMask") or gs_dict.get("SMask")
            if smask is not None and smask != "/None" and smask != "None":
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-029",
                        severity=Severity.ERROR,
                        message=f"Soft mask in '{gs_name}' on page {page.page_num} — prohibited in PDF/X-3",
                        page_num=page.page_num,
                        iso_clause="ISO 15930-6:2003 6.2.5",
                    )
                )
                return findings

    if findings:
        findings.insert(0, Finding(
            inspection_id=f"{_PREFIX}-027",
            severity=Severity.ERROR,
            message="Transparency is used — prohibited in PDF/X-3",
            iso_clause="ISO 15930-6:2003 6.2.5",
        ))

    return findings
