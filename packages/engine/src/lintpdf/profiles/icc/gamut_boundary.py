"""Gamut boundary computation and testing using convex hulls in Lab space.

Gamut boundaries are precomputed from characterization data (CGATS format)
and stored as JSON for fast runtime checking.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GamutBoundary:
    """Precomputed gamut boundary as a convex hull in CIELab space."""

    condition_name: str
    vertices: list[list[float]]  # Nx3 Lab points on hull surface
    equations: list[list[float]]  # Mx4 half-space equations [a, b, c, d]
    volume: float  # Hull volume in Lab^3 units

    def is_in_gamut(self, lab: tuple[float, float, float]) -> bool:
        """Test if a Lab point is inside the gamut boundary.

        Uses half-space intersection: point is in gamut if
        equations @ [L, a, b, 1] <= tolerance for all half-spaces.
        """
        tolerance = 1e-6  # Small tolerance for numerical stability
        for eq in self.equations:
            val = eq[0] * lab[0] + eq[1] * lab[1] + eq[2] * lab[2] + eq[3]
            if val > tolerance:
                return False
        return True

    def distance_to_boundary(self, lab: tuple[float, float, float]) -> float:
        """Compute approximate distance from a Lab point to the gamut boundary.

        Returns 0 if in gamut, positive distance if out of gamut.
        Uses maximum half-space violation as approximate distance.
        """
        max_violation = 0.0
        for eq in self.equations:
            val = eq[0] * lab[0] + eq[1] * lab[1] + eq[2] * lab[2] + eq[3]
            if val > max_violation:
                max_violation = val
        return max_violation

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "condition_name": self.condition_name,
            "vertices": self.vertices,
            "equations": self.equations,
            "volume": self.volume,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GamutBoundary:
        """Deserialize from dictionary."""
        return cls(
            condition_name=data["condition_name"],
            vertices=data["vertices"],
            equations=data["equations"],
            volume=data["volume"],
        )


def build_gamut_boundary_from_lab_points(
    condition_name: str, lab_points: list[tuple[float, float, float]]
) -> GamutBoundary:
    """Build a gamut boundary convex hull from Lab measurement points.

    Args:
        condition_name: Human-readable condition name.
        lab_points: List of (L, a, b) measurement points.

    Returns:
        GamutBoundary with computed hull.
    """
    try:
        import numpy as np
        from scipy.spatial import ConvexHull
    except ImportError:
        raise ImportError("scipy and numpy required for gamut boundary computation")

    points = np.array(lab_points)
    hull = ConvexHull(points)

    return GamutBoundary(
        condition_name=condition_name,
        vertices=points[hull.vertices].tolist(),
        equations=hull.equations.tolist(),
        volume=float(hull.volume),
    )


def load_gamut_boundary(path: Path) -> GamutBoundary:
    """Load a precomputed gamut boundary from JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return GamutBoundary.from_dict(data)


def save_gamut_boundary(boundary: GamutBoundary, path: Path) -> None:
    """Save a gamut boundary to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(boundary.to_dict(), indent=2),
        encoding="utf-8",
    )
