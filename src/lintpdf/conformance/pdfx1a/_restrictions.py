"""PDF/X-1a restricted features checks (PDFX1A-034-045).

Features prohibited in PDF/X-1a per ISO 15930-4:2003 section 6.2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

_PREFIX = "PDFX1A"


def validate_restrictions(  # skipcq: PY-R1000
    document: SemanticDocument, events: list[ContentStreamEvent]
) -> list[Finding]:
    """Run restricted features conformance checks."""
    from lintpdf.semantic.events import ImagePlacedEvent, PrepressStateChangedEvent

    findings: list[Finding] = []
    catalog = document.catalog

    # PDFX1A-034: JavaScript present
    names = catalog.get("/Names")
    if isinstance(names, dict):
        js_names = names.get("/JavaScript") or names.get("JavaScript")
        if js_names is not None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-034",
                    severity=Severity.ERROR,
                    message="JavaScript detected in /Names tree (prohibited in PDF/X-1a)",
                    iso_clause="ISO 15930-4:2003 6.2.8",
                )
            )

    # Also check OpenAction for JS
    open_action = catalog.get("/OpenAction") or catalog.get("OpenAction")
    if isinstance(open_action, dict):
        action_type = open_action.get("/S") or open_action.get("S")
        if action_type in ("/JavaScript", "JavaScript"):
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-034",
                    severity=Severity.ERROR,
                    message="JavaScript in /OpenAction (prohibited in PDF/X-1a)",
                    iso_clause="ISO 15930-4:2003 6.2.8",
                )
            )

    # PDFX1A-035: Embedded files present
    if isinstance(names, dict):
        ef_names = names.get("/EmbeddedFiles") or names.get("EmbeddedFiles")
        if ef_names is not None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-035",
                    severity=Severity.ERROR,
                    message="Embedded files detected (prohibited in PDF/X-1a)",
                    iso_clause="ISO 15930-4:2003 6.2.8",
                )
            )

    # PDFX1A-036: Form fields (AcroForm)
    acro_form = catalog.get("/AcroForm") or catalog.get("AcroForm")
    if acro_form is not None:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-036",
                severity=Severity.ERROR,
                message="AcroForm (form fields) detected (prohibited in PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.2.8",
            )
        )

    # PDFX1A-037: OPI references in resources
    for page in document.pages:
        xobjects = page.resources.get("/XObject") or page.resources.get("XObject")
        if isinstance(xobjects, dict):
            for xobj_name, xobj in xobjects.items():
                if isinstance(xobj, dict):
                    opi = xobj.get("/OPI") or xobj.get("OPI")
                    if opi is not None:
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-037",
                                severity=Severity.ERROR,
                                message=(
                                    f"OPI reference in XObject '{xobj_name}' "
                                    f"on page {page.page_num} "
                                    f"(prohibited in PDF/X-1a)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 15930-4:2003 6.2.8",
                            )
                        )

    # PDFX1A-038: LZW compression used
    for event in events:
        if isinstance(event, ImagePlacedEvent):
            filters = event.filters if hasattr(event, "filters") else []
            if filters and any(f in ("LZWDecode", "/LZWDecode") for f in filters):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-038",
                        severity=Severity.ERROR,
                        message=(
                            f"LZW compression used on image '{event.image_name}' "
                            f"on page {event.page_num} (prohibited in PDF/X-1a)"
                        ),
                        page_num=event.page_num,
                        iso_clause="ISO 15930-4:2003 6.2.6",
                    )
                )
                break  # One finding is enough

    # PDFX1A-039: Encryption/security present
    encrypt = catalog.get("/Encrypt") or catalog.get("Encrypt")
    if encrypt is not None:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-039",
                severity=Severity.ERROR,
                message="Encryption/security detected (prohibited in PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.1",
            )
        )
    # Also check document-level encryption attribute if available
    if (
        hasattr(document, "is_encrypted") and document.is_encrypted and encrypt is None
    ):  # Avoid duplicate finding
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-039",
                severity=Severity.ERROR,
                message="Document is encrypted (prohibited in PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.1",
            )
        )

    # PDFX1A-040: Transfer functions present
    has_transfer = False
    for event in events:
        if isinstance(event, PrepressStateChangedEvent) and event.has_transfer_function:
            has_transfer = True
            break

    if has_transfer:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-040",
                severity=Severity.ERROR,
                message="Transfer function detected (prohibited in PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.2.7",
            )
        )

    # PDFX1A-041: Halftone information present
    has_halftone = False
    for event in events:
        if isinstance(event, PrepressStateChangedEvent) and event.has_halftone:
            has_halftone = True
            break

    if has_halftone:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-041",
                severity=Severity.ERROR,
                message="Custom halftone dictionary detected (prohibited in PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.2.7",
            )
        )

    # PDFX1A-042: PostScript XObject present
    for page in document.pages:
        xobjects = page.resources.get("/XObject") or page.resources.get("XObject")
        if isinstance(xobjects, dict):
            for xobj_name, xobj in xobjects.items():
                if isinstance(xobj, dict):
                    subtype = xobj.get("/Subtype") or xobj.get("Subtype") or ""
                    if subtype in ("PS", "/PS"):
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-042",
                                severity=Severity.ERROR,
                                message=(
                                    f"PostScript XObject '{xobj_name}' on page "
                                    f"{page.page_num} (prohibited in PDF/X-1a)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 15930-4:2003 6.2.8",
                            )
                        )

    # PDFX1A-043: TrimBox or ArtBox required
    for page in document.pages:
        trim_box = page.resources.get("/TrimBox") or page.resources.get("TrimBox")
        art_box = page.resources.get("/ArtBox") or page.resources.get("ArtBox")
        # Also check page-level attributes (not just resources)
        if hasattr(page, "trim_box"):
            trim_box = trim_box or page.trim_box
        if hasattr(page, "art_box"):
            art_box = art_box or page.art_box
        if trim_box is None and art_box is None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-043",
                    severity=Severity.ERROR,
                    message=(
                        f"Page {page.page_num} missing both /TrimBox and /ArtBox "
                        f"(at least one required for PDF/X-1a)"
                    ),
                    page_num=page.page_num,
                    iso_clause="ISO 15930-4:2003 6.2.2",
                )
            )

    # PDFX1A-044: Alternate images present
    for page in document.pages:
        xobjects = page.resources.get("/XObject") or page.resources.get("XObject")
        if isinstance(xobjects, dict):
            for xobj_name, xobj in xobjects.items():
                if isinstance(xobj, dict):
                    alternates = xobj.get("/Alternates") or xobj.get("Alternates")
                    if alternates is not None:
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-044",
                                severity=Severity.ERROR,
                                message=(
                                    f"Alternate image in XObject '{xobj_name}' "
                                    f"on page {page.page_num} (prohibited in PDF/X-1a)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 15930-4:2003 6.2.8",
                            )
                        )

    # PDFX1A-045: Optional content (layers) present
    ocproperties = catalog.get("/OCProperties") or catalog.get("OCProperties")
    if ocproperties is not None:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-045",
                severity=Severity.ERROR,
                message="Optional content (layers) detected (prohibited in PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.2.8",
            )
        )

    return findings
