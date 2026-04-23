"""Unit tests for WS-10 2D-barcode structural gate.

Direct tests on ``_looks_like_2d_barcode`` covering the four
structural signals (aspect, size, regularity, density). Each
test exercises the exact failure mode that produced a disputed
finding in the 2026-04-23 Opus audit.
"""

from __future__ import annotations

import random

from lintpdf.analyzers.barcode import _looks_like_2d_barcode


def _grid_fills(
    *,
    rows: int,
    cols: int,
    x0: float = 0.0,
    y0: float = 0.0,
    module: float = 2.0,
    jitter: float = 0.0,
) -> tuple[list[tuple[float, float, float, float]], float, float]:
    """Build a dense grid of fills, optionally with uniform jitter."""
    rng = random.Random(42)
    fills: list[tuple[float, float, float, float]] = []
    for r in range(rows):
        for c in range(cols):
            j_w = rng.uniform(-jitter, jitter) * module
            j_h = rng.uniform(-jitter, jitter) * module
            fx0 = x0 + c * module
            fy0 = y0 + r * module
            fx1 = fx0 + module + j_w
            fy1 = fy0 + module + j_h
            fills.append((fx0, fy0, fx1, fy1))
    region_w = cols * module
    region_h = rows * module
    return fills, region_w, region_h


def test_dense_regular_grid_passes() -> None:
    """Synthetic 10x10 Data-Matrix-like grid with no jitter --
    aspect 1.0, 40pt side, density 100%."""
    fills, w, h = _grid_fills(rows=10, cols=10)
    assert _looks_like_2d_barcode(fills, w, h) is True


def test_non_square_region_fails_aspect_check() -> None:
    """A 5x40 strip (aspect 0.125) is not a 2D symbol."""
    fills, w, h = _grid_fills(rows=5, cols=40)
    assert _looks_like_2d_barcode(fills, w, h) is False


def test_page_scale_region_fails_size_check() -> None:
    """A candidate spanning more than 200pt on a side is too
    large for any plausible 2D symbol. Mirrors the Nutrops
    ``143.4 x 427.6 mm`` dispute."""
    fills, w, h = _grid_fills(rows=200, cols=200, module=2.0)
    # 400pt x 400pt region -- fails max-side.
    assert w == 400.0
    assert h == 400.0
    assert _looks_like_2d_barcode(fills, w, h) is False


def test_irregular_modules_fail_regularity_check() -> None:
    """Splatter artwork has wildly varying fill sizes --
    coefficient of variation on both axes blows through 0.5."""
    rng = random.Random(0)
    fills = []
    # Bimodal: half tiny (0.5-1pt), half large (8-9pt) -- CV ~0.9.
    for _ in range(30):
        x = rng.uniform(0, 35)
        y = rng.uniform(0, 35)
        fills.append((x, y, x + rng.uniform(0.5, 1.0), y + rng.uniform(0.5, 1.0)))
    for _ in range(30):
        x = rng.uniform(0, 32)
        y = rng.uniform(0, 32)
        fills.append((x, y, x + rng.uniform(8.0, 9.0), y + rng.uniform(8.0, 9.0)))
    assert _looks_like_2d_barcode(fills, 40.0, 40.0) is False


def test_sparse_scatter_fails_density_check() -> None:
    """30 tiny 1x1pt marks scattered in a 40x40 region give a
    module-area fraction of about 1.8%, far below the 20%
    density floor. Mirrors the Amalgam_Catalyst splatter
    dispute."""
    rng = random.Random(1)
    fills = []
    for _ in range(30):
        x = rng.uniform(0, 39)
        y = rng.uniform(0, 39)
        fills.append((x, y, x + 1.0, y + 1.0))
    assert _looks_like_2d_barcode(fills, 40.0, 40.0) is False


def test_borderline_aspect_still_passes_within_band() -> None:
    """Data Matrix Rectangular Extension allows 2:1 aspect.
    1.5 aspect with regular modules + dense coverage -> passes."""
    fills, w, h = _grid_fills(rows=10, cols=15)
    # 30pt x 20pt, aspect 1.5 -- inside the 0.4..2.5 band.
    assert _looks_like_2d_barcode(fills, w, h) is True
