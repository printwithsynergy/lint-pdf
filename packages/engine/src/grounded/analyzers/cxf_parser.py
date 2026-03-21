"""CxF/X-4 spectral data parser using defusedxml for XXE-safe XML parsing.

Parses Color Exchange Format (CxF) XML embedded in PDF output intents
to extract spectral measurement data and spot color definitions.

Reference: ISO 17972 (CxF/X-4)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# CxF/X-4 namespace
_CXF_NS = "http://colorexchange.org/CxF/v3"


@dataclass
class CxfSpotColor:
    """A spot color definition extracted from CxF data."""

    name: str
    lab: tuple[float, float, float] | None = None
    spectral_data: list[float] | None = None
    wavelength_start: int = 380
    wavelength_end: int = 730
    wavelength_interval: int = 10


@dataclass
class CxfData:
    """Parsed CxF/X-4 data container."""

    spot_colors: list[CxfSpotColor] = field(default_factory=list)
    file_standard: str = ""
    valid: bool = False
    errors: list[str] = field(default_factory=list)


def parse_cxf_xml(xml_bytes: bytes) -> CxfData:
    """Parse CxF/X-4 XML data and extract spectral/color information.

    Args:
        xml_bytes: Raw XML bytes of the CxF data.

    Returns:
        CxfData with parsed spot colors and validation info.
    """
    result = CxfData()

    try:
        import defusedxml.ElementTree as ET
    except ImportError:
        result.errors.append("defusedxml not available for CxF parsing")
        return result

    try:
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        result.errors.append(f"XML parse error: {e}")
        return result

    # Detect CxF namespace and version
    ns = _detect_namespace(root)
    result.file_standard = _detect_standard(root, ns)

    # Parse ObjectCollection → Object entries
    objects = _find_elements(root, "ObjectCollection/Object", ns)
    if not objects:
        # Try without ObjectCollection wrapper
        objects = _find_elements(root, "Object", ns)

    for obj_elem in objects:
        spot = _parse_object(obj_elem, ns)
        if spot:
            result.spot_colors.append(spot)

    # Validate spectral data completeness
    for spot in result.spot_colors:
        if spot.spectral_data:
            expected_count = (
                spot.wavelength_end - spot.wavelength_start
            ) // spot.wavelength_interval + 1
            if len(spot.spectral_data) != expected_count:
                result.errors.append(
                    f"Spot '{spot.name}': expected {expected_count} spectral "
                    f"values ({spot.wavelength_start}-{spot.wavelength_end}nm "
                    f"at {spot.wavelength_interval}nm intervals), "
                    f"got {len(spot.spectral_data)}"
                )

            # Convert spectral to Lab if no Lab value present
            if spot.lab is None:
                lab = _spectral_to_lab(
                    spot.spectral_data,
                    spot.wavelength_start,
                    spot.wavelength_end,
                    spot.wavelength_interval,
                )
                if lab:
                    spot.lab = lab

    result.valid = len(result.errors) == 0
    return result


def _detect_namespace(root: Any) -> str:
    """Detect CxF XML namespace from the root element."""
    tag = root.tag
    if "{" in tag:
        return tag.split("}")[0] + "}"
    return ""


def _detect_standard(root: Any, ns: str) -> str:
    """Extract the CxF standard version from the root element."""
    version = root.get("Version", "")
    if version:
        return f"CxF {version}"

    # Check for FileInformation element
    file_info = root.find(f"{ns}FileInformation")
    if file_info is None:
        file_info = root.find("FileInformation")
    if file_info is not None:
        std = file_info.findtext(f"{ns}Standard", "")
        if not std:
            std = file_info.findtext("Standard", "")
        if std:
            return std

    return "CxF/X-4" if ns and _CXF_NS in ns else "CxF"


def _find_elements(root: Any, path: str, ns: str) -> list[Any]:
    """Find elements by tag name, handling namespace."""
    # We want the leaf element name from the path
    leaf_tag = path.split("/")[-1]
    # Try with namespace first, then without
    results = list(root.iter(f"{ns}{leaf_tag}"))
    if not results:
        results = list(root.iter(leaf_tag))
    return results


def _parse_object(obj_elem: Any, ns: str) -> CxfSpotColor | None:
    """Parse a single CxF Object element into a CxfSpotColor."""
    name = obj_elem.get("Name", "") or obj_elem.get("ObjectType", "")
    if not name:
        # Try to get name from child element
        name_elem = _find_child(obj_elem, "Name", ns)
        if name_elem is not None and name_elem.text:
            name = name_elem.text.strip()

    if not name:
        return None

    spot = CxfSpotColor(name=name)

    # Look for ColorValues container
    for cv_tag in ("ColorValues", "ColorSpecification"):
        color_values = _find_child(obj_elem, cv_tag, ns)
        if color_values is not None:
            break
    else:
        color_values = obj_elem  # Try parsing directly from object

    if color_values is not None:
        # Parse Lab values
        lab = _parse_lab(color_values, ns)
        if lab:
            spot.lab = lab

        # Parse spectral data
        spectral = _parse_spectral(color_values, ns)
        if spectral:
            spot.spectral_data = spectral["values"]
            spot.wavelength_start = spectral.get("start", 380)
            spot.wavelength_end = spectral.get("end", 730)
            spot.wavelength_interval = spectral.get("interval", 10)

    return spot


def _parse_lab(elem: Any, ns: str) -> tuple[float, float, float] | None:
    """Extract CIELab values from a CxF element."""
    # Search in elem and all descendants for Lab data
    for tag in ("ColorCIELab", "Lab", "CIELab"):
        lab_elem = _find_child(elem, tag, ns)
        if lab_elem is not None:
            try:
                l_val = float(_find_child_text(lab_elem, "L", ns, "0"))
                a_val = float(_find_child_text(lab_elem, "A", ns, "0"))
                b_val = float(_find_child_text(lab_elem, "B", ns, "0"))
                return (l_val, a_val, b_val)
            except (ValueError, TypeError):
                continue
    return None


def _find_child(elem: Any, tag: str, ns: str) -> Any | None:
    """Find a child element, trying with and without namespace."""
    result = elem.find(f"{ns}{tag}")
    if result is not None:
        return result
    result = elem.find(tag)
    return result


def _find_child_text(elem: Any, tag: str, ns: str, default: str = "") -> str:
    """Find child element text, trying with and without namespace."""
    result = elem.findtext(f"{ns}{tag}")
    if result is not None:
        return result
    result = elem.findtext(tag)
    if result is not None:
        return result
    return default


def _parse_spectral(elem: Any, ns: str) -> dict[str, Any] | None:
    """Extract spectral reflectance data from a CxF element."""
    for tag in ("ReflectanceSpectrum", "SpectralData", "Spectrum"):
        spec_elem = _find_child(elem, tag, ns)
        if spec_elem is not None:
            try:
                # Parse wavelength range attributes
                start = int(spec_elem.get("StartWL", "380"))
                end = int(spec_elem.get("EndWL", "730"))
                interval = int(spec_elem.get("Interval", "10"))

                # Parse reflectance values (space-separated floats)
                text = spec_elem.text
                if text:
                    values = [float(v) for v in text.strip().split()]
                    return {
                        "values": values,
                        "start": start,
                        "end": end,
                        "interval": interval,
                    }
            except (ValueError, TypeError):
                continue
    return None


def _spectral_to_lab(
    spectral_data: list[float],
    start_nm: int,
    end_nm: int,
    interval_nm: int,
) -> tuple[float, float, float] | None:
    """Convert spectral reflectance data to CIELab using colour-science.

    Returns None if colour-science is not available.
    """
    try:
        import numpy as np
        import colour as colour_science

        wavelengths = np.arange(start_nm, end_nm + 1, interval_nm, dtype=float)
        if len(wavelengths) != len(spectral_data):
            return None

        sd = colour_science.SpectralDistribution(
            dict(zip(wavelengths, spectral_data)),
        )
        xyz = colour_science.sd_to_XYZ(sd)
        lab = colour_science.XYZ_to_Lab(xyz / 100.0)
        return (float(lab[0]), float(lab[1]), float(lab[2]))
    except (ImportError, Exception):
        return None
