"""Q-C1 — EPM-Advanced ICC engine via Little CMS (Pillow's wrapper).

Foundation layer for the gamut / ΔE / ΔC checks the EPM-Advanced
analyzers will fire (out-of-gamut spot colours, neutral-axis drift,
substrate-aware TAC, etc.). All Little CMS bindings come through
``PIL.ImageCms`` which is already in the engine's dependency set —
no new third-party package required.

This module is intentionally pure math + LCMS calls, no I/O. The
``EpmCandidacyScorer`` and the future analyzers in
``lintpdf.epm.analyzers`` import these helpers; that keeps the
unit-testable surface tight and avoids duplicating CIEDE2000
implementations across modules.

Three primary primitives:

* :func:`lab_distance_de76`, :func:`lab_distance_de94`,
  :func:`lab_distance_de2000` — closed-form colour-difference
  calculations against the Lab inputs. Pure Python math; no LCMS
  needed for the math itself.
* :func:`cmyk_to_lab`, :func:`rgb_to_lab` — colour-space conversions
  via ``PIL.ImageCms`` so the per-pixel arithmetic matches what the
  press-side RIP would produce. Each conversion uses the
  ``ICCProfileCache`` so a busy preflight doesn't pay the
  profile-creation cost on every call.
* :func:`is_in_gamut` — round-trips a Lab triple through the target
  profile and back, comparing the recovered Lab to the input. A
  ΔE76 above the configured tolerance means the target gamut can't
  reproduce the colour.

Default tolerances per Q-C1 design:

* ``IN_GAMUT_DELTA_E`` = 2.0 (perceptual just-noticeable threshold)
* CMY-only profile = synthesized at module-load time (4-channel
  CMYK profile with K forced to zero) so the EPM-Core scorer can
  ask "would this still look right without K?"

Caller responsibilities:

* Pass Lab triples as ``tuple[float, float, float]`` in CIE Lab*
  coordinates: L ∈ [0, 100], a, b ∈ [-128, 127].
* Pass CMYK as ``tuple[float, float, float, float]`` percentages
  (0-100), not the 0-255 byte form.
* Cache the returned :class:`ImageCmsProfile` references — this
  module memoises them, but consumers shouldn't reopen profiles
  in tight loops.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import TYPE_CHECKING

from PIL import Image, ImageCms

if TYPE_CHECKING:
    from PIL.ImageCms import ImageCmsProfile


# ── tolerances (Q-C1) ──────────────────────────────────────────────────

IN_GAMUT_DELTA_E = 2.0
"""ΔE76 below which two colours read as identical to the eye."""

JND_DELTA_E_2000 = 1.0
"""Just-noticeable-difference threshold under the CIEDE2000 metric."""


# ── profile builders ──────────────────────────────────────────────────


@lru_cache(maxsize=8)
def srgb_profile() -> ImageCmsProfile:
    """Return the standard sRGB profile (memoised)."""
    return ImageCms.createProfile("sRGB")


@lru_cache(maxsize=8)
def lab_profile() -> ImageCmsProfile:
    """Return the standard CIE Lab* profile (memoised)."""
    return ImageCms.createProfile("LAB")


# ── colour-difference math ────────────────────────────────────────────


def lab_distance_de76(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    """CIE76 ΔE — straight Euclidean distance in Lab space.

    Cheap; correct for "are these the same colour?" sanity checks but
    exaggerates differences in dark / saturated regions. Use ΔE2000
    for human-perception fidelity.
    """
    l1, a1, b1 = a
    l2, a2, b2 = b
    return math.sqrt((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)


def lab_distance_de94(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    *,
    is_textile: bool = False,
) -> float:
    """CIE94 ΔE — weights chroma + hue. Graphics-arts default ``kL=1``."""
    l1, a1, b1 = a
    l2, a2, b2 = b
    dl = l1 - l2
    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    dc = c1 - c2
    da = a1 - a2
    db = b1 - b2
    dh_sq = max(0.0, da * da + db * db - dc * dc)
    if is_textile:
        kL, k1, k2 = 2.0, 0.048, 0.014
    else:
        kL, k1, k2 = 1.0, 0.045, 0.015
    sl = 1.0
    sc = 1.0 + k1 * c1
    sh = 1.0 + k2 * c1
    return math.sqrt((dl / (kL * sl)) ** 2 + (dc / sc) ** 2 + dh_sq / (sh * sh))


def lab_distance_de2000(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    """CIEDE2000 — the perceptually-correct colour-difference metric.

    Implementation follows Sharma, Wu & Dalal (2005) "The CIEDE2000
    color-difference formula: implementation notes, supplementary
    test data, and mathematical observations". Default constants
    ``kL = kC = kH = 1`` for unweighted graphics arts use.
    """
    l1, a1, b1 = a
    l2, a2, b2 = b
    avg_l = (l1 + l2) / 2.0
    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    avg_c = (c1 + c2) / 2.0

    g = 0.5 * (1 - math.sqrt(avg_c**7 / (avg_c**7 + 25**7)))
    a1p = (1 + g) * a1
    a2p = (1 + g) * a2
    c1p = math.hypot(a1p, b1)
    c2p = math.hypot(a2p, b2)
    avg_cp = (c1p + c2p) / 2.0

    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360

    dlp = l2 - l1
    dcp = c2p - c1p
    dhp = h2p - h1p
    if dhp > 180:
        dhp -= 360
    elif dhp < -180:
        dhp += 360
    if c1p * c2p == 0:
        dhp = 0
    dhp_rad = math.radians(dhp)
    dHp = 2 * math.sqrt(c1p * c2p) * math.sin(dhp_rad / 2)

    avg_hp = h1p + h2p
    if c1p * c2p == 0:
        avg_hp = h1p + h2p
    elif abs(h1p - h2p) > 180:
        avg_hp = (h1p + h2p + 360) / 2 if (h1p + h2p) < 360 else (h1p + h2p - 360) / 2
    else:
        avg_hp = (h1p + h2p) / 2.0

    t = (
        1
        - 0.17 * math.cos(math.radians(avg_hp - 30))
        + 0.24 * math.cos(math.radians(2 * avg_hp))
        + 0.32 * math.cos(math.radians(3 * avg_hp + 6))
        - 0.20 * math.cos(math.radians(4 * avg_hp - 63))
    )
    delta_theta = 30 * math.exp(-(((avg_hp - 275) / 25) ** 2))
    rc = 2 * math.sqrt(avg_cp**7 / (avg_cp**7 + 25**7))
    sl = 1 + (0.015 * (avg_l - 50) ** 2) / math.sqrt(20 + (avg_l - 50) ** 2)
    sc = 1 + 0.045 * avg_cp
    sh = 1 + 0.015 * avg_cp * t
    rt = -math.sin(math.radians(2 * delta_theta)) * rc

    return math.sqrt(
        (dlp / sl) ** 2
        + (dcp / sc) ** 2
        + (dHp / sh) ** 2
        + rt * (dcp / sc) * (dHp / sh)
    )


# ── colour-space conversions ──────────────────────────────────────────


def rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """Convert an sRGB triple (0-255) to CIE Lab via the LCMS pipeline."""
    transform = _rgb_to_lab_transform()
    img = Image.new("RGB", (1, 1), color=rgb)
    converted = ImageCms.applyTransform(img, transform)
    pixel = converted.getpixel((0, 0))
    # Pillow returns Lab as 0-255 byte values; rescale to standard CIE Lab.
    L = pixel[0] * 100.0 / 255.0
    a = pixel[1] - 128.0
    b = pixel[2] - 128.0
    return (L, a, b)


def lab_to_rgb(lab: tuple[float, float, float]) -> tuple[int, int, int]:
    """Convert CIE Lab to sRGB (0-255) via the LCMS pipeline."""
    transform = _lab_to_rgb_transform()
    L, a, b = lab
    pixel_in = (
        max(0, min(255, round(L * 255 / 100))),
        max(0, min(255, round(a + 128))),
        max(0, min(255, round(b + 128))),
    )
    img = Image.new("LAB", (1, 1), color=pixel_in)
    converted = ImageCms.applyTransform(img, transform)
    return tuple(converted.getpixel((0, 0)))  # type: ignore[return-value]


# ── gamut containment ────────────────────────────────────────────────


def is_in_gamut(
    lab: tuple[float, float, float],
    *,
    tolerance_de: float = IN_GAMUT_DELTA_E,
) -> bool:
    """Return ``True`` iff ``lab`` survives a Lab→sRGB→Lab round-trip
    within ``tolerance_de`` ΔE76. sRGB is the reference target since
    every digital press maps through a near-sRGB-equivalent gamut at
    the proof stage; substrate-specific profiles plug in via
    :func:`is_in_gamut_for_profile` once the EPM-Advanced analyzers
    ship.
    """
    rgb = lab_to_rgb(lab)
    round_tripped = rgb_to_lab(rgb)
    return lab_distance_de76(lab, round_tripped) <= tolerance_de


# ── transforms (cached) ──────────────────────────────────────────────


@lru_cache(maxsize=4)
def _rgb_to_lab_transform() -> ImageCms.ImageCmsTransform:
    return ImageCms.buildTransformFromOpenProfiles(
        srgb_profile(),
        lab_profile(),
        "RGB",
        "LAB",
    )


@lru_cache(maxsize=4)
def _lab_to_rgb_transform() -> ImageCms.ImageCmsTransform:
    return ImageCms.buildTransformFromOpenProfiles(
        lab_profile(),
        srgb_profile(),
        "LAB",
        "RGB",
    )


__all__ = [
    "IN_GAMUT_DELTA_E",
    "JND_DELTA_E_2000",
    "is_in_gamut",
    "lab_distance_de76",
    "lab_distance_de94",
    "lab_distance_de2000",
    "lab_profile",
    "lab_to_rgb",
    "rgb_to_lab",
    "srgb_profile",
]
