"""ICC profile manager — loads conditions and handles customer profiles."""

from __future__ import annotations

import json
import logging
import struct
from pathlib import Path
from typing import Any

from grounded.profiles.icc.gamut_boundary import GamutBoundary, load_gamut_boundary

logger = logging.getLogger(__name__)

# D50 illuminant reference (ICC spec PCS illuminant)
_D50_X = 0.9642
_D50_Y = 1.0000
_D50_Z = 0.8249
_D50_TOLERANCE = 0.005

# Rendering intent names (ICC.1:2022 §7.2.15)
_RENDERING_INTENTS = {
    0: "Perceptual",
    1: "Media-Relative Colorimetric",
    2: "Saturation",
    3: "ICC-Absolute Colorimetric",
}

# Required tags per profile class (ICC.1:2022 §9)
_REQUIRED_TAGS_COMMON = frozenset({b"desc", b"wtpt", b"cprt"})
_REQUIRED_TAGS_INPUT = _REQUIRED_TAGS_COMMON | frozenset({b"A2B0"})
_REQUIRED_TAGS_DISPLAY = _REQUIRED_TAGS_COMMON | frozenset({
    b"rXYZ", b"gXYZ", b"bXYZ", b"rTRC", b"gTRC", b"bTRC",
})
_REQUIRED_TAGS_OUTPUT = _REQUIRED_TAGS_COMMON | frozenset({b"A2B0"})

_PROFILE_CLASS_REQUIRED_TAGS: dict[str, frozenset[bytes]] = {
    "mntr": _REQUIRED_TAGS_DISPLAY,
    "scnr": _REQUIRED_TAGS_INPUT,
    "prtr": _REQUIRED_TAGS_OUTPUT,
}

_CONDITIONS_PATH = Path(__file__).parent / "conditions.json"
_DEFAULT_PROFILES_DIR = Path(__file__).parent / "default_profiles"

# Cache loaded conditions and boundaries
_conditions_cache: dict[str, dict[str, Any]] | None = None
_boundary_cache: dict[str, GamutBoundary] = {}


def get_available_conditions() -> dict[str, dict[str, Any]]:
    """Return all available output conditions with metadata."""
    global _conditions_cache
    if _conditions_cache is not None:
        return _conditions_cache

    if not _CONDITIONS_PATH.exists():
        _conditions_cache = {}
        return _conditions_cache

    _conditions_cache = json.loads(_CONDITIONS_PATH.read_text(encoding="utf-8"))
    return _conditions_cache


def get_gamut_boundary(condition_slug: str) -> GamutBoundary | None:
    """Load a gamut boundary for a named condition.

    Returns None if the condition or mesh file is not available.
    """
    if condition_slug in _boundary_cache:
        return _boundary_cache[condition_slug]

    conditions = get_available_conditions()
    condition = conditions.get(condition_slug)
    if condition is None:
        return None

    mesh_file = condition.get("mesh_file")
    if not mesh_file:
        return None

    mesh_path = _DEFAULT_PROFILES_DIR / mesh_file
    if not mesh_path.exists():
        logger.debug("Gamut mesh not found: %s", mesh_path)
        return None

    try:
        boundary = load_gamut_boundary(mesh_path)
        _boundary_cache[condition_slug] = boundary
        return boundary
    except Exception:
        logger.exception("Failed to load gamut boundary: %s", mesh_path)
        return None


def _read_s15fixed16(data: bytes, offset: int) -> float:
    """Read an s15Fixed16Number from ICC profile data."""
    raw = struct.unpack_from(">i", data, offset)[0]
    return raw / 65536.0


def _read_xyz_type(data: bytes) -> tuple[float, float, float] | None:
    """Read an XYZType tag value (ICC.1:2022 §10.31)."""
    if len(data) < 20:
        return None
    # Bytes 0-3: type sig 'XYZ ', 4-7: reserved, 8-19: XYZ values
    x = _read_s15fixed16(data, 8)
    y = _read_s15fixed16(data, 12)
    z = _read_s15fixed16(data, 16)
    return (x, y, z)


