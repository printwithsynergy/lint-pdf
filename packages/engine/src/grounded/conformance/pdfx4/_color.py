"""PDF/X-4 color checks (PDFX4-026-035).

Validates color space restrictions per ISO 15930-7:2010 section 6.2.4.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX4"

# Prohibited device-dependent color spaces in PDF/X-4 without output intent
_CALIBRATED_PROHIBITED = {"CalGray", "CalRGB"}

# Valid rendering intents per ISO 32000-2
_VALID_RENDERING_INTENTS = {
    "AbsoluteColorimetric",
    "RelativeColorimetric",
    "Saturation",
    "Perceptual",
}


def validate_color(
    document: SemanticDocument, events: list[ContentStreamEvent]
) -> list[Finding]:  # skipcq: PY-R1000
    """Run color conformance checks."""
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

    # PDFX4-026: CalGray prohibited
    if "CalGray" in seen_color_spaces:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-026",
                severity=Severity.SQUALL,
                message="CalGray color space used (prohibited in PDF/X-4, use ICCBased instead)",
                iso_clause="ISO 15930-7:2010 6.2.4",
            )
        )

    # PDFX4-027: CalRGB prohibited
    if "CalRGB" in seen_color_spaces:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-027",
                severity=Severity.SQUALL,
                message="CalRGB color space used (prohibited in PDF/X-4, use ICCBased instead)",
                iso_clause="ISO 15930-7:2010 6.2.4",
            )
        )

    # PDFX4-028: DeviceRGB restricted
    # DeviceRGB is allowed only when an RGB output intent is present or
    # a DefaultRGB is defined. We flag it as advisory.
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
                    inspection_id=f"{_PREFIX}-028",
                    severity=Severity.SQUALL,
                    message=(
                        "DeviceRGB used without RGB output intent or DefaultRGB "
                        "(device-dependent color not recommended for PDF/X-4)"
                    ),
                    iso_clause="ISO 15930-7:2010 6.2.4.3",
                )
            )

    # PDFX4-029: DeviceCMYK restricted
    has_cmyk_intent = _has_color_space_intent(document, "CMYK")
    if "DeviceCMYK" in seen_color_spaces and not has_cmyk_intent:
        has_default_cmyk = any(
            (page.resources.get("/ColorSpace") or page.resources.get("ColorSpace") or {}).get(
                "/DefaultCMYK"
            )
            is not None
            for page in document.pages
        )
        if not has_default_cmyk:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-029",
                    severity=Severity.ADVISORY,
                    message="DeviceCMYK used without CMYK output intent or DefaultCMYK",
                    iso_clause="ISO 15930-7:2010 6.2.4.3",
                )
            )

    # PDFX4-030: DeviceGray restricted (same pattern)
    if "DeviceGray" in seen_color_spaces:
        has_gray_intent = _has_color_space_intent(document, "Gray")
        has_default_gray = any(
            (page.resources.get("/ColorSpace") or page.resources.get("ColorSpace") or {}).get(
                "/DefaultGray"
            )
            is not None
            for page in document.pages
        )
        if not has_gray_intent and not has_default_gray:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-030",
                    severity=Severity.ADVISORY,
                    message="DeviceGray used without Gray output intent or DefaultGray",
                    iso_clause="ISO 15930-7:2010 6.2.4.3",
                )
            )

    # PDFX4-031: ICCBased profiles must be valid
    # Checked at page resource level — look for ICCBased entries
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 2 and str(cs_def[0]) == "ICCBased":
                    profile = cs_def[1] if len(cs_def) > 1 else None
                    if isinstance(profile, dict):
                        n_components = profile.get("/N") or profile.get("N")
                        if n_components is not None and n_components not in (1, 3, 4):
                            findings.append(
                                Finding(
                                    inspection_id=f"{_PREFIX}-031",
                                    severity=Severity.SQUALL,
                                    message=(
                                        f"ICCBased profile '{cs_name}' has {n_components} "
                                        f"components (expected 1, 3, or 4)"
                                    ),
                                    page_num=page.page_num,
                                    iso_clause="ISO 15930-7:2010 6.2.4.4",
                                )
                            )

    # PDFX4-032: Separation color space consistency
    # Check that Separation and DeviceN alternate spaces are consistent
    separation_alternates: dict[str, set[str]] = {}
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for _cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 3:
                    cs_type = str(cs_def[0])
                    if cs_type == "Separation" and len(cs_def) >= 3:
                        colorant_name = str(cs_def[1])
                        alt_space = str(cs_def[2])
                        separation_alternates.setdefault(colorant_name, set()).add(alt_space)

    for colorant, alternates in separation_alternates.items():
        if len(alternates) > 1:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-032",
                    severity=Severity.SQUALL,
                    message=(
                        f"Separation colorant '{colorant}' has inconsistent "
                        f"alternate spaces: {sorted(alternates)}"
                    ),
                    iso_clause="ISO 15930-7:2010 6.2.4.5",
                    details={"colorant": colorant, "alternates": sorted(alternates)},
                )
            )

    # PDFX4-033: DeviceN consistency
    # Similar check for DeviceN color spaces
    devicen_found = False
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for _cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and cs_def and str(cs_def[0]) == "DeviceN":
                    devicen_found = True

    if devicen_found:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-033",
                severity=Severity.ADVISORY,
                message="DeviceN color space detected (verify colorant consistency)",
                iso_clause="ISO 15930-7:2010 6.2.4.5",
            )
        )

    # PDFX4-034: Lab color space (allowed but noted)
    if "Lab" in seen_color_spaces:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-034",
                severity=Severity.ADVISORY,
                message="Lab color space used",
                iso_clause="ISO 15930-7:2010 6.2.4",
            )
        )

    # PDFX4-035: Rendering intent validity
    for event in events:
        if isinstance(event, TextRenderedEvent):
            ri = event.rendering_intent
            if ri and ri not in _VALID_RENDERING_INTENTS:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-035",
                        severity=Severity.SQUALL,
                        message=f"Invalid rendering intent '{ri}' on page {event.page_num}",
                        page_num=event.page_num,
                        iso_clause="ISO 32000-2:2020 8.6.5.8",
                    )
                )
                break  # One finding is enough

    return findings


def _has_color_space_intent(
    document: SemanticDocument, color_space: str
) -> bool:  # skipcq: PY-R1000
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
