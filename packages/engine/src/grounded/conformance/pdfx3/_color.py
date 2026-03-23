"""PDF/X-3 color checks (PDFX3-001 through PDFX3-008).

Validates color space restrictions per ISO 15930-6:2003 section 6.2.4.

Key difference from PDF/X-1a: ICC-based RGB IS allowed, Lab IS allowed.
DeviceRGB without ICC profile is still prohibited.
CalRGB and CalGray are still prohibited.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX3"

# Valid rendering intents per ISO 32000-1
_VALID_RENDERING_INTENTS = {
    "AbsoluteColorimetric",
    "RelativeColorimetric",
    "Saturation",
    "Perceptual",
}


def validate_color(  # skipcq: PY-R1000
    document: SemanticDocument, events: list[ContentStreamEvent]
) -> list[Finding]:
    """Run color conformance checks for PDF/X-3."""
    from grounded.semantic.events import ColorChangedEvent, TextRenderedEvent

    findings: list[Finding] = []
    seen_color_spaces: set[str] = set()

    for event in events:
        if isinstance(event, (ColorChangedEvent, TextRenderedEvent)):
            seen_color_spaces.add(event.color_space)

    # Also check page resources for color space definitions
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for _cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, str):
                    seen_color_spaces.add(cs_def)
                elif isinstance(cs_def, list) and cs_def:
                    seen_color_spaces.add(str(cs_def[0]))

    # PDFX3-001: DeviceRGB without ICC profile (prohibited)
    # In PDF/X-3, DeviceRGB is not allowed — ICC-based RGB must be used instead.
    has_rgb_intent = _has_color_space_intent(document, "RGB")
    if "DeviceRGB" in seen_color_spaces and not has_rgb_intent:
        has_default_rgb = any(
            (page.resources.get("/ColorSpace") or page.resources.get("ColorSpace") or {}).get(
                "/DefaultRGB"
            )
            is not None
            for page in document.pages
        )
        if not has_default_rgb:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-001",
                    severity=Severity.ERROR,
                    message=(
                        "DeviceRGB used without ICC profile output intent or DefaultRGB "
                        "(prohibited in PDF/X-3, use ICCBased RGB instead)"
                    ),
                    iso_clause="ISO 15930-6:2003 6.2.4",
                )
            )

    # PDFX3-002: CalRGB prohibited
    if "CalRGB" in seen_color_spaces:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-002",
                severity=Severity.ERROR,
                message="CalRGB color space used (prohibited in PDF/X-3, use ICCBased instead)",
                iso_clause="ISO 15930-6:2003 6.2.4",
            )
        )

    # PDFX3-003: CalGray prohibited
    if "CalGray" in seen_color_spaces:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-003",
                severity=Severity.ERROR,
                message="CalGray color space used (prohibited in PDF/X-3, use ICCBased instead)",
                iso_clause="ISO 15930-6:2003 6.2.4",
            )
        )

    # PDFX3-004: Indexed color with device-dependent RGB base
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 2:
                    cs_type = str(cs_def[0])
                    if cs_type == "Indexed" and len(cs_def) >= 2:
                        base = str(cs_def[1])
                        if base == "DeviceRGB":
                            findings.append(
                                Finding(
                                    inspection_id=f"{_PREFIX}-004",
                                    severity=Severity.ERROR,
                                    message=(
                                        f"Indexed color space '{cs_name}' uses DeviceRGB base "
                                        f"(prohibited in PDF/X-3)"
                                    ),
                                    page_num=page.page_num,
                                    iso_clause="ISO 15930-6:2003 6.2.4",
                                )
                            )

    # PDFX3-005: Separation with non-CMYK/Gray/Lab alternate
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 3:
                    cs_type = str(cs_def[0])
                    if cs_type == "Separation":
                        alt_space = str(cs_def[2])
                        allowed_alternates = {
                            "DeviceCMYK", "DeviceGray", "ICCBased", "Lab",
                        }
                        if alt_space not in allowed_alternates:
                            findings.append(
                                Finding(
                                    inspection_id=f"{_PREFIX}-005",
                                    severity=Severity.WARNING,
                                    message=(
                                        f"Separation '{cs_name}' has alternate space "
                                        f"'{alt_space}' (expected CMYK, Gray, Lab, or ICCBased)"
                                    ),
                                    page_num=page.page_num,
                                    iso_clause="ISO 15930-6:2003 6.2.4.5",
                                )
                            )

    # PDFX3-006: DeviceN with incompatible alternate
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 3:
                    cs_type = str(cs_def[0])
                    if cs_type == "DeviceN":
                        alt_space = str(cs_def[2])
                        allowed_alternates = {
                            "DeviceCMYK", "DeviceGray", "ICCBased", "Lab",
                        }
                        if alt_space not in allowed_alternates:
                            findings.append(
                                Finding(
                                    inspection_id=f"{_PREFIX}-006",
                                    severity=Severity.WARNING,
                                    message=(
                                        f"DeviceN '{cs_name}' has alternate space "
                                        f"'{alt_space}' (expected CMYK, Gray, Lab, or ICCBased)"
                                    ),
                                    page_num=page.page_num,
                                    iso_clause="ISO 15930-6:2003 6.2.4.5",
                                )
                            )

    # PDFX3-007: Pattern with device-dependent base
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 2:
                    cs_type = str(cs_def[0])
                    if cs_type == "Pattern":
                        base = str(cs_def[1])
                        if base == "DeviceRGB":
                            findings.append(
                                Finding(
                                    inspection_id=f"{_PREFIX}-007",
                                    severity=Severity.ERROR,
                                    message=(
                                        f"Pattern '{cs_name}' uses DeviceRGB base "
                                        f"(prohibited in PDF/X-3)"
                                    ),
                                    page_num=page.page_num,
                                    iso_clause="ISO 15930-6:2003 6.2.4",
                                )
                            )

    # PDFX3-008: Invalid rendering intent
    for event in events:
        if isinstance(event, TextRenderedEvent):
            ri = event.rendering_intent
            if ri and ri not in _VALID_RENDERING_INTENTS:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-008",
                        severity=Severity.WARNING,
                        message=f"Invalid rendering intent '{ri}' on page {event.page_num}",
                        page_num=event.page_num,
                        iso_clause="ISO 15930-6:2003 6.2.4",
                    )
                )
                break  # One finding is enough

    return findings


def _has_color_space_intent(
    document: SemanticDocument, color_space: str
) -> bool:
    """Check if any output intent matches the given color space."""
    for intent in document.output_intents:
        dest_profile = intent.get("/DestOutputProfile") or intent.get("DestOutputProfile")
        if isinstance(dest_profile, dict):
            icc_cs = dest_profile.get("/ColorSpace") or dest_profile.get("ColorSpace") or ""
            if color_space.lower() in icc_cs.lower():
                return True
        # Also check output condition identifier for known conditions
        oci = intent.get("/OutputConditionIdentifier") or intent.get("OutputConditionIdentifier")
        if oci and isinstance(oci, str) and color_space.upper() in oci.upper():
            return True
    return False
