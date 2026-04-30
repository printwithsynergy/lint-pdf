"""DocumentAnalyzer — document-level consistency and metadata checks.

Inspects document-wide properties for print workflow issues:
mixed page sizes, inconsistent rotation, missing metadata, encryption.

Check IDs:
    LPDF_DOC_001 — Mixed page sizes
    LPDF_DOC_002 — Inconsistent page rotation
    LPDF_DOC_003 — Missing document title
    LPDF_DOC_004 — Document is encrypted
    LPDF_DOC_005 — Linearized PDF detected
    LPDF_DOC_006 — Incremental updates detected
    LPDF_DOC_007 — File size exceeds threshold
    LPDF_DOC_008 — Pre-separated pages detected
    LPDF_DOC_009 — PDF version outside profile range (T1-CMP02)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from siftpdf.analyzers.base import BaseAnalyzer
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument


# Default maximum file size: 500 MB
DEFAULT_MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024


def _parse_version(version: str) -> tuple[int, int] | None:
    """Parse a PDF version string like '1.6' or '2.0' into a comparable tuple.

    Returns ``None`` when the string doesn't look like a PDF version header.
    """
    if not version:
        return None
    try:
        parts = version.strip().split(".")
        if len(parts) != 2:
            return None
        return int(parts[0]), int(parts[1])
    except (ValueError, AttributeError):
        return None


class DocumentAnalyzer(BaseAnalyzer):
    """Analyzer for document-level consistency checks.

    Args:
        max_file_size_bytes: Maximum file size threshold in bytes (default 500MB).
        min_pdf_version: Lowest acceptable PDF header version (e.g. '1.6').
            ``None`` disables the lower-bound check.
        max_pdf_version: Highest acceptable PDF header version (e.g. '1.4').
            ``None`` disables the upper-bound check.
        profile_name: Active preflight profile name for messaging.
    """

    def __init__(
        self,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        min_pdf_version: str | None = None,
        max_pdf_version: str | None = None,
        profile_name: str | None = None,
    ) -> None:
        self.max_file_size_bytes = max_file_size_bytes
        self.min_pdf_version = min_pdf_version
        self.max_pdf_version = max_pdf_version
        self.profile_name = profile_name

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze document-level properties."""
        findings: list[Finding] = []

        # LPDF_DOC_004: Encryption
        if document.is_encrypted:
            findings.append(
                Finding(
                    inspection_id="LPDF_DOC_004",
                    severity=Severity.ERROR,
                    message="Document is encrypted (not allowed in print workflows)",
                    iso_clause="ISO 15930-7:2010 6.2.2",
                )
            )

        # LPDF_DOC_003: Missing title
        title = document.info_dict.get("/Title") or document.info_dict.get("Title")
        if not title:
            findings.append(
                Finding(
                    inspection_id="LPDF_DOC_003",
                    severity=Severity.ADVISORY,
                    message="Document has no title in Info dictionary",
                    iso_clause="ISO 32000-2:2020 14.3.3",
                )
            )

        # LPDF_DOC_005: Linearized PDF
        is_linearized = (
            document.catalog.get("/Linearized") is not None
            or document.trailer.get("/Linearized") is not None
        )
        if is_linearized:
            findings.append(
                Finding(
                    inspection_id="LPDF_DOC_005",
                    severity=Severity.ADVISORY,
                    message="Linearized PDF detected (web-optimized, may need re-saving for print)",
                    iso_clause="ISO 32000-2:2020 Annex F",
                )
            )

        # LPDF_DOC_006: Incremental updates
        if document.trailer.get("/Prev") is not None:
            findings.append(
                Finding(
                    inspection_id="LPDF_DOC_006",
                    severity=Severity.ADVISORY,
                    message=(
                        "Incremental updates detected (trailer has /Prev reference, "
                        "file may contain stale data)"
                    ),
                    iso_clause="ISO 32000-2:2020 7.5.6",
                )
            )

        # LPDF_DOC_007: File size exceeds threshold
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
                        inspection_id="LPDF_DOC_007",
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

        # LPDF_DOC_008: Pre-separated pages detected
        findings.extend(self._check_pre_separated_pages(document))

        # LPDF_DOC_009: PDF version vs profile range (T1-CMP02).
        # Fire independent of page count — a single-page PDF can still be
        # version-out-of-range for its workflow.
        findings.extend(self._check_pdf_version_against_profile(document))

        if len(document.pages) < 2:
            return findings

        # LPDF_DOC_001: Mixed page sizes
        sizes: set[tuple[float, float]] = set()
        for page in document.pages:
            w = round(page.media_box.width, 1)
            h = round(page.media_box.height, 1)
            sizes.add((w, h))

        if len(sizes) > 1:
            findings.append(
                Finding(
                    inspection_id="LPDF_DOC_001",
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

        # LPDF_DOC_002: Inconsistent rotation
        rotations: set[int] = set()
        for page in document.pages:
            rotations.add(page.rotate)

        if len(rotations) > 1:
            findings.append(
                Finding(
                    inspection_id="LPDF_DOC_002",
                    severity=Severity.ADVISORY,
                    message=(f"Document has inconsistent page rotations: {sorted(rotations)}"),
                    details={
                        "rotations": sorted(rotations),
                    },
                )
            )

        return findings

    def _check_pdf_version_against_profile(self, document: SemanticDocument) -> list[Finding]:
        """LPDF_DOC_009 — PDF version vs profile range (T1-CMP02).

        Fires when the active profile declares ``min_pdf_version`` or
        ``max_pdf_version`` and the document header version sits outside
        that range. Both constraints are optional; absence of both means
        this check silently no-ops (back-compat with profiles that
        predate the fields).

        Note that this is DISTINCT from LPDF_META_004, which checks
        internal consistency (header vs XMP). This check compares the
        header version to the workflow's expected range.
        """
        if self.min_pdf_version is None and self.max_pdf_version is None:
            return []

        version_str = document.version or ""
        actual = _parse_version(version_str)
        if actual is None:
            return []

        profile_label = self.profile_name or "profile"

        if self.min_pdf_version:
            min_v = _parse_version(self.min_pdf_version)
            if min_v is not None and actual < min_v:
                return [
                    Finding(
                        inspection_id="LPDF_DOC_009",
                        severity=Severity.WARNING,
                        message=(
                            f"PDF version {version_str} is below the {profile_label} "
                            f"minimum ({self.min_pdf_version})"
                        ),
                        details={
                            "pdf_version": version_str,
                            "min_pdf_version": self.min_pdf_version,
                            "max_pdf_version": self.max_pdf_version,
                            "profile_name": self.profile_name,
                            "failure_mode": "below_minimum",
                        },
                        iso_clause="ISO 32000-2:2020 7.5.2",
                    )
                ]

        if self.max_pdf_version:
            max_v = _parse_version(self.max_pdf_version)
            if max_v is not None and actual > max_v:
                return [
                    Finding(
                        inspection_id="LPDF_DOC_009",
                        severity=Severity.WARNING,
                        message=(
                            f"PDF version {version_str} is above the {profile_label} "
                            f"maximum ({self.max_pdf_version})"
                        ),
                        details={
                            "pdf_version": version_str,
                            "min_pdf_version": self.min_pdf_version,
                            "max_pdf_version": self.max_pdf_version,
                            "profile_name": self.profile_name,
                            "failure_mode": "above_maximum",
                        },
                        iso_clause="ISO 32000-2:2020 7.5.2",
                    )
                ]

        return []

    @staticmethod
    def _check_pre_separated_pages(document: SemanticDocument) -> list[Finding]:
        """Check for pre-separated pages (LPDF_DOC_008).

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
                    inspection_id="LPDF_DOC_008",
                    severity=Severity.WARNING,
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
                    inspection_id="LPDF_DOC_008",
                    severity=Severity.WARNING,
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
