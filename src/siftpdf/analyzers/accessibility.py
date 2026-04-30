"""AccessibilityAnalyzer — document-level accessibility checks.

Inspects the document catalog for structure tree, language, and tagging
metadata required for accessible PDFs (PDF/UA compliance).

Check IDs:
    LPDF_ACCESS_001 — No structure tree (not tagged)
    LPDF_ACCESS_002 — No document language specified
    LPDF_ACCESS_003 — Tagged PDF present (informational)
    LPDF_ACCESS_004 — Missing document language (/Lang in catalog)
    LPDF_ACCESS_005 — Missing alternative text on images
    LPDF_ACCESS_006 — Heading structure missing (no H1..H6)
    LPDF_ACCESS_007 — Empty table headers
    LPDF_ACCESS_008 — Missing list structure (/L, /LI, /Lbl)
    LPDF_ACCESS_009 — Artifact marking missing
    LPDF_ACCESS_010 — Reading order undefined (/StructTreeRoot without /K)
    LPDF_ACCESS_011 — Color-only information conveyed
    LPDF_ACCESS_012 — Insufficient text-background contrast
    LPDF_ACCESS_013 — Tab order not specified (/Tabs in page dict)
    LPDF_ACCESS_TABLE_STRUCTURE — Table cells missing /Scope or /Headers (T4-A06)
    LPDF_ACCESS_HEADING_SKIP — Heading hierarchy skips a level (T4-A07)
    LPDF_ACCESS_SCREEN_READER — Encryption denies screen-reader access (T4-A09)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from siftpdf.analyzers.base import BaseAnalyzer
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument


class AccessibilityAnalyzer(BaseAnalyzer):
    """Analyzer for PDF accessibility checks."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze document for accessibility properties."""
        findings: list[Finding] = []
        catalog = document.catalog

        has_struct_tree = catalog.get("/StructTreeRoot") is not None
        has_lang = catalog.get("/Lang") is not None

        # LPDF_ACCESS_001: No structure tree
        if not has_struct_tree:
            findings.append(
                Finding(
                    inspection_id="LPDF_ACCESS_001",
                    severity=Severity.ADVISORY,
                    message="Document has no structure tree (not tagged for accessibility)",
                    details={"has_struct_tree": False},
                    iso_clause="ISO 14289-1:2014 7.1",
                )
            )

        # LPDF_ACCESS_002: No document language
        if not has_lang:
            findings.append(
                Finding(
                    inspection_id="LPDF_ACCESS_002",
                    severity=Severity.ADVISORY,
                    message="Document has no language specified (/Lang missing from catalog)",
                    details={"has_lang": False},
                    iso_clause="ISO 14289-1:2014 7.2",
                )
            )

        # LPDF_ACCESS_003: Tagged PDF present (informational)
        if has_struct_tree:
            mark_info = catalog.get("/MarkInfo")
            is_marked = False
            if isinstance(mark_info, dict):
                is_marked = bool(mark_info.get("/Marked", False))

            if is_marked:
                findings.append(
                    Finding(
                        inspection_id="LPDF_ACCESS_003",
                        severity=Severity.ADVISORY,
                        message="Document is a tagged PDF (StructTreeRoot and MarkInfo present)",
                        details={
                            "has_struct_tree": True,
                            "is_marked": True,
                        },
                        iso_clause="ISO 32000-2:2020 14.8",
                    )
                )

        # --- Additional accessibility checks (LPDF_ACCESS_004-013) ---

        struct_tree = catalog.get("/StructTreeRoot")

        # LPDF_ACCESS_004: Missing document language (/Lang in catalog)
        lang = catalog.get("/Lang")
        if not lang or (isinstance(lang, str) and not lang.strip()):
            findings.append(
                Finding(
                    inspection_id="LPDF_ACCESS_004",
                    severity=Severity.WARNING,
                    message="Document language not specified (/Lang missing or empty in catalog)",
                    details={"lang": lang},
                    iso_clause="ISO 14289-1:2014 7.2",
                )
            )

        # LPDF_ACCESS_005: Missing alternative text on images
        # Check each page for images that lack /Alt in annotations or struct tree
        for page in document.pages:
            for img in page.images:
                # Heuristic: if the document has a struct tree, images should
                # have alt text.  We flag all images when the struct tree is
                # present but we cannot verify /Alt association at this level.
                if has_struct_tree:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_ACCESS_005",
                            severity=Severity.WARNING,
                            message=(
                                f"Image '{img.name}' on page {page.page_num} may lack "
                                f"alternative text (/Alt)"
                            ),
                            page_num=page.page_num,
                            details={"image_name": img.name},
                            iso_clause="ISO 14289-1:2014 7.3",
                            object_id=img.name,
                            object_type="image",
                        )
                    )

        # Structure-tree based checks (006-010)
        if isinstance(struct_tree, dict):
            k_array = struct_tree.get("/K")

            # LPDF_ACCESS_010: Reading order undefined (/StructTreeRoot without /K)
            if k_array is None:
                findings.append(
                    Finding(
                        inspection_id="LPDF_ACCESS_010",
                        severity=Severity.WARNING,
                        message="Reading order undefined (/StructTreeRoot has no /K children)",
                        details={"has_k": False},
                        iso_clause="ISO 14289-1:2014 7.1",
                    )
                )

            # Collect structure element types from the tree
            struct_types = self._collect_struct_types(struct_tree)

            # LPDF_ACCESS_006: Heading structure missing
            heading_tags = {"/H1", "/H2", "/H3", "/H4", "/H5", "/H6", "/H"}
            if not struct_types.intersection(heading_tags):
                findings.append(
                    Finding(
                        inspection_id="LPDF_ACCESS_006",
                        severity=Severity.ADVISORY,
                        message="No heading structure found in document (missing /H1../H6 tags)",
                        details={"heading_tags_found": []},
                        iso_clause="ISO 14289-1:2014 7.4",
                    )
                )

            # LPDF_ACCESS_007: Empty table headers
            has_table = "/Table" in struct_types or "/TR" in struct_types
            has_th = "/TH" in struct_types
            if has_table and not has_th:
                findings.append(
                    Finding(
                        inspection_id="LPDF_ACCESS_007",
                        severity=Severity.WARNING,
                        message="Table structure found but no table header (/TH) elements present",
                        details={"has_table": True, "has_th": False},
                        iso_clause="ISO 14289-1:2014 7.5",
                    )
                )

            # LPDF_ACCESS_008: Missing list structure
            has_list_items = "/LI" in struct_types or "/Lbl" in struct_types
            has_list_container = "/L" in struct_types
            if has_list_items and not has_list_container:
                findings.append(
                    Finding(
                        inspection_id="LPDF_ACCESS_008",
                        severity=Severity.ADVISORY,
                        message="List items found without proper list container (/L) structure",
                        details={"has_L": False, "has_LI": "/LI" in struct_types},
                        iso_clause="ISO 14289-1:2014 7.6",
                    )
                )

            # LPDF_ACCESS_009: Artifact marking missing
            has_artifact = "/Artifact" in struct_types
            if not has_artifact and document.page_count > 0:
                findings.append(
                    Finding(
                        inspection_id="LPDF_ACCESS_009",
                        severity=Severity.ADVISORY,
                        message=(
                            "No Artifact markings found in structure tree; "
                            "decorative elements may not be properly excluded"
                        ),
                        details={"has_artifact": False},
                        iso_clause="ISO 14289-1:2014 7.1",
                    )
                )

        # LPDF_ACCESS_011: Color-only information conveyed (heuristic)
        # Flag if colored text exists without structural emphasis (/Em, /Strong)
        if isinstance(struct_tree, dict):
            struct_types_for_emphasis = self._collect_struct_types(struct_tree)
            emphasis_tags = {"/Em", "/Strong"}
            has_emphasis = bool(struct_types_for_emphasis.intersection(emphasis_tags))
            if not has_emphasis and document.page_count > 0:
                findings.append(
                    Finding(
                        inspection_id="LPDF_ACCESS_011",
                        severity=Severity.ADVISORY,
                        message=(
                            "No structural emphasis tags (/Em, /Strong) found; "
                            "information may be conveyed by color alone"
                        ),
                        details={"has_emphasis": False},
                        iso_clause="ISO 14289-1:2014 7.1",
                    )
                )

        # LPDF_ACCESS_012: Insufficient text-background contrast (heuristic)
        # Without rendering, we flag if page count > 0 and no color management
        if document.page_count > 0 and not document.output_intents:
            findings.append(
                Finding(
                    inspection_id="LPDF_ACCESS_012",
                    severity=Severity.ADVISORY,
                    message=(
                        "No output intents defined; text-background contrast "
                        "cannot be verified for accessibility"
                    ),
                    details={"has_output_intents": False},
                )
            )

        # LPDF_ACCESS_013: Tab order not specified (/Tabs in page dict)
        for page in document.pages:
            tabs = page.resources.get("/Tabs")
            if tabs is None and has_struct_tree:
                findings.append(
                    Finding(
                        inspection_id="LPDF_ACCESS_013",
                        severity=Severity.ADVISORY,
                        message=f"Tab order not specified on page {page.page_num} (/Tabs missing)",
                        page_num=page.page_num,
                        details={"has_tabs": False},
                        iso_clause="ISO 14289-1:2014 7.1",
                    )
                )

        # T4-A06 — table structure (TH cells missing /Scope or /Headers).
        findings.extend(self._check_table_structure(document))

        # T4-A07 — heading hierarchy skips.
        findings.extend(self._check_heading_skip(document))

        # T4-A09 — encryption permission bit 10 (screen reader).
        findings.extend(self._check_screen_reader_permission(document))

        return findings

    @staticmethod
    def _check_table_structure(document: SemanticDocument) -> list[Finding]:
        """LPDF_ACCESS_TABLE_STRUCTURE — TH cells missing /Scope / /Headers."""
        struct_root = document.catalog.get("/StructTreeRoot")
        if not isinstance(struct_root, dict):
            return []

        table_count = 0
        missing_scope = 0

        def walk(node: object) -> None:
            nonlocal table_count, missing_scope
            if not isinstance(node, dict):
                return
            type_val = node.get("/S") or node.get("/Type")
            type_name = str(type_val).lstrip("/") if type_val else ""
            if type_name == "Table":
                table_count += 1
            if type_name == "TH":
                # Walk /A attribute object(s) for /Scope or /Headers.
                attrs = node.get("/A") or []
                if isinstance(attrs, dict):
                    attrs = [attrs]
                if not isinstance(attrs, list):
                    attrs = []
                has_scope_or_headers = any(
                    isinstance(a, dict)
                    and (a.get("/Scope") is not None or a.get("/Headers") is not None)
                    for a in attrs
                )
                if not has_scope_or_headers:
                    missing_scope += 1
            kids = node.get("/K")
            if isinstance(kids, list):
                for child in kids:
                    walk(child)
            elif isinstance(kids, dict):
                walk(kids)

        walk(struct_root)
        if missing_scope == 0:
            return []
        return [
            Finding(
                inspection_id="LPDF_ACCESS_TABLE_STRUCTURE",
                severity=Severity.WARNING,
                message=(
                    f"Table contains {missing_scope} header cell(s) without "
                    f"/Scope or /Headers — screen readers can't associate "
                    f"data with headers"
                ),
                details={
                    "table_count": table_count,
                    "missing_scope_count": missing_scope,
                },
                iso_clause="ISO 32000-2:2020 14.8.5.7 / WCAG 1.3.1",
            )
        ]

    @staticmethod
    def _check_heading_skip(document: SemanticDocument) -> list[Finding]:
        """LPDF_ACCESS_HEADING_SKIP — heading levels skip in document order."""
        struct_root = document.catalog.get("/StructTreeRoot")
        if not isinstance(struct_root, dict):
            return []

        skip_count = 0
        worst_from = ""
        worst_to = ""
        worst_gap = 0
        prev_level = 0

        def walk(node: object) -> None:
            nonlocal skip_count, worst_from, worst_to, worst_gap, prev_level
            if not isinstance(node, dict):
                return
            type_val = node.get("/S") or node.get("/Type")
            type_name = str(type_val).lstrip("/") if type_val else ""
            if len(type_name) == 2 and type_name[0] == "H" and type_name[1].isdigit():
                level = int(type_name[1])
                if prev_level > 0 and level > prev_level + 1:
                    skip_count += 1
                    gap = level - prev_level
                    if gap > worst_gap:
                        worst_gap = gap
                        worst_from = f"H{prev_level}"
                        worst_to = f"H{level}"
                prev_level = level
            kids = node.get("/K")
            if isinstance(kids, list):
                for child in kids:
                    walk(child)
            elif isinstance(kids, dict):
                walk(kids)

        walk(struct_root)
        if skip_count == 0:
            return []
        return [
            Finding(
                inspection_id="LPDF_ACCESS_HEADING_SKIP",
                severity=Severity.WARNING,
                message=(
                    f"{skip_count} heading hierarchy skip(s) detected "
                    f"(worst: {worst_from} -> {worst_to})"
                ),
                details={
                    "skip_count": skip_count,
                    "worst_skip_from": worst_from,
                    "worst_skip_to": worst_to,
                },
                iso_clause="WCAG 1.3.1 / ISO 32000-2:2020 14.8.4.3",
            )
        ]

    @staticmethod
    def _check_screen_reader_permission(
        document: SemanticDocument,
    ) -> list[Finding]:
        """LPDF_ACCESS_SCREEN_READER — encryption /P bit 10 cleared."""
        if not document.is_encrypted:
            return []
        encrypt = document.trailer.get("/Encrypt")
        if not isinstance(encrypt, dict):
            return []
        p_value = encrypt.get("/P")
        if not isinstance(p_value, int):
            return []
        # Bit 10 (= 1 << 9 = 0x200) — accessibility extraction allowed.
        # Negative /P values are still valid because Python ints carry
        # arbitrary-precision sign bits; mask with 0xFFFFFFFF first to
        # treat as unsigned 32-bit.
        unsigned = p_value & 0xFFFFFFFF
        screen_reader_allowed = bool(unsigned & 0x200)
        if screen_reader_allowed:
            return []
        return [
            Finding(
                inspection_id="LPDF_ACCESS_SCREEN_READER",
                severity=Severity.WARNING,
                message=("Encryption permissions deny screen-reader access (bit 10 cleared in /P)"),
                details={
                    "p_value": p_value,
                    "screen_reader_allowed": False,
                },
                iso_clause="ISO 32000-2:2020 7.6.4.2 Table 22",
            )
        ]

    @staticmethod
    def _collect_struct_types(node: dict, *, _depth: int = 0) -> set[str]:
        """Recursively collect structure element /S types from a struct tree node.

        Limits recursion depth to avoid stack overflow on malformed trees.
        """
        if _depth > 100:
            return set()

        types: set[str] = set()
        s_type = node.get("/S")
        if isinstance(s_type, str):
            types.add(s_type)

        children = node.get("/K")
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    types.update(
                        AccessibilityAnalyzer._collect_struct_types(child, _depth=_depth + 1)
                    )
        elif isinstance(children, dict):
            types.update(AccessibilityAnalyzer._collect_struct_types(children, _depth=_depth + 1))

        return types
