"""MetadataAnalyzer — XMP and Info dict consistency checks.

Validates document metadata for completeness and consistency,
especially fields required by PDF/X-4.

Check IDs:
    LPDF_META_001 — XMP metadata stream missing
    LPDF_META_002 — Info dict / XMP title inconsistency
    LPDF_META_003 — Trapped key missing or Unknown
    LPDF_META_004 — PDF version mismatch (header vs XMP)
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
