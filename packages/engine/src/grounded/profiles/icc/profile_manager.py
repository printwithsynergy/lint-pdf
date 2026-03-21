"""ICC profile manager — loads conditions and handles customer profiles."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from grounded.profiles.icc.gamut_boundary import GamutBoundary, load_gamut_boundary

logger = logging.getLogger(__name__)

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


def validate_icc_profile_bytes(profile_bytes: bytes) -> dict[str, Any]:
    """Validate ICC profile binary data and extract metadata.

    Returns dict with: valid (bool), error (str|None), metadata (dict).
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

    result["valid"] = True
    result["metadata"] = {
        "version": version,
        "color_space": cs_sig,
        "profile_class": class_sig,
        "pcs": pcs_sig,
        "size_bytes": profile_size,
    }

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
