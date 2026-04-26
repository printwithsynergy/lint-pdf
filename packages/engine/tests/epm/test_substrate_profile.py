"""Substrate-aware ICC profile loader tests.

Exercises :func:`lintpdf.epm.icc.load_profile` and
:func:`lintpdf.epm.icc.is_in_gamut_for_profile` using synthetic
profiles built via ``PIL.ImageCms.createProfile`` so the tests stay
self-contained — no checked-in .icc binaries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PIL import ImageCms

from lintpdf.epm import icc

if TYPE_CHECKING:
    from pathlib import Path

# ---- load_profile error handling ----------------------------------------


def test_load_profile_raises_on_missing_file(tmp_path):
    missing = tmp_path / "nope.icc"
    with pytest.raises(icc.ProfileLoadError, match="failed to load"):
        icc.load_profile(str(missing))


def test_load_profile_raises_on_invalid_bytes(tmp_path):
    bad = tmp_path / "garbage.icc"
    bad.write_bytes(b"not an icc profile at all")
    with pytest.raises(icc.ProfileLoadError):
        icc.load_profile(str(bad))


def test_load_profile_caches_by_path(tmp_path):
    """Round-trip a known-good sRGB profile through disk; ensure the
    cache returns the same object on repeat calls."""
    icc_path = _write_srgb_to_disk(tmp_path)
    a = icc.load_profile(str(icc_path))
    b = icc.load_profile(str(icc_path))
    assert a is b


# ---- is_in_gamut_for_profile (sRGB) -------------------------------------


def test_in_gamut_for_srgb_profile_neutral_white(tmp_path):
    profile = icc.load_profile(str(_write_srgb_to_disk(tmp_path)))
    assert icc.is_in_gamut_for_profile((100.0, 0.0, 0.0), profile=profile) is True


def test_in_gamut_for_srgb_profile_neutral_gray(tmp_path):
    profile = icc.load_profile(str(_write_srgb_to_disk(tmp_path)))
    assert icc.is_in_gamut_for_profile((50.0, 0.0, 0.0), profile=profile) is True


def test_out_of_gamut_for_srgb_profile_extreme_chroma(tmp_path):
    """Lab (50, 120, 120) is well past sRGB's gamut boundary."""
    profile = icc.load_profile(str(_write_srgb_to_disk(tmp_path)))
    assert (
        icc.is_in_gamut_for_profile((50.0, 120.0, 120.0), profile=profile)
        is False
    )


def test_loose_tolerance_passes_extreme_colour(tmp_path):
    profile = icc.load_profile(str(_write_srgb_to_disk(tmp_path)))
    assert (
        icc.is_in_gamut_for_profile(
            (50.0, 100.0, 100.0), profile=profile, tolerance_de=200.0
        )
        is True
    )


# ---- is_in_gamut_for_profile rejects unsupported spaces -----------------


def test_unsupported_profile_color_space_raises(tmp_path):
    """A Lab-output profile (color space LAB) isn't a printer/output target."""
    lab_path = tmp_path / "lab.icc"
    lab_profile = ImageCms.createProfile("LAB")
    ImageCms.ImageCmsProfile(lab_profile).tobytes()  # warm the wrapper
    # Write Lab profile bytes to disk so load_profile can read it back
    with lab_path.open("wb") as f:
        f.write(ImageCms.ImageCmsProfile(lab_profile).tobytes())
    profile = icc.load_profile(str(lab_path))
    with pytest.raises(icc.ProfileLoadError, match="unsupported profile color space"):
        icc.is_in_gamut_for_profile((50.0, 0.0, 0.0), profile=profile)


# ---- helpers ------------------------------------------------------------


def _write_srgb_to_disk(tmp_path: Path) -> Path:
    """Serialize a synthetic sRGB profile so load_profile can read it back."""
    icc_path = tmp_path / "srgb_synth.icc"
    profile = ImageCms.createProfile("sRGB")
    with icc_path.open("wb") as f:
        f.write(ImageCms.ImageCmsProfile(profile).tobytes())
    return icc_path