def _read_text_description(data: bytes) -> str:
    """Read a textDescriptionType or multiLocalizedUnicodeType tag."""
    if len(data) < 8:
        return ""
    type_sig = data[0:4]
    if type_sig == b"desc":
        # textDescriptionType: offset 8 = ASCII count, then ASCII string
        if len(data) < 12:
            return ""
        count = struct.unpack_from(">I", data, 8)[0]
        if count == 0:
            return ""
        end = min(12 + count - 1, len(data))  # -1 for null terminator
        return data[12:end].decode("ascii", errors="replace")
    elif type_sig == b"mluc":
        # multiLocalizedUnicodeType
        if len(data) < 16:
            return ""
        record_count = struct.unpack_from(">I", data, 8)[0]
        if record_count == 0:
            return ""
        # First record: offset 16 = lang, 20 = country, 24 = length, 28 = offset
        if len(data) < 28:
            return ""
        str_length = struct.unpack_from(">I", data, 20)[0]
        str_offset = struct.unpack_from(">I", data, 24)[0]
        end = min(str_offset + str_length, len(data))
        return data[str_offset:end].decode("utf-16-be", errors="replace")
    else:
        # Try plain text
        return data[8:].decode("ascii", errors="replace").strip("\x00")


def _read_curve_type(data: bytes) -> dict[str, Any]:
    """Read a curveType tag and return summary info."""
    result: dict[str, Any] = {"type": "curveType"}
    if len(data) < 12:
        return result
    count = struct.unpack_from(">I", data, 8)[0]
    result["entry_count"] = count
    if count == 0:
        result["gamma"] = 1.0  # Identity
    elif count == 1 and len(data) >= 14:
        # Single entry: u8Fixed8Number gamma value
        gamma_raw = struct.unpack_from(">H", data, 12)[0]
        result["gamma"] = gamma_raw / 256.0
    else:
        result["lut_entries"] = count
    return result


def extract_icc_tags(profile_bytes: bytes) -> dict[str, Any]:
    """Parse the ICC tag directory and extract known tag data.

    Returns dict with:
        - ``tag_count``: number of tags in directory
        - ``tags``: dict mapping tag signature → parsed data
        - ``required_tags_present``: set of found required tag sigs
        - ``required_tags_missing``: set of missing required tag sigs
        - ``errors``: list of structural errors found
    """
    result: dict[str, Any] = {
        "tag_count": 0,
        "tags": {},
        "required_tags_present": set(),
        "required_tags_missing": set(),
        "errors": [],
    }

    if len(profile_bytes) < 132:
        result["errors"].append("Profile too small for tag directory")
        return result

    # Tag count at offset 128
    tag_count = struct.unpack_from(">I", profile_bytes, 128)[0]
    result["tag_count"] = tag_count

    if tag_count > 1000:
        result["errors"].append(f"Unreasonable tag count: {tag_count}")
        return result

    table_end = 132 + tag_count * 12
    if table_end > len(profile_bytes):
        result["errors"].append(
            f"Tag table extends beyond file: needs {table_end} bytes, "
            f"have {len(profile_bytes)}"
        )
        return result

    # Profile class for required tag determination
    class_sig = profile_bytes[12:16].decode("ascii", errors="replace").strip()

    tag_sigs_found: set[bytes] = set()
    tags: dict[str, Any] = {}

    for i in range(tag_count):
        entry_offset = 132 + i * 12
        sig = profile_bytes[entry_offset : entry_offset + 4]
        data_offset = struct.unpack_from(">I", profile_bytes, entry_offset + 4)[0]
        data_size = struct.unpack_from(">I", profile_bytes, entry_offset + 8)[0]

        tag_sigs_found.add(sig)
        sig_str = sig.decode("ascii", errors="replace").strip()

        # Validate bounds
        if data_offset + data_size > len(profile_bytes):
            result["errors"].append(
                f"Tag '{sig_str}' at offset {data_offset} + size {data_size} "
                f"exceeds file size {len(profile_bytes)}"
            )
            continue

        tag_data = profile_bytes[data_offset : data_offset + data_size]

        # Parse known tags
        if sig in (b"rXYZ", b"gXYZ", b"bXYZ", b"wtpt"):
            xyz = _read_xyz_type(tag_data)
            if xyz:
                tags[sig_str] = {"xyz": xyz}

        elif sig == b"desc":
            desc = _read_text_description(tag_data)
            tags[sig_str] = {"description": desc}

        elif sig == b"cprt":
            text = _read_text_description(tag_data)
            tags[sig_str] = {"copyright": text}

        elif sig in (b"rTRC", b"gTRC", b"bTRC"):
            curve = _read_curve_type(tag_data)
            tags[sig_str] = curve

        elif sig in (b"A2B0", b"B2A0", b"A2B1", b"B2A1"):
            tags[sig_str] = {"present": True, "size": data_size}

        elif sig == b"chad":
            if data_size >= 44:
                matrix = []
                for j in range(9):
                    matrix.append(_read_s15fixed16(tag_data, 8 + j * 4))
                tags[sig_str] = {"chromatic_adaptation_matrix": matrix}

        else:
            tags[sig_str] = {"present": True, "size": data_size}

    result["tags"] = tags

    # Check required tags
    required = _PROFILE_CLASS_REQUIRED_TAGS.get(class_sig, _REQUIRED_TAGS_COMMON)
    present = set()
    missing = set()
    for req_sig in required:
        if req_sig in tag_sigs_found:
            present.add(req_sig.decode("ascii", errors="replace").strip())
        else:
            missing.add(req_sig.decode("ascii", errors="replace").strip())
    result["required_tags_present"] = present
    result["required_tags_missing"] = missing

    return result


