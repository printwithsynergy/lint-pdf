"""PDF/X-4 page box checks (PDFX4-049-056).

Validates page box requirements per ISO 15930-7:2010 section 6.2.1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.model import SemanticDocument

_PREFIX = "PDFX4"


def validate_boxes(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
    """Run page box conformance checks."""
    findings: list[Finding] = []

    for page in document.pages:
        pn = page.page_num

        # PDFX4-049: MediaBox required
        if page.media_box is None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-049",
                    severity=Severity.ERROR,
                    message=f"MediaBox missing on page {pn}",
                    page_num=pn,
                    iso_clause="ISO 32000-2:2020 14.11.2",
                )
            )

        # PDFX4-050: TrimBox or ArtBox required
        has_trim = page.trim_box is not None
        has_art = page.art_box is not None
        if not has_trim and not has_art:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-050",
                    severity=Severity.ERROR,
                    message=f"Neither TrimBox nor ArtBox present on page {pn} (one required for PDF/X-4)",
                    page_num=pn,
                    iso_clause="ISO 15930-7:2010 6.2.1",
                )
            )

        # PDFX4-051: TrimBox and ArtBox must not both be present (with different values)
        if has_trim and has_art and page.trim_box != page.art_box:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-051",
                    severity=Severity.WARNING,
                    message=f"Both TrimBox and ArtBox present with different values on page {pn}",
                    page_num=pn,
                    iso_clause="ISO 15930-7:2010 6.2.1",
                )
            )

        # PDFX4-052: BleedBox within CropBox/MediaBox
        if page.bleed_box is not None:
            container = page.crop_box or page.media_box
            if container is not None and not container.contains_box(page.bleed_box):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-052",
                        severity=Severity.WARNING,
                        message=f"BleedBox extends outside CropBox/MediaBox on page {pn}",
                        page_num=pn,
                        iso_clause="ISO 32000-2:2020 14.11.2",
                    )
                )

        # PDFX4-053: TrimBox within BleedBox (or CropBox if no BleedBox)
        if page.trim_box is not None:
            container = page.bleed_box or page.crop_box or page.media_box
            if container is not None and not container.contains_box(page.trim_box):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-053",
                        severity=Severity.WARNING,
                        message=f"TrimBox extends outside BleedBox on page {pn}",
                        page_num=pn,
                        iso_clause="ISO 32000-2:2020 14.11.2",
                    )
                )

        # PDFX4-054: All boxes well-formed (non-zero area)
        for box_name, box in [
            ("MediaBox", page.media_box),
            ("CropBox", page.crop_box),
            ("BleedBox", page.bleed_box),
            ("TrimBox", page.trim_box),
            ("ArtBox", page.art_box),
        ]:
            if box is not None and (box.width <= 0 or box.height <= 0):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-054",
                        severity=Severity.ERROR,
                        message=f"{box_name} has zero or negative dimensions on page {pn}",
                        page_num=pn,
                        iso_clause="ISO 32000-2:2020 14.11.2",
                        details={
                            "box_name": box_name,
                            "width": box.width,
                            "height": box.height,
                        },
                    )
                )

        # PDFX4-055: CropBox within MediaBox
        if (
            page.crop_box is not None
            and page.media_box is not None
            and not page.media_box.contains_box(page.crop_box)
        ):
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-055",
                    severity=Severity.WARNING,
                    message=f"CropBox extends outside MediaBox on page {pn}",
                    page_num=pn,
                    iso_clause="ISO 32000-2:2020 14.11.2",
                )
            )

        # PDFX4-056: ArtBox within TrimBox or BleedBox
        if page.art_box is not None:
            container = page.trim_box or page.bleed_box or page.crop_box or page.media_box
            if container is not None and not container.contains_box(page.art_box):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-056",
                        severity=Severity.WARNING,
                        message=f"ArtBox extends outside container box on page {pn}",
                        page_num=pn,
                        iso_clause="ISO 32000-2:2020 14.11.2",
                    )
                )

    return findings
