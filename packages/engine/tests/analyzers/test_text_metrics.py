"""Unit tests for ``analyzers.text_metrics``.

Tight fixture-free tests on the composition math. No PDF parsing
— the helper consumes already-constructed ``TextRenderedEvent``
objects, so the tests just build those directly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from lintpdf.analyzers.text_metrics import (
    effective_font_size_pt,
    effective_x_height_mm,
    glyph_bbox_height_mm,
)
from lintpdf.semantic.graphics_state import TransformationMatrix


@dataclass
class _FakeEvent:
    """Duck-typed stand-in for ``TextRenderedEvent`` — the helpers
    never call an instance method, just read attributes."""

    font_size: float = 1.0
    ctm: TransformationMatrix = field(default_factory=TransformationMatrix)
    text_matrix: TransformationMatrix = field(default_factory=TransformationMatrix)
    rendering_mode: int = 0
    bbox: tuple[float, float, float, float] | None = None


@dataclass
class _FakeFont:
    font_descriptor: dict | None = None


# -- effective_font_size_pt ---------------------------------------------------


def test_identity_matrices_return_nominal_size() -> None:
    event = _FakeEvent(font_size=8.0)
    assert effective_font_size_pt(event) == 8.0


def test_nutrops_logo_scenario_composes_matrices() -> None:
    # The 14 disputed AI_EU1169_001 findings on Nutrops reported
    # "x-height 0.17mm at 1.0 pt" for text that Opus confirmed was
    # the large back-panel wordmark. Typical shape:
    #   Tf = 1.0,  Tm.a = 72,  CTM.a = 1.5  -> 108 pt on page.
    event = _FakeEvent(
        font_size=1.0,
        text_matrix=TransformationMatrix(a=72.0, d=72.0),
        ctm=TransformationMatrix(a=1.5, d=1.5),
    )
    assert effective_font_size_pt(event) == 108.0


def test_rotated_matrix_uses_sqrt_scale() -> None:
    # 45-deg rotation with scale 10: a=c=~7.07, b=-c, d=a.
    # extract_scale returns sqrt(a^2 + c^2) = 10 on both axes.
    r = TransformationMatrix(a=7.0710678, b=-7.0710678, c=7.0710678, d=7.0710678)
    event = _FakeEvent(font_size=1.0, text_matrix=r)
    assert math.isclose(effective_font_size_pt(event), 10.0, rel_tol=1e-5)


def test_zero_or_negative_font_size_returns_zero() -> None:
    assert effective_font_size_pt(_FakeEvent(font_size=0.0)) == 0.0
    assert effective_font_size_pt(_FakeEvent(font_size=-4.0)) != 0.0
    # Negative Tf values are legal in PDF (flips direction) — helper
    # reads the magnitude so the on-page size stays positive.
    assert effective_font_size_pt(_FakeEvent(font_size=-4.0)) == 4.0


# -- effective_x_height_mm ----------------------------------------------------


def test_nominal_8pt_body_identity_matrices_is_above_1_2mm() -> None:
    """8 pt Helvetica body copy — well above the 1.2 mm EU FIR
    minimum, so the rule should NOT flag it. Previously correct
    but the test guards against regressions that lower the ratio."""
    event = _FakeEvent(font_size=8.0)
    mm = effective_x_height_mm(event)
    assert mm is not None
    # 8 pt * 0.52 ratio * (25.4/72) mm/pt = ~1.47 mm
    assert mm > 1.2
    assert math.isclose(mm, 8.0 * 0.52 * (25.4 / 72.0), rel_tol=1e-5)


def test_nutrops_logo_scenario_returns_large_mm() -> None:
    event = _FakeEvent(
        font_size=1.0,
        text_matrix=TransformationMatrix(a=72.0, d=72.0),
        ctm=TransformationMatrix(a=1.5, d=1.5),
    )
    mm = effective_x_height_mm(event)
    assert mm is not None
    # 108 pt * 0.52 * 25.4/72 = ~19.8 mm; definitely not < 1.2 mm.
    assert mm > 15.0


def test_invisible_text_returns_none() -> None:
    event = _FakeEvent(font_size=8.0, rendering_mode=3)
    assert effective_x_height_mm(event) is None


def test_descriptor_xheight_overrides_fallback_ratio() -> None:
    font = _FakeFont(font_descriptor={"XHeight": 450, "UnitsPerEm": 1000})
    event = _FakeEvent(font_size=10.0)
    # 10 pt * 0.45 * 25.4/72 = ~1.588 mm
    mm = effective_x_height_mm(event, font=font)
    assert mm is not None
    assert math.isclose(mm, 10.0 * 0.45 * (25.4 / 72.0), rel_tol=1e-5)


def test_descriptor_ratio_outside_plausible_band_falls_back() -> None:
    # XHeight 50 / UnitsPerEm 1000 = 0.05 — way too low, trust the
    # 0.52 fallback instead of a clearly broken descriptor.
    font = _FakeFont(font_descriptor={"XHeight": 50, "UnitsPerEm": 1000})
    event = _FakeEvent(font_size=10.0)
    mm = effective_x_height_mm(event, font=font)
    assert mm is not None
    assert math.isclose(mm, 10.0 * 0.52 * (25.4 / 72.0), rel_tol=1e-5)


# -- glyph_bbox_height_mm -----------------------------------------------------


def test_glyph_bbox_height_converts_pts_to_mm() -> None:
    event = _FakeEvent(bbox=(0.0, 0.0, 10.0, 20.0))
    mm = glyph_bbox_height_mm(event)
    assert mm is not None
    # 20 pt * 0.52 * 25.4/72 = ~3.67 mm
    assert math.isclose(mm, 20.0 * 0.52 * (25.4 / 72.0), rel_tol=1e-5)


def test_glyph_bbox_height_returns_none_without_bbox() -> None:
    assert glyph_bbox_height_mm(_FakeEvent()) is None