def validate_icc_profile_bytes(profile_bytes: bytes) -> dict[str, Any]:
    """Validate ICC profile binary data and extract metadata.

    Returns dict with: valid (bool), error (str|None), metadata (dict),
    tags (dict), rendering_intent (str), pcs_illuminant (dict).
    """
    result: dict[str, Any] = {"valid": False, "error": None, "metadata": {}}

    if len(profile_bytes) < 128:
        result["error"] = "Profile too small (< 128 bytes)"
        return result

    # Check magic number at offset 36: 'acsp'
    magic = profile_bytes[36:40]
    if magic != b"acsp":
        result["error"] = f"Invalid ICC magic number: {magic!r} (expected b'acsp')"
        return result

    # Extract header fields
    profile_size = int.from_bytes(profile_bytes[0:4], "big")
    if profile_size != len(profile_bytes):
        result["error"] = f"Size mismatch: header says {profile_size}, actual {len(profile_bytes)}"
        return result

    # Version (bytes 8-11)
    major = profile_bytes[8]
    minor = (profile_bytes[9] >> 4) & 0x0F
    version = f"{major}.{minor}"

    # Color space (bytes 16-19)
    cs_sig = profile_bytes[16:20].decode("ascii", errors="replace").strip()

    # Profile class (bytes 12-15)
    class_sig = profile_bytes[12:16].decode("ascii", errors="replace").strip()

    # PCS (bytes 20-23)
    pcs_sig = profile_bytes[20:24].decode("ascii", errors="replace").strip()

    # Rendering intent (byte 67)
    rendering_intent_code = profile_bytes[67] & 0x03
    rendering_intent = _RENDERING_INTENTS.get(
        rendering_intent_code, f"Unknown ({rendering_intent_code})",
    )

    # PCS illuminant (bytes 68-79: X, Y, Z as s15Fixed16Number)
    pcs_illuminant = None
    pcs_illuminant_valid = False
    if len(profile_bytes) >= 80:
        ill_x = _read_s15fixed16(profile_bytes, 68)
        ill_y = _read_s15fixed16(profile_bytes, 72)
        ill_z = _read_s15fixed16(profile_bytes, 76)
        pcs_illuminant = {"X": round(ill_x, 4), "Y": round(ill_y, 4), "Z": round(ill_z, 4)}
        pcs_illuminant_valid = (
            abs(ill_x - _D50_X) < _D50_TOLERANCE
            and abs(ill_y - _D50_Y) < _D50_TOLERANCE
            and abs(ill_z - _D50_Z) < _D50_TOLERANCE
        )

    result["valid"] = True
    result["metadata"] = {
        "version": version,
        "version_major": major,
        "version_minor": minor,
        "color_space": cs_sig,
        "profile_class": class_sig,
        "pcs": pcs_sig,
        "size_bytes": profile_size,
        "rendering_intent": rendering_intent,
        "rendering_intent_code": rendering_intent_code,
    }
    result["pcs_illuminant"] = pcs_illuminant
    result["pcs_illuminant_valid"] = pcs_illuminant_valid

    # Parse tag directory
    tag_info = extract_icc_tags(profile_bytes)
    result["tags"] = tag_info
    if tag_info["errors"]:
        result["valid"] = False
        result["error"] = "; ".join(tag_info["errors"])

    # Try Pillow ImageCms validation if available
    try:
        from PIL import ImageCms
        import io

        ImageCms.getOpenProfile(io.BytesIO(profile_bytes))
    except ImportError:
        pass
    except Exception as e:
        result["valid"] = False
        result["error"] = f"LittleCMS validation failed: {e}"

    return result
