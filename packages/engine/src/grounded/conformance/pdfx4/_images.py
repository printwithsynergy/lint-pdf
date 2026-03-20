"""PDF/X-4 image checks (PDFX4-079-087).

Validates image restrictions per ISO 15930-7:2010 section 6.2.6 and 6.6.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX4"


def validate_images(
    document: SemanticDocument, events: list[ContentStreamEvent]
) -> list[Finding]:  # skipcq: PY-R1000
    """Run image conformance checks."""
    from grounded.semantic.events import ImagePlacedEvent

    findings: list[Finding] = []

    for event in events:
        if not isinstance(event, ImagePlacedEvent):
            continue

        pn = event.page_num
        name = event.image_name

        # PDFX4-079: No LZW compression
        if "LZWDecode" in event.filters:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-079",
                    severity=Severity.SQUALL,
                    message=f"Image '{name}' uses LZW compression on page {pn} (deprecated in PDF/X-4)",
                    page_num=pn,
                    iso_clause="ISO 15930-7:2010 6.6",
                    object_id=name,
                    object_type="image",
                )
            )

        # PDFX4-080 (image streams): covered by file_structure

        # PDFX4-081 (image refs): covered by file_structure

        # PDFX4-082: No OPI references
        if event.has_opi:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-082i",
                    severity=Severity.AGROUND,
                    message=f"Image '{name}' has OPI reference on page {pn} (prohibited in PDF/X-4)",
                    page_num=pn,
                    iso_clause="ISO 15930-7:2010 6.6.3",
                    object_id=name,
                    object_type="image",
                )
            )

        # PDFX4-083i: No alternate images
        if event.has_alternate:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-083i",
                    severity=Severity.SQUALL,
                    message=f"Image '{name}' has alternate images on page {pn} (prohibited in PDF/X-4)",
                    page_num=pn,
                    iso_clause="ISO 15930-7:2010 6.6.4",
                    object_id=name,
                    object_type="image",
                )
            )

        # PDFX4-084i: ICC profile version in image color space
        # Checked at the color space level (see _color.py)

        # PDFX4-085: Color space compatible with output intent
        # Basic check — DeviceRGB images should have RGB intent
        if event.color_space == "DeviceRGB":
            has_rgb_intent = any(
                "RGB"
                in str(
                    (i.get("/DestOutputProfile") or i.get("DestOutputProfile") or {}).get(
                        "/ColorSpace", ""
                    )
                )
                for i in document.output_intents
            )
            if not has_rgb_intent:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-085",
                        severity=Severity.ADVISORY,
                        message=(f"RGB image '{name}' on page {pn} without RGB output intent"),
                        page_num=pn,
                        iso_clause="ISO 15930-7:2010 6.2.4",
                        object_id=name,
                        object_type="image",
                    )
                )

        # PDFX4-086: Inline images max 4KB
        if event.is_inline:
            # Approximate size: pixel_width * pixel_height * bits_per_component / 8
            approx_size = event.pixel_width * event.pixel_height * event.bits_per_component // 8
            if approx_size > 4096:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-086",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Inline image on page {pn} exceeds 4KB recommended maximum "
                            f"(~{approx_size} bytes)"
                        ),
                        page_num=pn,
                        iso_clause="ISO 32000-2:2020 8.9.7",
                        object_type="image",
                    )
                )

        # PDFX4-087: JPEG2000 profile
        if "JPXDecode" in event.filters:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-087",
                    severity=Severity.ADVISORY,
                    message=f"JPEG2000 image '{name}' on page {pn} (verify JPX profile compatibility)",
                    page_num=pn,
                    iso_clause="ISO 15930-7:2010 6.6.2",
                    object_id=name,
                    object_type="image",
                )
            )

    return findings
