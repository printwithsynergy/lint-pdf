"""PDF/X-1a color checks (PDFX1A-001-010).

Validates color space restrictions per ISO 15930-4:2003 section 6.2.4.
PDF/X-1a prohibits ALL RGB color spaces — only CMYK, DeviceGray,
Separation, and DeviceN are permitted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

_PREFIX = "PDFX1A"

# Valid rendering intents per ISO 32000-1
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
    from lintpdf.semantic.events import ColorChangedEvent, TextRenderedEvent

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

    # PDFX1A-001: RGB color space used (prohibited)
    if "DeviceRGB" in seen_color_spaces:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-001",
                severity=Severity.ERROR,
                message="DeviceRGB color space used (prohibited in PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.2.4",
            )
        )

    # PDFX1A-002: ICCBased RGB profile used (prohibited)
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 2 and str(cs_def[0]) == "ICCBased":
                    profile = cs_def[1] if len(cs_def) > 1 else None
                    if isinstance(profile, dict):
                        n_components = profile.get("/N") or profile.get("N")
                        if n_components == 3:
                            findings.append(
                                Finding(
                                    inspection_id=f"{_PREFIX}-002",
                                    severity=Severity.ERROR,
                                    message=(
                                        f"ICCBased RGB profile '{cs_name}' used "
                                        f"(prohibited in PDF/X-1a)"
                                    ),
                                    page_num=page.page_num,
                                    iso_clause="ISO 15930-4:2003 6.2.4",
                                )
                            )

    # PDFX1A-003: CalRGB used (prohibited)
    if "CalRGB" in seen_color_spaces:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-003",
                severity=Severity.ERROR,
                message="CalRGB color space used (prohibited in PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.2.4",
            )
        )

    # PDFX1A-004: CalGray used (prohibited, must be DeviceGray or ICCBased Gray)
    if "CalGray" in seen_color_spaces:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-004",
                severity=Severity.ERROR,
                message="CalGray color space used (prohibited in PDF/X-1a, use DeviceGray instead)",
                iso_clause="ISO 15930-4:2003 6.2.4",
            )
        )

    # PDFX1A-005: Lab color space used (prohibited)
    if "Lab" in seen_color_spaces:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-005",
                severity=Severity.ERROR,
                message="Lab color space used (prohibited in PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.2.4",
            )
        )

    # PDFX1A-006: Indexed color with RGB base (prohibited)
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 2 and str(cs_def[0]) == "Indexed":
                    base_cs = str(cs_def[1]) if len(cs_def) > 1 else ""
                    if base_cs in ("DeviceRGB", "CalRGB"):
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-006",
                                severity=Severity.ERROR,
                                message=(
                                    f"Indexed color space '{cs_name}' has RGB base "
                                    f"'{base_cs}' (prohibited in PDF/X-1a)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 15930-4:2003 6.2.4",
                            )
                        )
                    # Also check for ICCBased RGB base
                    if (
                        isinstance(cs_def[1], list)
                        and cs_def[1]
                        and str(cs_def[1][0]) == "ICCBased"
                    ):
                        base_profile = cs_def[1][1] if len(cs_def[1]) > 1 else None
                        if isinstance(base_profile, dict):
                            n = base_profile.get("/N") or base_profile.get("N")
                            if n == 3:
                                findings.append(
                                    Finding(
                                        inspection_id=f"{_PREFIX}-006",
                                        severity=Severity.ERROR,
                                        message=(
                                            f"Indexed color space '{cs_name}' has ICCBased RGB "
                                            f"base (prohibited in PDF/X-1a)"
                                        ),
                                        page_num=page.page_num,
                                        iso_clause="ISO 15930-4:2003 6.2.4",
                                    )
                                )

    # PDFX1A-007: Pattern color space without compatible base
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and cs_def and str(cs_def[0]) == "Pattern":
                    if len(cs_def) >= 2:
                        base_cs = str(cs_def[1])
                        if base_cs in ("DeviceRGB", "CalRGB", "Lab"):
                            findings.append(
                                Finding(
                                    inspection_id=f"{_PREFIX}-007",
                                    severity=Severity.ERROR,
                                    message=(
                                        f"Pattern color space '{cs_name}' has incompatible base "
                                        f"'{base_cs}' (prohibited in PDF/X-1a)"
                                    ),
                                    page_num=page.page_num,
                                    iso_clause="ISO 15930-4:2003 6.2.4",
                                )
                            )

    # PDFX1A-008: DeviceN with incompatible alternate
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 3 and str(cs_def[0]) == "DeviceN":
                    alt_space = str(cs_def[2])
                    if alt_space in ("DeviceRGB", "CalRGB", "Lab"):
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-008",
                                severity=Severity.ERROR,
                                message=(
                                    f"DeviceN color space '{cs_name}' has incompatible "
                                    f"alternate '{alt_space}' (prohibited in PDF/X-1a)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 15930-4:2003 6.2.4",
                            )
                        )

    # PDFX1A-009: Separation with RGB alternate (prohibited)
    for page in document.pages:
        cs_resources = page.resources.get("/ColorSpace") or page.resources.get("ColorSpace")
        if isinstance(cs_resources, dict):
            for cs_name, cs_def in cs_resources.items():
                if isinstance(cs_def, list) and len(cs_def) >= 3 and str(cs_def[0]) == "Separation":
                    alt_space = str(cs_def[2])
                    if alt_space in ("DeviceRGB", "CalRGB"):
                        findings.append(
                            Finding(
                                inspection_id=f"{_PREFIX}-009",
                                severity=Severity.ERROR,
                                message=(
                                    f"Separation color space '{cs_name}' has RGB alternate "
                                    f"'{alt_space}' (prohibited in PDF/X-1a)"
                                ),
                                page_num=page.page_num,
                                iso_clause="ISO 15930-4:2003 6.2.4",
                            )
                        )

    # PDFX1A-010: Invalid rendering intent
    for event in events:
        if isinstance(event, TextRenderedEvent):
            ri = event.rendering_intent
            if ri and ri not in _VALID_RENDERING_INTENTS:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-010",
                        severity=Severity.WARNING,
                        message=f"Invalid rendering intent '{ri}' on page {event.page_num}",
                        page_num=event.page_num,
                        iso_clause="ISO 15930-4:2003 6.2.4",
                    )
                )
                break  # One finding is enough

    return findings
