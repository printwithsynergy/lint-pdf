"""Pantone reference database manager — lookup and Delta-E validation.

Provides Pantone Lab/CMYK reference data for spot color fallback validation.
Ships enriched reference data (PANTONE_PUBLISHED Lab values + Color Bridge CMYK)
covering 23,000+ colors across 16 Pantone libraries. Customers can upload
official Pantone Color Bridge data to override.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REFERENCE_PATH = Path(__file__).parent / "pantone_reference.json"

# Cached reference data
_reference_cache: dict[str, dict[str, Any]] | None = None

# Normalize Pantone name variants
_SPACE_COLLAPSE = re.compile(r"\s+")


@dataclass(frozen=True)
class PantoneReference:
    """Reference data for a single Pantone color."""

    name: str
    lab: tuple[float, float, float]
    cmyk_bridge: tuple[float, float, float, float] | None
    library: str | None = None
    lab_source: str | None = None
    cmyk_source: str | None = None


@dataclass(frozen=True)
class DeltaEResult:
    """Result of a Pantone fallback Delta-E validation."""

    delta_e: float
    reference_lab: tuple[float, float, float]
    fallback_lab: tuple[float, float, float]
    pantone_name: str
    acceptable: bool


def _normalize_pantone_name(name: str) -> str:
    """Normalize a Pantone name for matching.

    Handles variations like:
    - "PANTONE 485 C" vs "PANTONE 485C"
    - "Pantone 485 C" (case)
    - Extra whitespace
    """
    s = name.strip().upper()
    s = _SPACE_COLLAPSE.sub(" ", s)
    return s


def _load_reference() -> dict[str, dict[str, Any]]:
    """Load the built-in Pantone reference database (lazy, cached)."""
    global _reference_cache
    if _reference_cache is not None:
        return _reference_cache

    if not _REFERENCE_PATH.exists():
        logger.debug("Pantone reference database not found: %s", _REFERENCE_PATH)
        _reference_cache = {}
        return _reference_cache

    try:
        data = json.loads(_REFERENCE_PATH.read_text(encoding="utf-8"))
        colors = data.get("colors", {})
        # Build normalized lookup index
        _reference_cache = {_normalize_pantone_name(k): v for k, v in colors.items()}
        logger.debug("Loaded %d Pantone reference colors", len(_reference_cache))
    except Exception:
        logger.exception("Failed to load Pantone reference database")
        _reference_cache = {}

    return _reference_cache


class PantoneManager:
    """Manages Pantone color reference data and performs Delta-E validation.

    Args:
        custom_overrides: Customer-uploaded Pantone data to merge on top
            of the built-in reference. Format: ``{"PANTONE 485 C": {"lab": [...]}}``.
    """

    def __init__(self, custom_overrides: dict[str, dict[str, Any]] | None = None) -> None:
        self._reference = _load_reference()
        self._overrides: dict[str, dict[str, Any]] = {}
        if custom_overrides:
            self._overrides = {_normalize_pantone_name(k): v for k, v in custom_overrides.items()}

    def lookup(self, name: str) -> PantoneReference | None:
        """Look up a Pantone color by name.

        Returns None if the color is not in the reference database.
        """
        key = _normalize_pantone_name(name)

        # Customer overrides take precedence
        data = self._overrides.get(key) or self._reference.get(key)
        if data is None:
            # Try without space before suffix: "PANTONE 485C" → "PANTONE 485 C"
            alt_key = self._try_alternate_key(key)
            if alt_key:
                data = self._overrides.get(alt_key) or self._reference.get(alt_key)
        if data is None:
            return None

        lab_raw = data.get("lab")
        if not lab_raw or len(lab_raw) != 3:
            return None

        lab = (float(lab_raw[0]), float(lab_raw[1]), float(lab_raw[2]))

        cmyk_raw = data.get("cmyk_bridge")
        cmyk = None
        if cmyk_raw and len(cmyk_raw) == 4:
            cmyk = (
                float(cmyk_raw[0]),
                float(cmyk_raw[1]),
                float(cmyk_raw[2]),
                float(cmyk_raw[3]),
            )

        return PantoneReference(
            name=name,
            lab=lab,
            cmyk_bridge=cmyk,
            library=data.get("library"),
            lab_source=data.get("lab_source"),
            cmyk_source=data.get("cmyk_source"),
        )

    def has_color(self, name: str) -> bool:
        """Check if a color exists in the reference database."""
        key = _normalize_pantone_name(name)
        if key in self._overrides or key in self._reference:
            return True
        alt_key = self._try_alternate_key(key)
        return alt_key is not None and (alt_key in self._overrides or alt_key in self._reference)

    @staticmethod
    def _try_alternate_key(key: str) -> str | None:
        """Try alternate normalized forms for Pantone name matching."""
        # "PANTONE 485C" → "PANTONE 485 C"
        m = re.match(r"^(PANTONE\s+.+?)([CUMV])$", key)
        if m:
            return f"{m.group(1)} {m.group(2)}"

        # "PANTONE 485 C" → "PANTONE 485C"
        m = re.match(r"^(PANTONE\s+.+?)\s+([CUMV])$", key)
        if m:
            return f"{m.group(1)}{m.group(2)}"

        return None

    def validate_cmyk_fallback(
        self,
        pantone_name: str,
        cmyk_values: tuple[float, float, float, float],
        icc_profile_bytes: bytes | None = None,
        warning_threshold: float = 5.0,
        advisory_threshold: float = 2.0,
    ) -> DeltaEResult | None:
        """Validate CMYK fallback values against the Pantone reference.

        Args:
            pantone_name: Pantone color name (e.g., "PANTONE 485 C").
            cmyk_values: CMYK alternate values (0-1 range).
            icc_profile_bytes: Optional ICC profile for accurate CMYK→Lab.
            warning_threshold: Delta-E threshold for WARNING severity.
            advisory_threshold: Delta-E threshold for ADVISORY severity.

        Returns:
            DeltaEResult with Delta-E and Lab values, or None if reference
            not found.
        """
        ref = self.lookup(pantone_name)
        if ref is None:
            return None

        # Convert CMYK fallback to Lab
        fallback_lab = self._cmyk_to_lab(cmyk_values, icc_profile_bytes)

        # Compute Delta-E (CIEDE2000)
        delta_e = self._delta_e_2000(ref.lab, fallback_lab)

        return DeltaEResult(
            delta_e=round(delta_e, 2),
            reference_lab=ref.lab,
            fallback_lab=fallback_lab,
            pantone_name=pantone_name,
            acceptable=delta_e <= warning_threshold,
        )

    @staticmethod
    def _cmyk_to_lab(
        cmyk: tuple[float, float, float, float],
        icc_profile_bytes: bytes | None,
    ) -> tuple[float, float, float]:
        """Convert CMYK to Lab using gamut_analyzer's conversion."""
        from lintpdf.analyzers.gamut_analyzer import cmyk_to_lab

        return cmyk_to_lab(
            cmyk[0],
            cmyk[1],
            cmyk[2],
            cmyk[3],
            icc_profile_bytes=icc_profile_bytes,
        )

    @staticmethod
    def _delta_e_2000(
        lab1: tuple[float, float, float],
        lab2: tuple[float, float, float],
    ) -> float:
        """Compute CIEDE2000 Delta-E.

        Uses colour-science if available, otherwise falls back to CIE76.
        """
        try:
            import colour as colour_science
            import numpy as np

            a1 = np.array(lab1)
            a2 = np.array(lab2)
            return float(colour_science.delta_E(a1, a2, method="CIE 2000"))
        except ImportError:
            pass

        # Fallback: CIE76 (simple Euclidean distance in Lab)
        dl = lab1[0] - lab2[0]
        da = lab1[1] - lab2[1]
        db = lab1[2] - lab2[2]
        return (dl**2 + da**2 + db**2) ** 0.5
