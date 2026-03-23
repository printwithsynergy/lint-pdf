"""PDF/X-3 restricted features checks (PDFX3-032-043)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX3"


def validate_restrictions(
    document: SemanticDocument, events: list[ContentStreamEvent]
) -> list[Finding]:
    """Run restricted features conformance checks for PDF/X-3."""
    findings: list[Finding] = []
    catalog = document.catalog

    findings.extend(_check_javascript(catalog))

    names = catalog.get("/Names") or catalog.get("Names")
    if isinstance(names, dict):
        ef = names.get("/EmbeddedFiles") or names.get("EmbeddedFiles")
        if ef is not None:
            findings.append(Finding(
                inspection_id=f"{_PREFIX}-033", severity=Severity.ERROR,
                message="Embedded files present — prohibited in PDF/X-3",
                iso_clause="ISO 15930-6:2003 6.2.8",
            ))

    acro_form = catalog.get("/AcroForm") or catalog.get("AcroForm")
    if isinstance(acro_form, dict):
        fields = acro_form.get("/Fields") or acro_form.get("Fields") or []
        if isinstance(fields, list) and len(fields) > 0:
            findings.append(Finding(
                inspection_id=f"{_PREFIX}-034", severity=Severity.ERROR,
                message=f"Form fields ({len(fields)}) present — prohibited in PDF/X-3",
                iso_clause="ISO 15930-6:2003 6.2.8",
            ))

    if document.is_encrypted:
        findings.append(Finding(
            inspection_id=f"{_PREFIX}-037", severity=Severity.ERROR,
            message="Document is encrypted — prohibited in PDF/X-3",
            iso_clause="ISO 15930-6:2003 6.2.2",
        ))

    for page in document.pages:
        if page.trim_box is None and page.art_box is None:
            findings.append(Finding(
                inspection_id=f"{_PREFIX}-041", severity=Severity.ERROR,
                message=f"Page {page.page_num}: neither TrimBox nor ArtBox present (required for PDF/X-3)",
                page_num=page.page_num,
                iso_clause="ISO 15930-6:2003 6.2.1",
            ))

    oc_properties = catalog.get("/OCProperties") or catalog.get("OCProperties")
    if isinstance(oc_properties, dict):
        findings.append(Finding(
            inspection_id=f"{_PREFIX}-043", severity=Severity.ERROR,
            message="Optional content (layers) present — prohibited in PDF/X-3",
            iso_clause="ISO 15930-6:2003 6.2.8",
        ))

    for page in document.pages:
        xobjects = page.resources.get("/XObject") or page.resources.get("XObject") or {}
        if isinstance(xobjects, dict):
            for xobj_name, xobj_dict in xobjects.items():
                if not isinstance(xobj_dict, dict):
                    continue
                if "/OPI" in xobj_dict or "OPI" in xobj_dict:
                    findings.append(Finding(
                        inspection_id=f"{_PREFIX}-035", severity=Severity.ERROR,
                        message=f"OPI reference in '{xobj_name}' on page {page.page_num} — prohibited in PDF/X-3",
                        page_num=page.page_num, iso_clause="ISO 15930-6:2003 6.2.7",
                    ))
                    return findings
                subtype = xobj_dict.get("/Subtype") or xobj_dict.get("Subtype")
                if subtype in ("/PS", "PS"):
                    findings.append(Finding(
                        inspection_id=f"{_PREFIX}-040", severity=Severity.ERROR,
                        message=f"PostScript XObject '{xobj_name}' on page {page.page_num} — prohibited in PDF/X-3",
                        page_num=page.page_num, iso_clause="ISO 15930-6:2003 6.2.5",
                    ))
                    return findings
                if "/Alternates" in xobj_dict or "Alternates" in xobj_dict:
                    findings.append(Finding(
                        inspection_id=f"{_PREFIX}-042", severity=Severity.ERROR,
                        message=f"Alternate image for '{xobj_name}' on page {page.page_num} — prohibited in PDF/X-3",
                        page_num=page.page_num, iso_clause="ISO 15930-6:2003 6.2.5",
                    ))
                    return findings

        ext_gstate = page.resources.get("/ExtGState") or page.resources.get("ExtGState")
        if isinstance(ext_gstate, dict):
            for gs_name, gs_dict in ext_gstate.items():
                if not isinstance(gs_dict, dict):
                    continue
                tr = gs_dict.get("/TR") or gs_dict.get("TR")
                tr2 = gs_dict.get("/TR2") or gs_dict.get("TR2")
                if tr is not None or tr2 is not None:
                    findings.append(Finding(
                        inspection_id=f"{_PREFIX}-038", severity=Severity.ERROR,
                        message=f"Transfer function in '{gs_name}' on page {page.page_num} — prohibited in PDF/X-3",
                        page_num=page.page_num, iso_clause="ISO 15930-6:2003 6.2.6",
                    ))
                    return findings

    from grounded.semantic.events import ImagePlacedEvent
    for event in events:
        if isinstance(event, ImagePlacedEvent) and event.filters and "LZWDecode" in event.filters:
            findings.append(Finding(
                inspection_id=f"{_PREFIX}-036", severity=Severity.ERROR,
                message=f"LZW compression on '{event.image_name}' on page {event.page_num} — prohibited in PDF/X-3",
                page_num=event.page_num, iso_clause="ISO 15930-6:2003 6.2.5",
            ))
            break

    return findings


def _check_javascript(catalog: dict[str, Any]) -> list[Finding]:
    """Check for JavaScript in catalog."""
    findings: list[Finding] = []
    aa = catalog.get("/AA") or catalog.get("AA")
    if isinstance(aa, dict):
        for action in aa.values():
            if isinstance(action, dict) and (action.get("/S") == "/JavaScript" or action.get("S") == "JavaScript"):
                findings.append(Finding(
                    inspection_id=f"{_PREFIX}-032", severity=Severity.ERROR,
                    message="JavaScript action — prohibited in PDF/X-3",
                    iso_clause="ISO 15930-6:2003 6.2.8",
                ))
                return findings
    names = catalog.get("/Names") or catalog.get("Names")
    if isinstance(names, dict):
        if names.get("/JavaScript") is not None or names.get("JavaScript") is not None:
            findings.append(Finding(
                inspection_id=f"{_PREFIX}-032", severity=Severity.ERROR,
                message="JavaScript name tree — prohibited in PDF/X-3",
                iso_clause="ISO 15930-6:2003 6.2.8",
            ))
    open_action = catalog.get("/OpenAction") or catalog.get("OpenAction")
    if isinstance(open_action, dict) and (open_action.get("/S") == "/JavaScript" or open_action.get("S") == "JavaScript"):
        findings.append(Finding(
            inspection_id=f"{_PREFIX}-032", severity=Severity.ERROR,
            message="JavaScript open action — prohibited in PDF/X-3",
            iso_clause="ISO 15930-6:2003 6.2.8",
        ))
    return findings
