"""JDF/XJDF job ticket parser.

Extracts preflight-relevant parameters from JDF (Job Definition Format)
and XJDF (XML JDF) job tickets to auto-configure preflight profiles.

Supported fields:
- Output condition / ICC profile
- Media type / substrate
- Trim size / bleed requirements
- Color requirements (CMYK, spot colors)
- Conformance standard (PDF/X-1a, X-3, X-4)
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JobTicketParams:
    """Parameters extracted from a JDF/XJDF job ticket."""
    conformance: str | None = None  # e.g., "pdfx4", "pdfx1a"
    output_condition: str = ""
    media_type: str = ""
    trim_width_mm: float = 0.0
    trim_height_mm: float = 0.0
    bleed_mm: float = 3.0
    color_type: str = "CMYK"  # CMYK, spot, etc.
    spot_colors: list[str] = field(default_factory=list)
    min_dpi: float = 0.0
    max_ink_coverage: float = 0.0
    copies: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


def parse_jdf(jdf_xml: str | bytes) -> JobTicketParams:
    """Parse a JDF/XJDF job ticket XML and extract preflight parameters."""
    params = JobTicketParams()

    try:
        if isinstance(jdf_xml, str):
            root = ET.fromstring(jdf_xml)
        else:
            root = ET.fromstring(jdf_xml.decode("utf-8"))
    except ET.ParseError:
        return params

    ns = {"jdf": "http://www.CIP4.org/JDFSchema_1_1"}

    # Try JDF namespace first, then plain
    for prefix in [ns, {}]:
        _extract_jdf_params(root, params, prefix)

    return params


def _extract_jdf_params(
    root: ET.Element,
    params: JobTicketParams,
    ns: dict[str, str],
) -> None:
    """Extract parameters from JDF XML tree."""
    # Media/substrate
    for media in root.iter("Media"):
        params.media_type = media.get("MediaType", params.media_type)
        dim = media.get("Dimension", "")
        if dim:
            parts = dim.split()
            if len(parts) >= 2:
                try:
                    # JDF dimensions are in points
                    params.trim_width_mm = float(parts[0]) * 0.352778
                    params.trim_height_mm = float(parts[1]) * 0.352778
                except ValueError:
                    pass

    # Color intent
    for ci in root.iter("ColorIntent"):
        params.color_type = ci.get("NumColors", params.color_type)
        for sc in ci.iter("SeparationSpec"):
            name = sc.get("Name", "")
            if name:
                params.spot_colors.append(name)

    # Output condition from ColorSpaceConversionParams
    for csc in root.iter("ColorSpaceConversionParams"):
        oci = csc.get("FinalTargetDevice", "")
        if oci:
            params.output_condition = oci

    # Layout/bleed
    for layout in root.iter("LayoutPreparationParams"):
        bleed = layout.get("BleedMargin", "")
        if bleed:
            try:
                params.bleed_mm = float(bleed) * 0.352778
            except ValueError:
                pass


def params_to_overrides(params: JobTicketParams) -> dict[str, Any]:
    """Convert job ticket params to PreflightProfile threshold overrides."""
    overrides: dict[str, Any] = {}

    if params.conformance:
        overrides["conformance"] = params.conformance
    if params.min_dpi > 0:
        overrides["min_dpi"] = params.min_dpi
    if params.max_ink_coverage > 0:
        overrides["tac_limit"] = params.max_ink_coverage
    if params.bleed_mm > 0:
        overrides["min_bleed_mm"] = params.bleed_mm
    if params.output_condition:
        overrides["target_output_condition"] = params.output_condition

    return overrides
