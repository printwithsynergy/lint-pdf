"""PDF/X-1a restricted features checks (PDFX1A-034-045).

Validates features prohibited or restricted in PDF/X-1a.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX1A"


def validate_restrictions(
    document: SemanticDocument, events: list[ContentStreamEvent]
) -> list[Finding]:
    """Run restricted features conformance checks."""
    findings: list[Finding] = []
    catalog = document.catalog

    # PDFX1A-034: JavaScript
    findings.extend(_check_javascript(catalog))

    # PDFX1A-035: Embedded files
    names = catalog.get("/Names") or catalog.get("Names")
    if isinstance(names, dict):
        ef = names.get("/EmbeddedFiles") or names.get("EmbeddedFiles")
        if ef is not None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-035",
                    severity=Severity.AGROUND,
                    message="Embedded files present — prohibited in PDF/X-1a",
                    iso_clause="ISO 15930-4:2003 6.2.8",
                )
            )

    # PDFX1A-036: AcroForm
    acro_form = catalog.get("/AcroForm") or catalog.get("AcroForm")
    if isinstance(acro_form, dict):
        fields = acro_form.get("/Fields") or acro_form.get("Fields") or []
        if isinstance(fields, list) and len(fields) > 0:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-036",
                    severity=Severity.AGROUND,
                    message=(
                        f"Form fields ({len(fields)}) present — prohibited in PDF/X-1a"
                    ),
                    iso_clause="ISO 15930-4:2003 6.2.8",
                )
            )

    # PDFX1A-039: Encryption
    if document.is_encrypted:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-039",
                severity=Severity.AGROUND,
                message="Document is encrypted — prohibited in PDF/X-1a",
                iso_clause="ISO 15930-4:2003 6.2.2",
            )
        )

    # PDFX1A-043: TrimBox or ArtBox required on every page
    for page in document.pages:
        if page.trim_box is None and page.art_box is None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-043",
                    severity=Severity.AGROUND,
                    message=(
                        f"Page {page.page_num}: neither TrimBox nor ArtBox present "
                        f"(at least one required for PDF/X-1a)"
                    ),
                    page_num=page.page_num,
                    iso_clause="ISO 15930-4:2003 6.2.1",
                )
            )

    # PDFX1A-045: Optional content (layers) — prohibited
    oc_properties = catalog.get("/OCProperties") or catalog.get("OCProperties")
    if isinstance(oc_properties, dict):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-045",
                severity=Severity.AGROUND,
                message="Optional content (layers) present — prohibited in PDF/X-1a",
                iso_clause="ISO 15930-4:2003 6.2.8",
            )
        )

    # Page-level resource checks
    for page in document.pages:
        # PDFX1A-037: OPI references
        xobjects = page.resources.get("/XObject") or page.resources.get("XObject") or {}
        if isinstance(xobjects, dict):
            for xobj_name, xobj_dict in xobjects.items():
                if isinstance(xobj_dict, dict):
                    if (
                        "/OPI" in xobj_dict
                        or "OPI" in xobj_dict
                        or xobj_dict.get("/Subtype") == "/PS"
                        or xobj_dict.get("Subtype") == "PS"
                    ):
                        if "/OPI" in xobj_dict or "OPI" in xobj_dict:
                            # PDFX1A-037: OPI
                            findings.append(
                                Finding(
                                    inspection_id=f"{_PREFIX}-037",
                                    severity=Severity.AGROUND,
                                    message=(
                                        f"OPI reference in '{xobj_name}' on page "
                                        f"{page.page_num} — prohibited in PDF/X-1a"
                                    ),
                                    page_num=page.page_num,
                                    iso_clause="ISO 15930-4:2003 6.2.7",
                                )
                            )
                            return findings
                        # PDFX1A-042: PostScript XObject
                        if (
                            xobj_dict.get("/Subtype") == "/PS"
                            or xobj_dict.get("Subtype") == "PS"
                        ):
                            findings.append(
                                Finding(
                                    inspection_id=f"{_PREFIX}-042",
                                    severity=Severity.AGROUND,
                                    message=(
                                        f"PostScript XObject '{xobj_name}' on page "
                                        f"{page.page_num} — prohibited in PDF/X-1a"
                                    ),
                                    page_num=page.page_num,
                                    iso_clause="ISO 15930-4:2003 6.2.5",
                                )
                            )
                            return findings

                    # PDFX1A-044: Alternate images
                    if "/Alternates" in xobj_dict or "Alternates" in xobj_dict:
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-044",
                                severity=Severity.AGROUND,
                                message=(
                                    f"Alternate image for '{xobj_name}' on page "
                                    f"{page.page_num} — prohibited in PDF/X-1a"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 15930-4:2003 6.2.5",
                            )
                        )
                        return findings

        # PDFX1A-040: Transfer functions in ExtGState
        ext_gstate = page.resources.get("/ExtGState") or page.resources.get("ExtGState")
        if isinstance(ext_gstate, dict):
            for gs_name, gs_dict in ext_gstate.items():
                if not isinstance(gs_dict, dict):
                    continue
                tr = gs_dict.get("/TR") or gs_dict.get("TR")
                tr2 = gs_dict.get("/TR2") or gs_dict.get("TR2")
                if tr is not None or tr2 is not None:
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-040",
                            severity=Severity.AGROUND,
                            message=(
                                f"Transfer function in graphics state '{gs_name}' "
                                f"on page {page.page_num} — prohibited in PDF/X-1a"
                            ),
                            page_num=page.page_num,
                            iso_clause="ISO 15930-4:2003 6.2.6",
                        )
                    )
                    return findings

                # PDFX1A-041: Halftone information
                ht = gs_dict.get("/HT") or gs_dict.get("HT")
                if ht is not None:
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-041",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Halftone information in graphics state '{gs_name}' "
                                f"on page {page.page_num}"
                            ),
                            page_num=page.page_num,
                            iso_clause="ISO 15930-4:2003 6.2.6",
                        )
                    )
                    return findings

    # PDFX1A-038: LZW compression in images
    from grounded.semantic.events import ImagePlacedEvent

    for event in events:
        if isinstance(event, ImagePlacedEvent):
            if event.filters and "LZWDecode" in event.filters:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-038",
                        severity=Severity.AGROUND,
                        message=(
                            f"LZW compression on image '{event.image_name}' "
                            f"on page {event.page_num} — prohibited in PDF/X-1a"
                        ),
                        page_num=event.page_num,
                        iso_clause="ISO 15930-4:2003 6.2.5",
                    )
                )
                break

    return findings


def _check_javascript(catalog: dict[str, Any]) -> list[Finding]:
    """Check for JavaScript in catalog."""
    findings: list[Finding] = []

    aa = catalog.get("/AA") or catalog.get("AA")
    if isinstance(aa, dict):
        for action in aa.values():
            if isinstance(action, dict) and (
                action.get("/S") == "/JavaScript" or action.get("S") == "JavaScript"
            ):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-034",
                        severity=Severity.AGROUND,
                        message="JavaScript action detected — prohibited in PDF/X-1a",
                        iso_clause="ISO 15930-4:2003 6.2.8",
                    )
                )
                return findings

    names = catalog.get("/Names") or catalog.get("Names")
    if isinstance(names, dict):
        if names.get("/JavaScript") is not None or names.get("JavaScript") is not None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-034",
                    severity=Severity.AGROUND,
                    message="JavaScript name tree present — prohibited in PDF/X-1a",
                    iso_clause="ISO 15930-4:2003 6.2.8",
                )
            )

    open_action = catalog.get("/OpenAction") or catalog.get("OpenAction")
    if isinstance(open_action, dict) and (
        open_action.get("/S") == "/JavaScript" or open_action.get("S") == "JavaScript"
    ):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-034",
                severity=Severity.AGROUND,
                message="JavaScript open action detected — prohibited in PDF/X-1a",
                iso_clause="ISO 15930-4:2003 6.2.8",
            )
        )

    return findings
