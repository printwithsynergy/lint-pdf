"""PDF/A restricted features checks (PDFA-026-040).

Validates feature restrictions per ISO 19005.
Restrictions vary by level: PDF/A-1b is most restrictive,
PDF/A-2b relaxes transparency/JPEG2000/layers, PDF/A-3b allows any embedded file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFA"


def validate_restrictions(  # skipcq: PY-R1000
    document: SemanticDocument, events: list[ContentStreamEvent], level: str
) -> list[Finding]:
    """Run restricted features conformance checks."""
    from grounded.semantic.events import (
        ImagePlacedEvent,
        OpacityChangedEvent,
        PrepressStateChangedEvent,
    )

    findings: list[Finding] = []
    catalog = document.catalog

    # PDFA-026: JavaScript present
    names = catalog.get("/Names")
    if isinstance(names, dict):
        js_names = names.get("/JavaScript") or names.get("JavaScript")
        if js_names is not None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-026",
                    severity=Severity.ERROR,
                    message="JavaScript detected in /Names tree (prohibited in PDF/A)",
                    iso_clause="ISO 19005 6.6.1",
                )
            )

    # Also check OpenAction for JS
    open_action = catalog.get("/OpenAction") or catalog.get("OpenAction")
    if isinstance(open_action, dict):
        action_type = open_action.get("/S") or open_action.get("S")
        if action_type in ("/JavaScript", "JavaScript"):
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-026",
                    severity=Severity.ERROR,
                    message="JavaScript in /OpenAction (prohibited in PDF/A)",
                    iso_clause="ISO 19005 6.6.1",
                )
            )

    # PDFA-027: Encryption present
    encrypt = catalog.get("/Encrypt") or catalog.get("Encrypt")
    if encrypt is not None:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-027",
                severity=Severity.ERROR,
                message="Encryption/security detected (prohibited in PDF/A)",
                iso_clause="ISO 19005 6.1.3",
            )
        )
    elif hasattr(document, "is_encrypted") and document.is_encrypted:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-027",
                severity=Severity.ERROR,
                message="Document is encrypted (prohibited in PDF/A)",
                iso_clause="ISO 19005 6.1.3",
            )
        )

    # PDFA-028: Embedded files present
    # A-1b: prohibited, A-2b: allowed if PDF/A, A-3b: any file allowed
    if isinstance(names, dict):
        ef_names = names.get("/EmbeddedFiles") or names.get("EmbeddedFiles")
        if ef_names is not None:
            if level.startswith("1"):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-028",
                        severity=Severity.ERROR,
                        message="Embedded files detected (prohibited in PDF/A-1)",
                        iso_clause="ISO 19005-1 6.6.1",
                    )
                )
            elif level.startswith("2"):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-028",
                        severity=Severity.WARNING,
                        message=(
                            "Embedded files detected — must be PDF/A compliant "
                            "for PDF/A-2 conformance"
                        ),
                        iso_clause="ISO 19005-2 6.9",
                    )
                )
            # A-3b: any file type allowed, no finding

    # PDFA-029: Audio/video/3D annotations
    for page in document.pages:
        annots = page.resources.get("/Annots") or page.resources.get("Annots")
        if not isinstance(annots, list):
            # Also check page-level annotations attribute
            if hasattr(page, "annotations"):
                annots = page.annotations
        if isinstance(annots, list):
            for annot in annots:
                if not isinstance(annot, dict):
                    continue
                annot_subtype = annot.get("/Subtype") or annot.get("Subtype") or ""
                if annot_subtype in (
                    "/Sound", "Sound",
                    "/Movie", "Movie",
                    "/Screen", "Screen",
                    "/3D", "3D",
                    "/RichMedia", "RichMedia",
                ):
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-029",
                            severity=Severity.ERROR,
                            message=(
                                f"Multimedia annotation '{annot_subtype}' on page "
                                f"{page.page_num} (prohibited in PDF/A)"
                            ),
                            page_num=page.page_num,
                            iso_clause="ISO 19005 6.6.1",
                        )
                    )
                    break  # One finding per page is enough

    # PDFA-030: LZW compression
    for event in events:
        if isinstance(event, ImagePlacedEvent):
            filters = event.filters if hasattr(event, "filters") else []
            if filters and any(f in ("LZWDecode", "/LZWDecode") for f in filters):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-030",
                        severity=Severity.ERROR,
                        message=(
                            f"LZW compression used on image '{event.image_name}' "
                            f"on page {event.page_num} (prohibited in PDF/A)"
                        ),
                        page_num=event.page_num,
                        iso_clause="ISO 19005 6.1.10",
                    )
                )
                break  # One finding is enough

    # PDFA-031: Form fields (XFA prohibited, AcroForm allowed in A-2+)
    acro_form = catalog.get("/AcroForm") or catalog.get("AcroForm")
    if acro_form is not None:
        if isinstance(acro_form, dict):
            xfa = acro_form.get("/XFA") or acro_form.get("XFA")
            if xfa is not None:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-031",
                        severity=Severity.ERROR,
                        message="XFA form data detected (prohibited in PDF/A)",
                        iso_clause="ISO 19005 6.6.1",
                    )
                )
        if level.startswith("1"):
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-031",
                    severity=Severity.WARNING,
                    message="AcroForm detected (interactive forms restricted in PDF/A-1)",
                    iso_clause="ISO 19005-1 6.6.1",
                )
            )

    # PDFA-032: External references (OPI, /Ref, /URL)
    for page in document.pages:
        xobjects = page.resources.get("/XObject") or page.resources.get("XObject")
        if isinstance(xobjects, dict):
            for xobj_name, xobj in xobjects.items():
                if isinstance(xobj, dict):
                    opi = xobj.get("/OPI") or xobj.get("OPI")
                    if opi is not None:
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-032",
                                severity=Severity.ERROR,
                                message=(
                                    f"OPI reference in XObject '{xobj_name}' "
                                    f"on page {page.page_num} (prohibited in PDF/A)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 19005 6.6.1",
                            )
                        )

                    ref = xobj.get("/Ref") or xobj.get("Ref")
                    if ref is not None:
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-032",
                                severity=Severity.ERROR,
                                message=(
                                    f"External /Ref in XObject '{xobj_name}' "
                                    f"on page {page.page_num} (prohibited in PDF/A)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 19005 6.6.1",
                            )
                        )

    # Check catalog for /URI or /URL actions
    uri_action = catalog.get("/URI") or catalog.get("URI")
    if isinstance(uri_action, dict):
        base_uri = uri_action.get("/Base") or uri_action.get("Base")
        if base_uri:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-032",
                    severity=Severity.WARNING,
                    message="Document-level URI base found (external reference)",
                    iso_clause="ISO 19005 6.6.1",
                )
            )

    # PDFA-033: Transparency used (prohibited in A-1b, allowed in A-2b+)
    if level.startswith("1"):
        transparency_detected = False

        for event in events:
            if not isinstance(event, OpacityChangedEvent):
                continue
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
                            f"(transparency prohibited in PDF/A-1)"
                        ),
                        page_num=event.page_num,
                        iso_clause="ISO 19005-1 6.4",
                    )
                )
                break  # One finding is enough

            if event.blend_mode and event.blend_mode not in ("Normal", "Compatible"):
                transparency_detected = True
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-033",
                        severity=Severity.ERROR,
                        message=(
                            f"Non-Normal blend mode '{event.blend_mode}' on page "
                            f"{event.page_num} (transparency prohibited in PDF/A-1)"
                        ),
                        page_num=event.page_num,
                        iso_clause="ISO 19005-1 6.4",
                    )
                )
                break  # One finding is enough

        # Check for transparency groups on pages
        for page in document.pages:
            group = page.transparency_group
            if group is not None:
                transparency_detected = True
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-033",
                        severity=Severity.ERROR,
                        message=(
                            f"Page {page.page_num} has a transparency group "
                            f"(prohibited in PDF/A-1)"
                        ),
                        page_num=page.page_num,
                        iso_clause="ISO 19005-1 6.4",
                    )
                )

        # Check for soft masks in ExtGState
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
                                    inspection_id=f"{_PREFIX}-033",
                                    severity=Severity.ERROR,
                                    message=(
                                        f"Soft mask '{gs_name}' on page {page.page_num} "
                                        f"(prohibited in PDF/A-1)"
                                    ),
                                    page_num=page.page_num,
                                    iso_clause="ISO 19005-1 6.4",
                                )
                            )

    # PDFA-034: JPEG2000 compression (prohibited in A-1b, allowed in A-2b+)
    if level.startswith("1"):
        for event in events:
            if isinstance(event, ImagePlacedEvent):
                filters = event.filters if hasattr(event, "filters") else []
                if filters and any(
                    f in ("JPXDecode", "/JPXDecode") for f in filters
                ):
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-034",
                            severity=Severity.ERROR,
                            message=(
                                f"JPEG2000 compression used on image '{event.image_name}' "
                                f"on page {event.page_num} (prohibited in PDF/A-1)"
                            ),
                            page_num=event.page_num,
                            iso_clause="ISO 19005-1 6.1.10",
                        )
                    )
                    break  # One finding is enough

    # PDFA-035: Optional content present (prohibited in A-1b, constrained in A-2b+)
    ocproperties = catalog.get("/OCProperties") or catalog.get("OCProperties")
    if ocproperties is not None:
        if level.startswith("1"):
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-035",
                    severity=Severity.ERROR,
                    message="Optional content (layers) detected (prohibited in PDF/A-1)",
                    iso_clause="ISO 19005-1 6.6.1",
                )
            )
        else:
            # A-2b/A-3b: optional content allowed but all OCGs must be printable
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-035",
                    severity=Severity.WARNING,
                    message=(
                        "Optional content (layers) detected — all OCGs must be printable "
                        "for PDF/A-2/A-3 conformance"
                    ),
                    iso_clause=f"ISO 19005-{level[0]} 6.8",
                )
            )

    # PDFA-036: Actions/triggers present
    # Check catalog-level actions
    aa = catalog.get("/AA") or catalog.get("AA")
    if aa is not None:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-036",
                severity=Severity.ERROR,
                message="Additional actions (/AA) in document catalog (prohibited in PDF/A)",
                iso_clause="ISO 19005 6.6.1",
            )
        )

    # Check page-level actions/triggers
    for page in document.pages:
        page_aa = page.resources.get("/AA") or page.resources.get("AA")
        if hasattr(page, "additional_actions"):
            page_aa = page_aa or page.additional_actions
        if page_aa is not None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-036",
                    severity=Severity.ERROR,
                    message=(
                        f"Additional actions (/AA) on page {page.page_num} "
                        f"(prohibited in PDF/A)"
                    ),
                    page_num=page.page_num,
                    iso_clause="ISO 19005 6.6.1",
                )
            )
            break  # One finding is enough

    # PDFA-037: Transfer functions present
    has_transfer = False
    for event in events:
        if isinstance(event, PrepressStateChangedEvent) and event.has_transfer_function:
            has_transfer = True
            break

    if has_transfer:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-037",
                severity=Severity.ERROR,
                message="Transfer function detected (prohibited in PDF/A)",
                iso_clause="ISO 19005 6.2.8",
            )
        )

    # PDFA-038: PostScript XObject present
    for page in document.pages:
        xobjects = page.resources.get("/XObject") or page.resources.get("XObject")
        if isinstance(xobjects, dict):
            for xobj_name, xobj in xobjects.items():
                if isinstance(xobj, dict):
                    subtype = xobj.get("/Subtype") or xobj.get("Subtype") or ""
                    if subtype in ("PS", "/PS"):
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-038",
                                severity=Severity.ERROR,
                                message=(
                                    f"PostScript XObject '{xobj_name}' on page "
                                    f"{page.page_num} (prohibited in PDF/A)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 19005 6.2.8",
                            )
                        )

    # PDFA-039: Alternate images present
    for page in document.pages:
        xobjects = page.resources.get("/XObject") or page.resources.get("XObject")
        if isinstance(xobjects, dict):
            for xobj_name, xobj in xobjects.items():
                if isinstance(xobj, dict):
                    alternates = xobj.get("/Alternates") or xobj.get("Alternates")
                    if alternates is not None:
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-039",
                                severity=Severity.ERROR,
                                message=(
                                    f"Alternate image in XObject '{xobj_name}' "
                                    f"on page {page.page_num} (prohibited in PDF/A)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 19005 6.2.8",
                            )
                        )

    # PDFA-040: File attachment annotations (A-1b: prohibited, A-2b+: allowed)
    if level.startswith("1"):
        for page in document.pages:
            annots = page.resources.get("/Annots") or page.resources.get("Annots")
            if not isinstance(annots, list):
                if hasattr(page, "annotations"):
                    annots = page.annotations
            if isinstance(annots, list):
                for annot in annots:
                    if not isinstance(annot, dict):
                        continue
                    annot_subtype = annot.get("/Subtype") or annot.get("Subtype") or ""
                    if annot_subtype in ("/FileAttachment", "FileAttachment"):
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-040",
                                severity=Severity.ERROR,
                                message=(
                                    f"File attachment annotation on page {page.page_num} "
                                    f"(prohibited in PDF/A-1)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 19005-1 6.6.1",
                            )
                        )
                        break  # One finding per page is enough

    return findings
