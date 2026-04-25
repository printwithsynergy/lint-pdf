"""MetadataAnalyzer — XMP and Info dict consistency checks.

Validates document metadata for completeness and consistency,
especially fields required by PDF/X-4.

Check IDs:
    LPDF_META_001 — XMP metadata stream missing
    LPDF_META_002 — Info dict / XMP title inconsistency
    LPDF_META_003 — Trapped key missing or Unknown
    LPDF_META_004 — PDF version mismatch (header vs XMP)
    LPDF_VIEWER_DISPLAY_TITLE — Catalog /ViewerPreferences /DisplayDocTitle
        absent or false (T4-A10)
    LPDF_XMP_GWG_TRAIL — GWG XMP audit-trail namespace not present (T2-XMP01)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.conformance.xmp import XmpMetadata

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


class MetadataAnalyzer(BaseAnalyzer):
    """Analyzer for document metadata completeness and consistency."""

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze document metadata."""
        findings: list[Finding] = []

        # T4-A10 — Catalog /ViewerPreferences /DisplayDocTitle.
        findings.extend(self._check_display_doc_title(document))

        # LPDF_META_001: XMP metadata missing
        if document.metadata_stream is None:
            findings.append(
                Finding(
                    inspection_id="LPDF_META_001",
                    severity=Severity.WARNING,
                    message="XMP metadata stream is missing",
                    iso_clause="ISO 15930-7:2010 6.2.2",
                )
            )
            return findings

        xmp = XmpMetadata.from_bytes(document.metadata_stream)

        # T2-XMP01 — GWG XMP audit-trail namespace.
        findings.extend(self._check_gwg_namespace(xmp, document.metadata_stream))

        # LPDF_META_002: Title inconsistency
        info_title = str(document.info_dict.get("/Title", "")).strip()
        xmp_title = xmp.title.strip()
        if info_title and xmp_title and info_title != xmp_title:
            findings.append(
                Finding(
                    inspection_id="LPDF_META_002",
                    severity=Severity.ADVISORY,
                    message=(f"Title mismatch: Info dict '{info_title}' vs XMP '{xmp_title}'"),
                    details={
                        "info_title": info_title,
                        "xmp_title": xmp_title,
                    },
                    iso_clause="ISO 15930-7:2010 6.2.2",
                )
            )

        # LPDF_META_003: Trapped key
        trapped = xmp.trapped
        if not trapped or trapped == "Unknown":
            findings.append(
                Finding(
                    inspection_id="LPDF_META_003",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Trapped key is {'Unknown' if trapped == 'Unknown' else 'missing'} "
                        f"in XMP metadata"
                    ),
                    details={"trapped": trapped},
                    iso_clause="ISO 15930-7:2010 6.2.2",
                )
            )

        # LPDF_META_004: PDF version mismatch
        xmp_version = xmp.pdf_version
        if xmp_version and xmp_version != document.version:
            findings.append(
                Finding(
                    inspection_id="LPDF_META_004",
                    severity=Severity.ADVISORY,
                    message=(
                        f"PDF version mismatch: header '{document.version}' vs XMP '{xmp_version}'"
                    ),
                    details={
                        "header_version": document.version,
                        "xmp_version": xmp_version,
                    },
                    iso_clause="ISO 15930-7:2010 6.2.2",
                )
            )

        return findings

    @staticmethod
    def _check_display_doc_title(document: SemanticDocument) -> list[Finding]:
        """T4-A10 — /Catalog /ViewerPreferences /DisplayDocTitle should
        be true so PDF readers display the document's title rather
        than the filename. Required by WCAG 2.1 SC 2.4.2 (Page Titled)
        when the title is the meaningful identifier."""
        catalog = document.catalog or {}
        viewer_prefs = catalog.get("/ViewerPreferences")
        if isinstance(viewer_prefs, dict):
            display_title = viewer_prefs.get("/DisplayDocTitle")
            if display_title is True:
                return []
            return [
                Finding(
                    inspection_id="LPDF_VIEWER_DISPLAY_TITLE",
                    severity=Severity.ADVISORY,
                    message=(
                        "/Catalog /ViewerPreferences /DisplayDocTitle is not true; "
                        "PDF readers will fall back to the filename"
                    ),
                    details={"display_doc_title": display_title},
                    iso_clause="ISO 32000-2 §12.2 / WCAG 2.1 SC 2.4.2",
                )
            ]
        return [
            Finding(
                inspection_id="LPDF_VIEWER_DISPLAY_TITLE",
                severity=Severity.ADVISORY,
                message=(
                    "/Catalog /ViewerPreferences dictionary is missing — add it "
                    "with /DisplayDocTitle true so readers show the document "
                    "title rather than the filename"
                ),
                details={"viewer_preferences_present": False},
                iso_clause="ISO 32000-2 §12.2 / WCAG 2.1 SC 2.4.2",
            )
        ]

    @staticmethod
    def _check_gwg_namespace(xmp: XmpMetadata, raw_xmp: bytes) -> list[Finding]:
        """T2-XMP01 — GWG-compliant tools register an audit-trail
        namespace in XMP (``http://www.gwg.org/...`` / ``ghentpdfworkgroup``).
        Absence is advisory: the PDF likely never passed through a
        GWG-aware preflight tool.

        Checks both raw XMP bytes (catches the namespace declaration
        attribute even when the parser strips the prefix) and parsed
        property keys (catches non-prefixed properties from a known
        GWG schema).
        """
        if raw_xmp:
            try:
                text = raw_xmp.decode("utf-8", errors="replace").lower()
            except Exception:
                text = ""
            if "gwg.org" in text or "ghentpdfworkgroup" in text or "ghent-pdf" in text:
                return []
        for key in xmp.raw_properties:
            lower = key.lower()
            if "gwg" in lower or "ghentpdf" in lower:
                return []
        return [
            Finding(
                inspection_id="LPDF_XMP_GWG_TRAIL",
                severity=Severity.ADVISORY,
                message=(
                    "No GWG audit-trail namespace found in XMP metadata; "
                    "the PDF has not been through a GWG-aware preflight"
                ),
                details={"audit_trail_present": False},
                iso_clause="GWG XMP audit-trail (Application Settings 2022)",
            )
        ]
