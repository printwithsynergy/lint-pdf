"""StructureAnalyzer — document structure and feature detection.

Inspects the document catalog for features that cause print issues:
JavaScript, form fields, layers (OCG), embedded files, 3D content.

Check IDs:
    LPDF_STRUCT_001 — JavaScript present
    LPDF_STRUCT_002 — Form fields present
    LPDF_STRUCT_003 — Layers (OCG) detected
    LPDF_STRUCT_004 — Embedded files present
    LPDF_STRUCT_005 — 3D content present
    LPDF_STRUCT_006 — XFA forms detected
    LPDF_STRUCT_007 — Tagged PDF (structure tree present)
    LPDF_STRUCT_008 — JavaScript detected in PDF (via /JS or /JavaScript actions)
    LPDF_STRUCT_009 — Interactive form fields detected
    LPDF_STRUCT_010 — Layer print state mismatch (screen vs print)
    LPDF_STRUCT_011 — PostScript fragments detected
    LPDF_STRUCT_012 — Bookmarks/outlines detected
    LPDF_STRUCT_013 — Embedded page thumbnails detected
    LPDF_STRUCT_014 — Non-JavaScript action detected
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument, SemanticPage


class StructureAnalyzer(BaseAnalyzer):
    """Analyzer for document structure features that affect printability."""

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze document catalog for problematic structures."""
        findings: list[Finding] = []
        catalog = document.catalog

        # LPDF_STRUCT_001: JavaScript
        if self._has_javascript(catalog):
            findings.append(
                Finding(
                    inspection_id="LPDF_STRUCT_001",
                    severity=Severity.ERROR,
                    message="Document contains JavaScript (not allowed in print workflows)",
                    details={"source": "catalog"},
                    iso_clause="ISO 15930-7:2010 6.2.8",
                )
            )

        # LPDF_STRUCT_002: Form fields (AcroForm)
        acro_form = catalog.get("/AcroForm")
        if isinstance(acro_form, dict):
            fields = acro_form.get("/Fields", [])
            if isinstance(fields, list) and len(fields) > 0:
                findings.append(
                    Finding(
                        inspection_id="LPDF_STRUCT_002",
                        severity=Severity.WARNING,
                        message=(
                            f"Document contains {len(fields)} form field(s) "
                            f"(should be flattened before print)"
                        ),
                        details={"field_count": len(fields)},
                        iso_clause="ISO 15930-7:2010 6.2.8",
                    )
                )

        # LPDF_STRUCT_003: Optional Content (Layers/OCG)
        oc_properties = catalog.get("/OCProperties")
        if isinstance(oc_properties, dict):
            ocgs = oc_properties.get("/OCGs", [])
            count = len(ocgs) if isinstance(ocgs, list) else 0
            findings.append(
                Finding(
                    inspection_id="LPDF_STRUCT_003",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Document contains optional content / layers "
                        f"({count} group{'s' if count != 1 else ''} detected)"
                    ),
                    details={"ocg_count": count},
                    iso_clause="ISO 32000-2:2020 8.11",
                )
            )

        # LPDF_STRUCT_004: Embedded files
        names = catalog.get("/Names")
        if isinstance(names, dict):
            ef = names.get("/EmbeddedFiles")
            if ef is not None:
                findings.append(
                    Finding(
                        inspection_id="LPDF_STRUCT_004",
                        severity=Severity.WARNING,
                        message="Document contains embedded files",
                        iso_clause="ISO 15930-7:2010 6.2.8",
                    )
                )

        # LPDF_STRUCT_005: 3D content (check annotations on pages)
        for page in document.pages:
            if self._page_has_3d(page):
                findings.append(
                    Finding(
                        inspection_id="LPDF_STRUCT_005",
                        severity=Severity.ERROR,
                        message=f"3D annotation found on page {page.page_num}",
                        page_num=page.page_num,
                        iso_clause="ISO 32000-2:2020 13.6.3",
                    )
                )
                break  # One finding is enough

        # LPDF_STRUCT_006: XFA forms
        acro_form_xfa = catalog.get("/AcroForm")
        if isinstance(acro_form_xfa, dict) and acro_form_xfa.get("/XFA") is not None:
            findings.append(
                Finding(
                    inspection_id="LPDF_STRUCT_006",
                    severity=Severity.ERROR,
                    message="Document contains XFA forms (not supported in print workflows)",
                    iso_clause="ISO 15930-7:2010 6.2.8",
                )
            )

        # LPDF_STRUCT_007: Tagged PDF (structure tree present)
        if catalog.get("/MarkInfo") is not None or catalog.get("/StructTreeRoot") is not None:
            findings.append(
                Finding(
                    inspection_id="LPDF_STRUCT_007",
                    severity=Severity.ADVISORY,
                    message="Document is a tagged PDF (structure tree present)",
                    details={
                        "has_mark_info": catalog.get("/MarkInfo") is not None,
                        "has_struct_tree": catalog.get("/StructTreeRoot") is not None,
                    },
                    iso_clause="ISO 32000-2:2020 14.7",
                )
            )

        # LPDF_STRUCT_008: JavaScript detected via /JS or /JavaScript in actions
        findings.extend(self._check_javascript_actions(catalog, document))

        # LPDF_STRUCT_009: Interactive form fields detected
        findings.extend(self._check_interactive_forms(catalog))

        # LPDF_STRUCT_010: Layer print state mismatch
        findings.extend(self._check_layer_print_mismatch(catalog))

        # LPDF_STRUCT_011: PostScript fragments
        findings.extend(self._check_postscript_fragments(document))

        # LPDF_STRUCT_012: Bookmarks/outlines
        findings.extend(self._check_bookmarks(catalog))

        # LPDF_STRUCT_013: Embedded page thumbnails
        findings.extend(self._check_page_thumbnails(document))

        # LPDF_STRUCT_014: Non-JavaScript actions
        findings.extend(self._check_non_js_actions(catalog))

        return findings

    @staticmethod
    def _has_javascript(catalog: dict[str, Any]) -> bool:
        """Check catalog for JavaScript actions."""
        # Check /AA (Additional Actions)
        aa = catalog.get("/AA")
        if isinstance(aa, dict):
            for action in aa.values():
                if isinstance(action, dict) and action.get("/S") == "/JavaScript":
                    return True

        # Check /Names/JavaScript
        names = catalog.get("/Names")
        if isinstance(names, dict) and names.get("/JavaScript") is not None:
            return True

        # Check /OpenAction
        open_action = catalog.get("/OpenAction")
        return isinstance(open_action, dict) and open_action.get("/S") == "/JavaScript"

    @staticmethod
    def _check_javascript_actions(  # skipcq: PY-R1000
        catalog: dict[str, Any], document: SemanticDocument
    ) -> list[Finding]:
        """Check for /JS or /JavaScript in page actions (LPDF_STRUCT_008).

        Complements LPDF_STRUCT_001 by also scanning page-level /AA dictionaries
        for JavaScript action triggers.
        """
        findings: list[Finding] = []

        # Check page-level additional actions
        for page in document.pages:
            page_aa = page.resources.get("/AA", {})
            if not isinstance(page_aa, dict):
                continue
            for _trigger, action in page_aa.items():
                if not isinstance(action, dict):
                    continue
                action_type = action.get("/S", "")
                if action_type == "/JavaScript" or "/JS" in action:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_STRUCT_008",
                            severity=Severity.ERROR,
                            message=(
                                f"JavaScript action detected in page {page.page_num} "
                                f"actions (security and print workflow risk)"
                            ),
                            page_num=page.page_num,
                            details={"source": "page_actions"},
                            iso_clause="ISO 15930-7:2010 6.2.8",
                        )
                    )
                    return findings  # One finding is enough

        # Also check annotation actions on pages
        for page in document.pages:
            for _annot in page.annotations:
                annot_dict = page.resources.get("/Annots", [])
                if isinstance(annot_dict, list):
                    for ann in annot_dict:
                        if not isinstance(ann, dict):
                            continue
                        ann_action = ann.get("/A", {})
                        if isinstance(ann_action, dict) and (
                            ann_action.get("/S") == "/JavaScript" or "/JS" in ann_action
                        ):
                            findings.append(
                                Finding(
                                    inspection_id="LPDF_STRUCT_008",
                                    severity=Severity.ERROR,
                                    message=(
                                        f"JavaScript action detected in annotation "
                                        f"on page {page.page_num}"
                                    ),
                                    page_num=page.page_num,
                                    details={"source": "annotation_action"},
                                    iso_clause="ISO 15930-7:2010 6.2.8",
                                )
                            )
                            return findings
                    break  # Only check annotations once per page

        return findings

    @staticmethod
    def _check_interactive_forms(catalog: dict[str, Any]) -> list[Finding]:
        """Check for interactive form fields with widgets (LPDF_STRUCT_009).

        Looks for /AcroForm with non-empty /Fields that have /Widget subtypes,
        indicating interactive elements that may not render correctly in print.
        """
        findings: list[Finding] = []
        acro_form = catalog.get("/AcroForm")
        if not isinstance(acro_form, dict):
            return findings

        fields = acro_form.get("/Fields", [])
        if not isinstance(fields, list) or len(fields) == 0:
            return findings

        # Count fields with interactive widget subtypes
        widget_count = 0
        for field_dict in fields:
            if isinstance(field_dict, dict):
                ft = field_dict.get("/FT", "")
                if ft in ("/Tx", "/Btn", "/Ch", "/Sig"):
                    widget_count += 1

        if widget_count > 0:
            findings.append(
                Finding(
                    inspection_id="LPDF_STRUCT_009",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Document contains {widget_count} interactive form field(s) "
                        f"(text inputs, buttons, dropdowns, or signatures)"
                    ),
                    details={
                        "widget_count": widget_count,
                        "total_fields": len(fields),
                    },
                    iso_clause="ISO 32000-2:2020 12.7",
                )
            )
        elif len(fields) > 0:
            # Fields exist but types not identified — still flag
            findings.append(
                Finding(
                    inspection_id="LPDF_STRUCT_009",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Document contains {len(fields)} form field(s) "
                        f"in /AcroForm (may contain interactive elements)"
                    ),
                    details={"total_fields": len(fields)},
                    iso_clause="ISO 32000-2:2020 12.7",
                )
            )

        return findings

    @staticmethod
    def _check_layer_print_mismatch(catalog: dict[str, Any]) -> list[Finding]:  # skipcq: PY-R1000
        """Check for OCG layers where print state differs from screen (LPDF_STRUCT_010).

        Looks at /OCProperties -> /D -> /AS (usage application) or individual
        OCG dictionaries for /Usage/Print vs /Usage/View mismatches.
        """
        findings: list[Finding] = []
        oc_properties = catalog.get("/OCProperties")
        if not isinstance(oc_properties, dict):
            return findings

        ocgs = oc_properties.get("/OCGs", [])
        if not isinstance(ocgs, list):
            return findings

        for ocg in ocgs:
            if not isinstance(ocg, dict):
                continue
            usage = ocg.get("/Usage")
            if not isinstance(usage, dict):
                continue

            print_usage = usage.get("/Print")
            view_usage = usage.get("/View")

            if isinstance(print_usage, dict) and isinstance(view_usage, dict):
                print_state = print_usage.get("/PrintState", "ON")
                view_state = view_usage.get("/ViewState", "ON")
                if print_state != view_state:
                    layer_name = ocg.get("/Name", "unnamed")
                    findings.append(
                        Finding(
                            inspection_id="LPDF_STRUCT_010",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Layer '{layer_name}' has print/screen state mismatch "
                                f"(Print={print_state}, View={view_state})"
                            ),
                            details={
                                "layer_name": layer_name,
                                "print_state": print_state,
                                "view_state": view_state,
                            },
                            iso_clause="ISO 32000-2:2020 8.11.4.4",
                        )
                    )

        # Also check default configuration /D for /AS entries
        default_config = oc_properties.get("/D")
        if isinstance(default_config, dict):
            as_entries = default_config.get("/AS", [])
            if isinstance(as_entries, list):
                for as_entry in as_entries:
                    if not isinstance(as_entry, dict):
                        continue
                    event = as_entry.get("/Event", "")
                    if event == "/Print":
                        ocg_refs = as_entry.get("/OCGs", [])
                        if isinstance(ocg_refs, list) and len(ocg_refs) > 0:
                            findings.append(
                                Finding(
                                    inspection_id="LPDF_STRUCT_010",
                                    severity=Severity.ADVISORY,
                                    message=(
                                        f"Layer configuration has print-specific visibility "
                                        f"rules for {len(ocg_refs)} layer(s)"
                                    ),
                                    details={
                                        "event": event,
                                        "ocg_count": len(ocg_refs),
                                    },
                                    iso_clause="ISO 32000-2:2020 8.11.4.4",
                                )
                            )
                            break

        return findings

    @staticmethod
    def _check_postscript_fragments(document: SemanticDocument) -> list[Finding]:
        """Check for PostScript XObject fragments on pages (LPDF_STRUCT_011).

        PostScript Type 1 XObjects (/Subtype /PS) are prohibited in modern
        PDF/X print workflows.
        """
        findings: list[Finding] = []
        for page in document.pages:
            xobjects = page.resources.get("/XObject", {})
            if not isinstance(xobjects, dict):
                continue
            for _name, xobj in xobjects.items():
                if isinstance(xobj, dict) and xobj.get("/Subtype") == "/PS":
                    findings.append(
                        Finding(
                            inspection_id="LPDF_STRUCT_011",
                            severity=Severity.ERROR,
                            message=(
                                f"PostScript fragment (Type 1 XObject) detected on page "
                                f"{page.page_num} (prohibited in modern PDF/X workflows)"
                            ),
                            page_num=page.page_num,
                            details={"source": "xobject"},
                            iso_clause="ISO 15930-7:2010 6.2.5",
                        )
                    )
                    return findings  # One finding is enough
        return findings

    @staticmethod
    def _check_bookmarks(catalog: dict[str, Any]) -> list[Finding]:
        """Check for bookmarks/outlines in the document catalog (LPDF_STRUCT_012)."""
        findings: list[Finding] = []
        outlines = catalog.get("/Outlines")
        if not isinstance(outlines, dict):
            return findings

        has_first = outlines.get("/First") is not None
        count = outlines.get("/Count")

        if isinstance(count, int) and count > 0:
            findings.append(
                Finding(
                    inspection_id="LPDF_STRUCT_012",
                    severity=Severity.ADVISORY,
                    message=f"Document contains bookmarks/outlines ({count} entries)",
                    details={"count": count},
                    iso_clause="ISO 32000-2:2020 12.3.3",
                )
            )
        elif has_first:
            findings.append(
                Finding(
                    inspection_id="LPDF_STRUCT_012",
                    severity=Severity.ADVISORY,
                    message="Document contains bookmarks/outlines detected",
                    details={"has_first": True},
                    iso_clause="ISO 32000-2:2020 12.3.3",
                )
            )

        return findings

    @staticmethod
    def _check_page_thumbnails(document: SemanticDocument) -> list[Finding]:
        """Check for embedded page thumbnails (LPDF_STRUCT_013).

        Embedded thumbnails are unnecessary in modern PDF and waste file size.
        Only reports once (first page found).
        """
        findings: list[Finding] = []
        for page in document.pages:
            if page.resources.get("/Thumb") is not None:
                findings.append(
                    Finding(
                        inspection_id="LPDF_STRUCT_013",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Embedded page thumbnails detected (starting on page "
                            f"{page.page_num} — increases file size unnecessarily)"
                        ),
                        page_num=page.page_num,
                        details={"source": "page_resources"},
                        iso_clause="ISO 32000-2:2020 12.3.4",
                    )
                )
                return findings  # Only report once
        return findings

    @staticmethod
    def _check_non_js_actions(catalog: dict[str, Any]) -> list[Finding]:
        """Check for non-JavaScript actions in document catalog (LPDF_STRUCT_014).

        Flags action types that are problematic for print workflows:
        /Launch, /URI, /SubmitForm, /ResetForm, /ImportData.
        """
        findings: list[Finding] = []
        problematic_types = {"/Launch", "/URI", "/SubmitForm", "/ResetForm", "/ImportData"}

        def _check_action(action: Any) -> str | None:
            """Return the action type if it is a problematic non-JS action."""
            if isinstance(action, dict):
                action_type = action.get("/S", "")
                if action_type in problematic_types:
                    return action_type
            return None

        # Check /AA (Additional Actions)
        aa = catalog.get("/AA")
        if isinstance(aa, dict):
            for _trigger, action in aa.items():
                action_type = _check_action(action)
                if action_type is not None:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_STRUCT_014",
                            severity=Severity.WARNING,
                            message=(
                                f"Non-JavaScript action '{action_type}' detected in document "
                                f"catalog (may cause unexpected behavior in print workflow)"
                            ),
                            details={"action_type": action_type, "source": "/AA"},
                            iso_clause="ISO 15930-7:2010 6.2.8",
                        )
                    )

        # Check /OpenAction
        open_action = catalog.get("/OpenAction")
        action_type = _check_action(open_action)
        if action_type is not None:
            findings.append(
                Finding(
                    inspection_id="LPDF_STRUCT_014",
                    severity=Severity.WARNING,
                    message=(
                        f"Non-JavaScript action '{action_type}' detected in document "
                        f"catalog (may cause unexpected behavior in print workflow)"
                    ),
                    details={"action_type": action_type, "source": "/OpenAction"},
                    iso_clause="ISO 15930-7:2010 6.2.8",
                )
            )

        return findings

    @staticmethod
    def _page_has_3d(page: SemanticPage) -> bool:
        """Check if page has 3D annotations."""
        annots = page.resources.get("/Annots", [])
        if not isinstance(annots, list):
            return False
        return any(isinstance(annot, dict) and annot.get("/Subtype") == "/3D" for annot in annots)
