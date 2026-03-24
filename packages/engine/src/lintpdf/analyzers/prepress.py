"""PrepressAnalyzer — halftone, transfer function, and BG/UCR detection.

Processes PrepressStateChangedEvent events to detect prepress features
that may be prohibited or problematic in print workflows.

Check IDs:
    LPDF_PRESS_001 — Custom halftone dictionary detected
    LPDF_PRESS_002 — Transfer function detected (prohibited in PDF/X)
    LPDF_PRESS_003 — Custom BG/UCR function detected
    LPDF_PRESS_004 — Custom halftone detected in page resources
    LPDF_PRESS_005 — Custom transfer curve detected in page resources
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


class PrepressAnalyzer(BaseAnalyzer):
    """Analyzer for prepress-related features (halftone, transfer, BG/UCR)."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze prepress state events."""
        from lintpdf.semantic.events import PrepressStateChangedEvent

        findings: list[Finding] = []
        seen_halftone = False
        seen_transfer = False
        seen_bg_ucr = False

        for event in events:
            if not isinstance(event, PrepressStateChangedEvent):
                continue

            # LPDF_PRESS_001: Custom halftone
            if event.has_halftone and not seen_halftone:
                seen_halftone = True
                findings.append(
                    Finding(
                        inspection_id="LPDF_PRESS_001",
                        severity=Severity.ADVISORY,
                        message=(f"Custom halftone dictionary detected on page {event.page_num}"),
                        page_num=event.page_num,
                        iso_clause="ISO 32000-2:2020 10.5",
                    )
                )

            # LPDF_PRESS_002: Transfer function (prohibited in PDF/X)
            if event.has_transfer_function and not seen_transfer:
                seen_transfer = True
                findings.append(
                    Finding(
                        inspection_id="LPDF_PRESS_002",
                        severity=Severity.WARNING,
                        message=(
                            f"Transfer function detected on page {event.page_num} "
                            f"(prohibited in PDF/X)"
                        ),
                        page_num=event.page_num,
                        iso_clause="ISO 15930-7:2010 6.2.6",
                    )
                )

            # LPDF_PRESS_003: Custom BG/UCR
            if event.has_bg_ucr and not seen_bg_ucr:
                seen_bg_ucr = True
                findings.append(
                    Finding(
                        inspection_id="LPDF_PRESS_003",
                        severity=Severity.ADVISORY,
                        message=(f"Custom BG/UCR function detected on page {event.page_num}"),
                        page_num=event.page_num,
                        iso_clause="ISO 32000-2:2020 10.3.4",
                    )
                )

        # LPDF_PRESS_004: Custom halftone in page resources or graphics state dicts
        findings.extend(self._check_halftone_in_resources(document))

        # LPDF_PRESS_005: Custom transfer curve in page resources or graphics state dicts
        findings.extend(self._check_transfer_curve_in_resources(document))

        return findings

    @staticmethod
    def _check_halftone_in_resources(document: SemanticDocument) -> list[Finding]:
        """Check for /HalftoneType in page resources (LPDF_PRESS_004).

        Looks for halftone dictionaries in ExtGState or page-level resources
        that contain /HalftoneType, indicating a custom halftone screen.
        """
        findings: list[Finding] = []
        for page in document.pages:
            resources = page.resources
            ext_gstate = resources.get("/ExtGState", {})
            if not isinstance(ext_gstate, dict):
                continue
            for gs_name, gs_dict in ext_gstate.items():
                if not isinstance(gs_dict, dict):
                    continue
                ht = gs_dict.get("/HT")
                if isinstance(ht, dict) and "/HalftoneType" in ht:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_PRESS_004",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Custom halftone (HalftoneType {ht['/HalftoneType']}) "
                                f"detected in ExtGState '{gs_name}' on page {page.page_num}"
                            ),
                            page_num=page.page_num,
                            details={
                                "gs_name": gs_name,
                                "halftone_type": ht["/HalftoneType"],
                            },
                            iso_clause="ISO 32000-2:2020 10.5",
                        )
                    )
                    return findings  # One finding is enough
        return findings

    @staticmethod
    def _check_transfer_curve_in_resources(document: SemanticDocument) -> list[Finding]:
        """Check for /TR or /TR2 in page resources (LPDF_PRESS_005).

        Looks for transfer function entries in ExtGState dictionaries.
        """
        findings: list[Finding] = []
        for page in document.pages:
            resources = page.resources
            ext_gstate = resources.get("/ExtGState", {})
            if not isinstance(ext_gstate, dict):
                continue
            for gs_name, gs_dict in ext_gstate.items():
                if not isinstance(gs_dict, dict):
                    continue
                has_tr = gs_dict.get("/TR") is not None
                has_tr2 = gs_dict.get("/TR2") is not None
                if has_tr or has_tr2:
                    tr_key = "/TR2" if has_tr2 else "/TR"
                    findings.append(
                        Finding(
                            inspection_id="LPDF_PRESS_005",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Custom transfer curve ({tr_key}) detected "
                                f"in ExtGState '{gs_name}' on page {page.page_num}"
                            ),
                            page_num=page.page_num,
                            details={
                                "gs_name": gs_name,
                                "transfer_key": tr_key,
                            },
                            iso_clause="ISO 32000-2:2020 10.4",
                        )
                    )
                    return findings  # One finding is enough
        return findings
