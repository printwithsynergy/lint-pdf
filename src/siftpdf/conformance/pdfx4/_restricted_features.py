"""PDF/X-4 restricted features checks (PDFX4-071-078).

Features prohibited in PDF/X-4 per ISO 15930-7:2010 section 6.2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument

_PREFIX = "PDFX4"


def validate_restricted_features(  # skipcq: PY-R1000
    document: SemanticDocument, events: list[ContentStreamEvent]
) -> list[Finding]:
    """Run restricted features conformance checks."""
    from siftpdf.semantic.events import PrepressStateChangedEvent

    findings: list[Finding] = []
    catalog = document.catalog

    # PDFX4-071: No JavaScript
    names = catalog.get("/Names")
    if isinstance(names, dict):
        js_names = names.get("/JavaScript") or names.get("JavaScript")
        if js_names is not None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-071",
                    severity=Severity.ERROR,
                    message="JavaScript detected in /Names tree (prohibited in PDF/X-4)",
                    iso_clause="ISO 15930-7:2010 6.2.8",
                )
            )

    # Also check OpenAction for JS
    open_action = catalog.get("/OpenAction") or catalog.get("OpenAction")
    if isinstance(open_action, dict):
        action_type = open_action.get("/S") or open_action.get("S")
        if action_type in ("/JavaScript", "JavaScript"):
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-071",
                    severity=Severity.ERROR,
                    message="JavaScript in /OpenAction (prohibited in PDF/X-4)",
                    iso_clause="ISO 15930-7:2010 6.2.8",
                )
            )

    # PDFX4-072: No Launch actions
    aa = catalog.get("/AA") or catalog.get("AA")
    if isinstance(aa, dict):
        for _trigger, action in aa.items():
            if isinstance(action, dict):
                action_type = action.get("/S") or action.get("S")
                if action_type in ("/Launch", "Launch"):
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-072",
                            severity=Severity.ERROR,
                            message="Launch action detected (prohibited in PDF/X-4)",
                            iso_clause="ISO 15930-7:2010 6.2.8",
                        )
                    )
                    break

    # PDFX4-073: No embedded files (EF in file spec)
    if isinstance(names, dict):
        ef_names = names.get("/EmbeddedFiles") or names.get("EmbeddedFiles")
        if ef_names is not None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-073",
                    severity=Severity.ERROR,
                    message="Embedded files detected (prohibited in PDF/X-4)",
                    iso_clause="ISO 15930-7:2010 6.2.8",
                )
            )

    # PDFX4-074: No XFA forms
    acro_form = catalog.get("/AcroForm")
    if isinstance(acro_form, dict):
        xfa = acro_form.get("/XFA") or acro_form.get("XFA")
        if xfa is not None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-074",
                    severity=Severity.ERROR,
                    message="XFA forms detected (prohibited in PDF/X-4)",
                    iso_clause="ISO 15930-7:2010 6.2.8",
                )
            )

    # PDFX4-075: No transfer functions
    has_transfer = False
    for event in events:
        if isinstance(event, PrepressStateChangedEvent) and event.has_transfer_function:
            has_transfer = True
            break

    if has_transfer:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-075",
                severity=Severity.ERROR,
                message="Transfer function detected (prohibited in PDF/X-4)",
                iso_clause="ISO 15930-7:2010 6.2.7",
            )
        )

    # PDFX4-076: Non-default halftones flagged
    has_halftone = False
    for event in events:
        if isinstance(event, PrepressStateChangedEvent) and event.has_halftone:
            has_halftone = True
            break

    if has_halftone:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-076",
                severity=Severity.ADVISORY,
                message="Custom halftone dictionary detected (verify compatibility with RIP)",
                iso_clause="ISO 15930-7:2010 6.2.7",
            )
        )

    # PDFX4-077: No PostScript XObjects
    for page in document.pages:
        xobjects = page.resources.get("/XObject") or page.resources.get("XObject")
        if isinstance(xobjects, dict):
            for xobj_name, xobj in xobjects.items():
                if isinstance(xobj, dict):
                    subtype = xobj.get("/Subtype") or xobj.get("Subtype") or ""
                    if subtype in ("PS", "/PS"):
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-077",
                                severity=Severity.ERROR,
                                message=(
                                    f"PostScript XObject '{xobj_name}' on page {page.page_num} "
                                    f"(prohibited in PDF/X-4)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 15930-7:2010 6.2.8",
                            )
                        )

    # PDFX4-078: No external streams
    for page in document.pages:
        xobjects = page.resources.get("/XObject") or page.resources.get("XObject")
        if isinstance(xobjects, dict):
            for xobj_name, xobj in xobjects.items():
                if isinstance(xobj, dict):
                    f_entry = xobj.get("/F") or xobj.get("F")
                    if f_entry is not None:
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-078",
                                severity=Severity.ERROR,
                                message=(
                                    f"External stream reference in XObject '{xobj_name}' "
                                    f"on page {page.page_num}"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 15930-7:2010 6.2.8",
                            )
                        )

    return findings
