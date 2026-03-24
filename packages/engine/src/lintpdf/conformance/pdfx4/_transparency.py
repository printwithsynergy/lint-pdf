"""PDF/X-4 transparency checks (PDFX4-043-048).

Validates transparency constraints per ISO 15930-7:2010 section 6.2.5.
PDF/X-4 allows transparency (unlike PDF/X-1a) but constrains it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

_PREFIX = "PDFX4"

# Standard blend modes per ISO 32000-2:2020 11.3.5
_STANDARD_BLEND_MODES = {
    "Normal",
    "Compatible",
    "Multiply",
    "Screen",
    "Overlay",
    "Darken",
    "Lighten",
    "ColorDodge",
    "ColorBurn",
    "HardLight",
    "SoftLight",
    "Difference",
    "Exclusion",
    "Hue",
    "Saturation",
    "Color",
    "Luminosity",
}


def validate_transparency(  # skipcq: PY-R1000
    document: SemanticDocument, events: list[ContentStreamEvent]
) -> list[Finding]:
    """Run transparency conformance checks."""
    from lintpdf.semantic.events import OpacityChangedEvent

    findings: list[Finding] = []
    has_transparency = False

    for event in events:
        if isinstance(event, OpacityChangedEvent):
            sa = event.stroking_alpha
            nsa = event.non_stroking_alpha
            if (sa is not None and sa < 1.0) or (nsa is not None and nsa < 1.0):
                has_transparency = True

            # PDFX4-046: Standard blend modes only
            if event.blend_mode and event.blend_mode not in _STANDARD_BLEND_MODES:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-046",
                        severity=Severity.ERROR,
                        message=(
                            f"Non-standard blend mode '{event.blend_mode}' on page {event.page_num}"
                        ),
                        page_num=event.page_num,
                        iso_clause="ISO 32000-2:2020 11.3.5",
                    )
                )

    # PDFX4-043: Transparency allowed (informational)
    if has_transparency:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-043",
                severity=Severity.ADVISORY,
                message="Document uses transparency (allowed in PDF/X-4 but verify flatten compatibility)",
                iso_clause="ISO 15930-7:2010 6.2.5",
            )
        )

    # PDFX4-044: Transparency group /CS consistent with output intent
    for page in document.pages:
        group = page.transparency_group
        if group is None:
            continue

        cs = group.get("/CS") or group.get("CS") or ""
        if not cs:
            continue

        # PDFX4-045: Group color space should match page or output intent
        # Check that group CS is compatible
        if isinstance(cs, str) and cs.startswith("/"):
            cs = cs[1:]

        output_cs = _get_output_intent_cs(document)
        if output_cs and cs and cs != output_cs and _cs_families_conflict(cs, output_cs):
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-044",
                    severity=Severity.WARNING,
                    message=(
                        f"Transparency group /CS '{cs}' on page {page.page_num} "
                        f"conflicts with output intent color space '{output_cs}'"
                    ),
                    page_num=page.page_num,
                    iso_clause="ISO 15930-7:2010 6.2.5",
                )
            )

    # PDFX4-047: Soft mask /CS compatible
    for page in document.pages:
        group = page.transparency_group
        if group is None:
            continue
        # Soft mask groups should have compatible CS
        sm_cs = group.get("/SMaskCS") or group.get("SMaskCS")
        if sm_cs:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-047",
                    severity=Severity.ADVISORY,
                    message=f"Soft mask color space present on page {page.page_num}",
                    page_num=page.page_num,
                    iso_clause="ISO 15930-7:2010 6.2.5",
                )
            )

    # PDFX4-048: Transparency group isolation/knockout noted
    for page in document.pages:
        group = page.transparency_group
        if group is None:
            continue
        isolated = group.get("/I", False)
        knockout = group.get("/K", False)
        if isolated and knockout:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-048",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Isolated knockout transparency group on page {page.page_num} "
                        f"(verify rendering intent)"
                    ),
                    page_num=page.page_num,
                    iso_clause="ISO 32000-2:2020 11.4.7",
                )
            )

    return findings


def _get_output_intent_cs(document: SemanticDocument) -> str:
    """Get color space from first GTS_PDFX output intent."""
    for intent in document.output_intents:
        s = intent.get("/S") or intent.get("S") or ""
        if "GTS_PDFX" in s:
            dest = intent.get("/DestOutputProfile") or intent.get("DestOutputProfile")
            if isinstance(dest, dict):
                return dest.get("/ColorSpace") or dest.get("ColorSpace") or ""
    return ""


def _cs_families_conflict(cs1: str, cs2: str) -> bool:
    """Check if two color spaces are from conflicting families."""
    rgb_names = {"DeviceRGB", "RGB", "sRGB", "AdobeRGB"}
    cmyk_names = {"DeviceCMYK", "CMYK"}

    cs1_rgb = any(n in cs1 for n in rgb_names)
    cs1_cmyk = any(n in cs1 for n in cmyk_names)
    cs2_rgb = any(n in cs2 for n in rgb_names)
    cs2_cmyk = any(n in cs2 for n in cmyk_names)

    return (cs1_rgb and cs2_cmyk) or (cs1_cmyk and cs2_rgb)
