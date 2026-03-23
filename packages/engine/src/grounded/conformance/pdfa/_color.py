"""PDF/A color checks (PDFA-011-018).

Validates color space requirements per ISO 19005.
PDF/A requires device-independent color spaces or output intents
with ICC profiles for device-dependent color usage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFA"

# Valid rendering intents per ISO 32000-1
_VALID_RENDERING_INTENTS = {
    "AbsoluteColorimetric",
    "RelativeColorimetric",
    "Saturation",
    "Perceptual",
}

# Device-dependent color spaces
_DEVICE_DEPENDENT_SPACES = {"DeviceRGB", "DeviceCMYK", "DeviceGray"}


def validate_color(  # skipcq: PY-R1000
    document: SemanticDocument, events: list[ContentStreamEvent], level: str
) -> list[Finding]:
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

    # Check if output intent exists (needed to allow device-dependent spaces)
    has_output_intent = bool(document.output_intents)

    # PDFA-011: Device-dependent color space without fallback intent
    for cs in _DEVICE_DEPENDENT_SPACES:
        if cs in seen_color_spaces and not has_output_intent:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-011",
                    severity=Severity.ERROR,
                    message=(
                        f"Device-dependent color space '{cs}' used without an "
                        f"OutputIntent (required for PDF/A)"
                    ),
                    iso_clause="ISO 19005 6.2.4",
                )
            )

    # PDFA-012: Uncalibrated DeviceRGB/DeviceCMYK/DeviceGray without ICC or Output Intent
    for cs in _DEVICE_DEPENDENT_SPACES:
        if cs in seen_color_spaces:
            has_icc_fallback = _has_icc_profile_for_space(document, cs)
            if not has_icc_fallback and not has_output_intent:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-012",
                        severity=Severity.ERROR,
                        message=(
                            f"Uncalibrated '{cs}' used without ICC profile or OutputIntent "
                            f"(required for PDF/A)"
                        ),
                        iso_clause="ISO 19005 6.2.4",
                    )
                )

    # PDFA-013: Calibrated color space missing profile
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 2 and str(cs_def[0]) == "ICCBased":
                    profile = cs_def[1] if len(cs_def) > 1 else None
                    if profile is None:
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-013",
                                severity=Severity.ERROR,
                                message=(
                                    f"ICCBased color space '{cs_name}' missing ICC profile data"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 19005 6.2.4",
                            )
                        )

    # PDFA-014: ICC profile version too high
    _max_icc_version = 2 if level.startswith("1") else 4
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 2 and str(cs_def[0]) == "ICCBased":
                    profile = cs_def[1] if len(cs_def) > 1 else None
                    if isinstance(profile, dict):
                        icc_version = profile.get("/Version") or profile.get("Version")
                        if icc_version is not None:
                            try:
                                icc_ver_num = float(str(icc_version).split(".")[0])
                            except (ValueError, TypeError):
                                icc_ver_num = 0.0
                            if icc_ver_num > _max_icc_version:
                                findings.append(
                                    Finding(
                                        inspection_id=f"{_PREFIX}-014",
                                        severity=Severity.ERROR,
                                        message=(
                                            f"ICC profile version {icc_version} in '{cs_name}' "
                                            f"exceeds maximum v{_max_icc_version} "
                                            f"for PDF/A-{level[0]}"
                                        ),
                                        page_num=page.page_num,
                                        iso_clause=f"ISO 19005-{level[0]} 6.2.4",
                                        details={
                                            "icc_version": str(icc_version),
                                            "max_version": _max_icc_version,
                                        },
                                    )
                                )

    # PDFA-015: Rendering intent invalid
    for event in events:
        if isinstance(event, TextRenderedEvent):
            ri = event.rendering_intent
            if ri and ri not in _VALID_RENDERING_INTENTS:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-015",
                        severity=Severity.WARNING,
                        message=f"Invalid rendering intent '{ri}' on page {event.page_num}",
                        page_num=event.page_num,
                        iso_clause="ISO 19005 6.2.4",
                    )
                )
                break  # One finding is enough

    # PDFA-016: Separation/DeviceN without valid alternate
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if not isinstance(cs_def, list) or len(cs_def) < 3:
                    continue
                cs_type = str(cs_def[0])
                if cs_type == "Separation":
                    alt_space = str(cs_def[2])
                    if alt_space in _DEVICE_DEPENDENT_SPACES and not has_output_intent:
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-016",
                                severity=Severity.ERROR,
                                message=(
                                    f"Separation color space '{cs_name}' has device-dependent "
                                    f"alternate '{alt_space}' without OutputIntent"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 19005 6.2.4",
                            )
                        )
                elif cs_type == "DeviceN":
                    alt_space = str(cs_def[2])
                    if alt_space in _DEVICE_DEPENDENT_SPACES and not has_output_intent:
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-016",
                                severity=Severity.ERROR,
                                message=(
                                    f"DeviceN color space '{cs_name}' has device-dependent "
                                    f"alternate '{alt_space}' without OutputIntent"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 19005 6.2.4",
                            )
                        )

    # PDFA-017: Pattern color space with device-dependent base
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and cs_def and str(cs_def[0]) == "Pattern":
                    if len(cs_def) >= 2:
                        base_cs = str(cs_def[1])
                        if base_cs in _DEVICE_DEPENDENT_SPACES and not has_output_intent:
                            findings.append(
                                Finding(
                                    inspection_id=f"{_PREFIX}-017",
                                    severity=Severity.ERROR,
                                    message=(
                                        f"Pattern color space '{cs_name}' has device-dependent "
                                        f"base '{base_cs}' without OutputIntent"
                                    ),
                                    page_num=page.page_num,
                                    iso_clause="ISO 19005 6.2.4",
                                )
                            )

    # PDFA-018: Indexed color space with device-dependent base
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 2 and str(cs_def[0]) == "Indexed":
                    base_cs = str(cs_def[1])
                    if base_cs in _DEVICE_DEPENDENT_SPACES and not has_output_intent:
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-018",
                                severity=Severity.ERROR,
                                message=(
                                    f"Indexed color space '{cs_name}' has device-dependent "
                                    f"base '{base_cs}' without OutputIntent"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 19005 6.2.4",
                            )
                        )
                    # Also check for ICCBased base with missing profile
                    if (
                        isinstance(cs_def[1], list)
                        and cs_def[1]
                        and str(cs_def[1][0]) == "ICCBased"
                    ):
                        base_profile = cs_def[1][1] if len(cs_def[1]) > 1 else None
                        if base_profile is None:
                            findings.append(
                                Finding(
                                    inspection_id=f"{_PREFIX}-018",
                                    severity=Severity.ERROR,
                                    message=(
                                        f"Indexed color space '{cs_name}' has ICCBased base "
                                        f"with missing profile"
                                    ),
                                    page_num=page.page_num,
                                    iso_clause="ISO 19005 6.2.4",
                                )
                            )

    return findings


def _has_icc_profile_for_space(document: SemanticDocument, color_space: str) -> bool:
    """Check if any page defines an ICCBased profile that covers the given space."""
    n_components_map = {"DeviceRGB": 3, "DeviceCMYK": 4, "DeviceGray": 1}
    target_n = n_components_map.get(color_space)
    if target_n is None:
        return False

    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for _cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 2 and str(cs_def[0]) == "ICCBased":
                    profile = cs_def[1] if len(cs_def) > 1 else None
                    if isinstance(profile, dict):
                        n = profile.get("/N") or profile.get("N")
                        if n == target_n:
                            return True
    return False
