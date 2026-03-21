#!/usr/bin/env python3
"""Build precomputed gamut boundary mesh files for standard output conditions.

This script generates JSON gamut boundary files from ICC profiles.
It is a build tool — not shipped in production.

Usage:
    python build_gamut_meshes.py --profile FOGRA39.icc --condition fogra39_coated
    python build_gamut_meshes.py --srgb  # Generate sRGB boundary

Requires: Pillow (ImageCms), scipy, numpy
"""

from __future__ import annotations

import argparse
import io
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
_ROOT = Path(__file__).resolve().parents[5]  # up to packages/engine
sys.path.insert(0, str(_ROOT / "src"))

from grounded.profiles.icc.gamut_boundary import (
    build_gamut_boundary_from_lab_points,
    save_gamut_boundary,
)

_DEFAULT_PROFILES_DIR = Path(__file__).parent / "default_profiles"


def _sample_cmyk_grid(
    profile_bytes: bytes,
    steps: int = 11,
) -> list[tuple[float, float, float]]:
    """Sample CMYK space at a regular grid and convert to Lab.

    Args:
        profile_bytes: Raw ICC profile bytes.
        steps: Number of steps per channel (11 = 14,641 samples).

    Returns:
        List of (L*, a*, b*) tuples.
    """
    from PIL import Image, ImageCms

    cmyk_profile = ImageCms.getOpenProfile(io.BytesIO(profile_bytes))
    lab_profile = ImageCms.createProfile("Lab")
    transform = ImageCms.buildTransform(
        cmyk_profile,
        lab_profile,
        "CMYK",
        "Lab",
    )

    lab_points: list[tuple[float, float, float]] = []
    values = [i / (steps - 1) for i in range(steps)]

    for c in values:
        for m in values:
            for y in values:
                for k in values:
                    c_b = int(round(c * 255))
                    m_b = int(round(m * 255))
                    y_b = int(round(y * 255))
                    k_b = int(round(k * 255))

                    src = Image.new("CMYK", (1, 1), (c_b, m_b, y_b, k_b))
                    lab_img = ImageCms.applyTransform(src, transform)
                    px = lab_img.getpixel((0, 0))

                    l_star = px[0] * 100.0 / 255.0
                    a_star = px[1] - 128.0
                    b_star = px[2] - 128.0
                    lab_points.append((l_star, a_star, b_star))

    return lab_points


def _sample_srgb_grid(steps: int = 33) -> list[tuple[float, float, float]]:
    """Sample sRGB space at a regular grid and convert to Lab."""
    from grounded.analyzers.gamut_analyzer import srgb_to_lab

    lab_points: list[tuple[float, float, float]] = []
    values = [i / (steps - 1) for i in range(steps)]

    for r in values:
        for g in values:
            for b in values:
                lab_points.append(srgb_to_lab(r, g, b))

    return lab_points


def build_from_icc(
    profile_path: Path,
    condition_slug: str,
    condition_name: str,
) -> None:
    """Build gamut mesh from an ICC profile file."""
    profile_bytes = profile_path.read_bytes()
    logger.info(
        "Sampling CMYK grid from %s (condition: %s)...",
        profile_path.name,
        condition_slug,
    )

    lab_points = _sample_cmyk_grid(profile_bytes, steps=11)
    logger.info("Collected %d Lab samples", len(lab_points))

    boundary = build_gamut_boundary_from_lab_points(condition_name, lab_points)
    logger.info(
        "Convex hull: %d vertices, volume %.0f Lab^3",
        len(boundary.vertices),
        boundary.volume,
    )

    out_path = _DEFAULT_PROFILES_DIR / f"{condition_slug}.json"
    save_gamut_boundary(boundary, out_path)
    logger.info("Saved: %s", out_path)


def build_srgb() -> None:
    """Build gamut mesh for sRGB."""
    logger.info("Sampling sRGB grid...")
    lab_points = _sample_srgb_grid(steps=33)
    logger.info("Collected %d Lab samples", len(lab_points))

    boundary = build_gamut_boundary_from_lab_points(
        "sRGB IEC61966-2.1",
        lab_points,
    )
    logger.info(
        "Convex hull: %d vertices, volume %.0f Lab^3",
        len(boundary.vertices),
        boundary.volume,
    )

    out_path = _DEFAULT_PROFILES_DIR / "srgb.json"
    save_gamut_boundary(boundary, out_path)
    logger.info("Saved: %s", out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build gamut boundary meshes")
    parser.add_argument("--profile", type=Path, help="Path to ICC profile file")
    parser.add_argument("--condition", help="Condition slug (e.g., fogra39_coated)")
    parser.add_argument("--name", help="Human-readable condition name")
    parser.add_argument("--srgb", action="store_true", help="Build sRGB mesh")
    parser.add_argument("--steps", type=int, default=11, help="Grid steps per channel")

    args = parser.parse_args()

    if args.srgb:
        build_srgb()
    elif args.profile and args.condition:
        name = args.name or args.condition
        build_from_icc(args.profile, args.condition, name)
    else:
        parser.error("Specify --srgb or --profile + --condition")


if __name__ == "__main__":
    main()
