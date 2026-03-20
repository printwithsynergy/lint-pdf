"""AccessibilityAnalyzer — document-level accessibility checks.

Inspects the document catalog for structure tree, language, and tagging
metadata required for accessible PDFs (PDF/UA compliance).

Check IDs:
    GRD_ACCESS_001 — No structure tree (not tagged)
    GRD_ACCESS_002 — No document language specified
    GRD_ACCESS_003 — Tagged PDF present (informational)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument


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

        # GRD_ACCESS_001: No structure tree
        if not has_struct_tree:
            findings.append(
                Finding(
                    inspection_id="GRD_ACCESS_001",
                    severity=Severity.ADVISORY,
                    message="Document has no structure tree (not tagged for accessibility)",
                    details={"has_struct_tree": False},
                    iso_clause="ISO 14289-1:2014 7.1",
                )
            )

        # GRD_ACCESS_002: No document language
        if not has_lang:
            findings.append(
                Finding(
                    inspection_id="GRD_ACCESS_002",
                    severity=Severity.ADVISORY,
                    message="Document has no language specified (/Lang missing from catalog)",
                    details={"has_lang": False},
                    iso_clause="ISO 14289-1:2014 7.2",
                )
            )

        # GRD_ACCESS_003: Tagged PDF present (informational)
        if has_struct_tree:
            mark_info = catalog.get("/MarkInfo")
            is_marked = False
            if isinstance(mark_info, dict):
                is_marked = bool(mark_info.get("/Marked", False))

            if is_marked:
                findings.append(
                    Finding(
                        inspection_id="GRD_ACCESS_003",
                        severity=Severity.ADVISORY,
                        message="Document is a tagged PDF (StructTreeRoot and MarkInfo present)",
                        details={
                            "has_struct_tree": True,
                            "is_marked": True,
                        },
                        iso_clause="ISO 32000-2:2020 14.8",
                    )
                )

        return findings
