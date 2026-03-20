"""DocumentAnalyzer — document-level consistency and metadata checks.

Inspects document-wide properties for print workflow issues:
mixed page sizes, inconsistent rotation, missing metadata, encryption.

Check IDs:
    GRD_DOC_001 — Mixed page sizes
    GRD_DOC_002 — Inconsistent page rotation
    GRD_DOC_003 — Missing document title
    GRD_DOC_004 — Document is encrypted
    GRD_DOC_005 — Linearized PDF detected
    GRD_DOC_006 — Incremental updates detected
    GRD_DOC_007 — File size exceeds threshold
    GRD_DOC_008 — Pre-separated pages detected
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument


# Default maximum file size: 500 MB
DEFAULT_MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024


class DocumentAnalyzer(BaseAnalyzer):
    """Analyzer for document-level consistency checks.

    Args:
        max_file_size_bytes: Maximum file size threshold in bytes (default 500MB).
    """

    def __init__(
        self,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
    ) -> None:
        self.max_file_size_bytes = max_file_size_bytes

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze document-level properties."""
        findings: list[Finding] = []

        # GRD_DOC_004: Encryption
        if document.is_encrypted:
            findings.append(
                Finding(
                    inspection_id="GRD_DOC_004",
                    severity=Severity.AGROUND,
                    message="Document is encrypted (not allowed in print workflows)",
                    iso_clause="ISO 15930-7:2010 6.2.2",
                )
            )

        # GRD_DOC_003: Missing title
        title = document.info_dict.get("/Title") or document.info_dict.get("Title")
        if not title:
            findings.append(
                Finding(
                    inspection_id="GRD_DOC_003",
                    severity=Severity.ADVISORY,
                    message="Document has no title in Info dictionary",
                    iso_clause="ISO 32000-2:2020 14.3.3",
                )
            )

        # GRD_DOC_005: Linearized PDF
        is_linearized = (
            document.catalog.get("/Linearized") is not None
            or document.trailer.get("/Linearized") is not None
        )
        if is_linearized:
            findings.append(
                Finding(
                    inspection_id="GRD_DOC_005",
                    severity=Severity.ADVISORY,
                    message="Linearized PDF detected (web-optimized, may need re-saving for print)",
                    iso_clause="ISO 32000-2:2020 Annex F",
                )
            )

        # GRD_DOC_006: Incremental updates
        if document.trailer.get("/Prev") is not None:
            findings.append(
                Finding(
                    inspection_id="GRD_DOC_006",
                    severity=Severity.ADVISORY,
                    message=(
                        "Incremental updates detected (trailer has /Prev reference, "
                        "file may contain stale data)"
                    ),
                    iso_clause="ISO 32000-2:2020 7.5.6",
                )
            )

        # GRD_DOC_007: File size exceeds threshold
        file_size = document.info_dict.get("/FileSize") or document.info_dict.get("FileSize")
        if file_size is not None:
            try:
                size_bytes = int(file_size)
            except (ValueError, TypeError):
                size_bytes = 0
            if size_bytes > self.max_file_size_bytes:
                size_mb = size_bytes / (1024 * 1024)
                max_mb = self.max_file_size_bytes / (1024 * 1024)
                findings.append(
                    Finding(
                        inspection_id="GRD_DOC_007",
                        severity=Severity.ADVISORY,
                        message=(
                            f"File size ({size_mb:.1f} MB) exceeds threshold ({max_mb:.1f} MB)"
                        ),
                        details={
                            "file_size_bytes": size_bytes,
                            "max_file_size_bytes": self.max_file_size_bytes,
                        },
                    )
                )

        # GRD_DOC_008: Pre-separated pages detected
        findings.extend(self._check_pre_separated_pages(document))

        if len(document.pages) < 2:
            return findings

        # GRD_DOC_001: Mixed page sizes
        sizes: set[tuple[float, float]] = set()
        for page in document.pages:
            w = round(page.media_box.width, 1)
            h = round(page.media_box.height, 1)
            sizes.add((w, h))

        if len(sizes) > 1:
            findings.append(
                Finding(
                    inspection_id="GRD_DOC_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Document has {len(sizes)} different page sizes "
                        f"(may cause imposition issues)"
                    ),
                    details={
                        "page_sizes": [{"width": s[0], "height": s[1]} for s in sorted(sizes)],
                    },
                )
            )

        # GRD_DOC_002: Inconsistent rotation
        rotations: set[int] = set()
        for page in document.pages:
            rotations.add(page.rotate)

        if len(rotations) > 1:
            findings.append(
                Finding(
                    inspection_id="GRD_DOC_002",
                    severity=Severity.ADVISORY,
                    message=(f"Document has inconsistent page rotations: {sorted(rotations)}"),
                    details={
                        "rotations": sorted(rotations),
                    },
                )
            )

        return findings

    @staticmethod
    def _check_pre_separated_pages(document: SemanticDocument) -> list[Finding]:
        """Check for pre-separated pages (GRD_DOC_008).

        Pre-separated PDFs have individual color separations as separate pages
        (one page per ink). Detected by looking for /Separation color spaces
        at the page level or /SeparationInfo in page dictionaries, or by
        checking if pages use only single-component device color spaces
        in patterns that suggest pre-separation.
        """
        findings: list[Finding] = []

        # Check catalog for /SeparationInfo (document-level hint)
        sep_info = document.catalog.get("/SeparationInfo")
        if isinstance(sep_info, dict):
            findings.append(
                Finding(
                    inspection_id="GRD_DOC_008",
                    severity=Severity.SQUALL,
                    message=("Pre-separated pages detected (document contains /SeparationInfo)"),
                    details={"source": "catalog_separation_info"},
                )
            )
            return findings

        # Check pages for /SeparationInfo in resources or predominant
        # Separation color spaces
        separation_pages: list[int] = []
        for page in document.pages:
            # Check for SeparationInfo in page resources
            page_sep_info = page.resources.get("/SeparationInfo")
            if page_sep_info is not None:
                separation_pages.append(page.page_num)
                continue

            # Check if page uses predominantly Separation color spaces
            sep_count = 0
            total_count = 0
            for _cs_name, cs in page.color_spaces.items():
                total_count += 1
                if cs.cs_type == "Separation":
                    sep_count += 1

            # If all color spaces on the page are Separation type and
            # there's exactly one, it likely is a pre-separated page
            if sep_count == 1 and total_count == 1:
                separation_pages.append(page.page_num)

        if len(separation_pages) >= 2:
            findings.append(
                Finding(
                    inspection_id="GRD_DOC_008",
                    severity=Severity.SQUALL,
                    message=(
                        f"Pre-separated pages detected "
                        f"({len(separation_pages)} pages with single Separation "
                        f"color space)"
                    ),
                    details={
                        "separation_pages": separation_pages,
                        "source": "page_color_spaces",
                    },
                )
            )

        return findings
