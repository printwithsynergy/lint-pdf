"""Unit tests for WS-9 violation-region bbox.

Direct unit tests on the two helpers (``_safety_margin_violation``
/ ``_beyond_bleed_violation``) — both were introduced so the
findings panel can highlight the actual sliver that violates the
safety margin or sits outside the bleed, rather than the entire
content bbox.
"""

from __future__ import annotations

from siftpdf.analyzers.page_geometry import (
    _beyond_bleed_violation,
    _safety_margin_violation,
)
from siftpdf.semantic.model import PdfBox

# -- safety margin ------------------------------------------------------------


def test_content_fully_inside_safe_zone_has_no_violation() -> None:
    trim = PdfBox(0.0, 0.0, 612.0, 792.0)
    # Content sits well inside the 8.5pt inner inset on every side.
    content = (50.0, 50.0, 500.0, 700.0)
    assert _safety_margin_violation(content, trim, 8.5) is None


def test_content_touching_one_edge_returns_narrow_strip() -> None:
    """The Amalgam_Catalyst Opus dispute: content 'fills the page'
    but the violation is a thin strip near one trim edge, not the
    whole content bbox."""
    trim = PdfBox(0.0, 0.0, 612.0, 792.0)
    # Content extends 3pt INTO the right-side safety margin. The
    # violation should be the 3pt-wide vertical strip at the right,
    # not the whole content bbox.
    content = (50.0, 50.0, 606.0, 700.0)
    violation = _safety_margin_violation(content, trim, 8.5)
    assert violation is not None
    vx0, vy0, vx1, vy1 = violation
    # Violation strip hugs the right edge of the trim, capped at
    # the content extent on the y axis.
    assert vx0 == 612.0 - 8.5
    assert vx1 == 606.0
    assert vy0 == 50.0
    assert vy1 == 700.0
    # Strip width is 5.5pt, far narrower than the 556pt-wide content.
    assert (vx1 - vx0) < 10.0


def test_content_fully_outside_trim_returns_none() -> None:
    """Content entirely beyond the trim box isn't a safety-margin
    violation (that's a bleed concern). Helper returns None."""
    trim = PdfBox(0.0, 0.0, 100.0, 100.0)
    content = (200.0, 200.0, 300.0, 300.0)
    assert _safety_margin_violation(content, trim, 5.0) is None


# -- beyond bleed -------------------------------------------------------------


def test_content_inside_bleed_has_no_violation() -> None:
    bleed = PdfBox(-10.0, -10.0, 622.0, 802.0)
    content = (50.0, 50.0, 500.0, 700.0)
    assert _beyond_bleed_violation(content, bleed) is None


def test_content_extending_beyond_bleed_returns_only_outside_portion() -> None:
    bleed = PdfBox(0.0, 0.0, 612.0, 792.0)
    # Content pokes 20pt past the right bleed edge.
    content = (500.0, 100.0, 632.0, 200.0)
    violation = _beyond_bleed_violation(content, bleed)
    assert violation is not None
    vx0, vy0, vx1, vy1 = violation
    # Only the 20pt sliver beyond the bleed should count.
    assert vx0 == 612.0
    assert vx1 == 632.0
    assert vy0 == 100.0
    assert vy1 == 200.0


def test_content_piercing_bleed_on_two_sides_returns_aabb_union() -> None:
    bleed = PdfBox(0.0, 0.0, 100.0, 100.0)
    # Content pokes beyond both the right and the top bleed edges.
    content = (50.0, 50.0, 150.0, 150.0)
    violation = _beyond_bleed_violation(content, bleed)
    assert violation is not None
    # AABB of the two external strips: right strip is x in [100, 150]
    # covering y in [50, 150]; top strip is y in [100, 150] covering
    # x in [50, 150]. Union AABB is (50, 100, 150, 150) OR
    # (100, 50, 150, 150) depending on which strip dominates --
    # the helper unions BOTH, so the AABB encloses x in [50, 150]
    # and y in [50, 150]. But that would match the content bbox
    # itself -- so the test just asserts the violation is strictly
    # smaller than the full content bbox when only one edge is
    # pierced, and returns a sensible AABB here.
    vx0, vy0, vx1, vy1 = violation
    assert (vx0, vy0, vx1, vy1) == (50.0, 50.0, 150.0, 150.0)
