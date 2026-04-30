"""Tests for the multi-up handling in ``LPDF_DIE_CONTENT_OUTSIDE``.

The post-merge Opus 4.7 audit (`/tmp/audit-opus-postmerge-1777391641/`)
flagged DailyFiber's `LPDF_DIE_CONTENT_OUTSIDE` finding (11 680 regions
"outside the dieline") as a false positive — the file is a 10-up
step-and-repeat flat, not a single-die job. The engine had been merging
all 10 dieline regions into a single sheet-wide envelope, then flagging
every repeat's edge content as "outside" it.

Fix: detect multi-up via region size uniformity, then test each foreign
content bbox against the *nearest* region's tolerance instead of the
sheet-wide envelope.
"""

from __future__ import annotations

from lintpdf.analyzers.dieline_quality import (
    _is_multi_up,
    _min_overhang_against_regions,
)

# ── _is_multi_up heuristic ─────────────────────────────────────────────────


class TestIsMultiUp:
    @staticmethod
    def test_three_equal_regions_qualifies() -> None:
        regions = [
            {"x0": 0, "y0": 0, "x1": 100, "y1": 200},
            {"x0": 110, "y0": 0, "x1": 210, "y1": 200},
            {"x0": 220, "y0": 0, "x1": 320, "y1": 200},
        ]
        assert _is_multi_up(regions) is True

    @staticmethod
    def test_ten_uniform_repeats_qualifies() -> None:
        regions = [{"x0": i * 110, "y0": 0, "x1": i * 110 + 100, "y1": 200} for i in range(10)]
        assert _is_multi_up(regions) is True

    @staticmethod
    def test_single_region_never_multi_up() -> None:
        regions = [{"x0": 0, "y0": 0, "x1": 612, "y1": 792}]
        assert _is_multi_up(regions) is False

    @staticmethod
    def test_two_regions_below_threshold() -> None:
        # We require >= 3 regions to call it a step-and-repeat;
        # a 2-up duplex print is too ambiguous.
        regions = [
            {"x0": 0, "y0": 0, "x1": 100, "y1": 200},
            {"x0": 110, "y0": 0, "x1": 210, "y1": 200},
        ]
        assert _is_multi_up(regions) is False

    @staticmethod
    def test_unequal_sizes_not_multi_up() -> None:
        # A label + a header on the same page → two regions, but
        # different sizes. Don't classify as multi-up.
        regions = [
            {"x0": 0, "y0": 0, "x1": 100, "y1": 200},
            {"x0": 110, "y0": 0, "x1": 500, "y1": 50},
            {"x0": 110, "y0": 60, "x1": 600, "y1": 700},
        ]
        assert _is_multi_up(regions) is False

    @staticmethod
    def test_degenerate_box_skipped() -> None:
        regions = [
            {"x0": 0, "y0": 0, "x1": 100, "y1": 200},
            {"x0": 0, "y0": 0, "x1": 0, "y1": 0},  # zero area — skipped
            {"x0": 110, "y0": 0, "x1": 210, "y1": 200},
            {"x0": 220, "y0": 0, "x1": 320, "y1": 200},
        ]
        # 3 valid uniform regions remain after skipping the degenerate.
        assert _is_multi_up(regions) is True


# ── _min_overhang_against_regions ──────────────────────────────────────────


class TestMinOverhangAgainstRegions:
    @staticmethod
    def test_content_inside_one_region_returns_zero() -> None:
        regions = [
            {"x0": 0, "y0": 0, "x1": 100, "y1": 200},
            {"x0": 110, "y0": 0, "x1": 210, "y1": 200},
        ]
        # bbox sits inside region 2 — overhang vs nearest = 0.
        bbox = (120, 50, 200, 150)
        assert _min_overhang_against_regions(bbox, regions) == 0.0

    @staticmethod
    def test_content_partly_inside_one_repeat_uses_smaller_overhang() -> None:
        """For multi-up sheets the right comparison is "how far does
        this paint stick out of the *nearest* dieline region?", not
        "how far past the sheet-wide envelope?".

        Bbox (95, 50, 109, 150) overlaps region 1's right edge by 5pt
        and overlaps the gutter by 9pt; vs region 1 the overhang is 9pt
        (the right side sticks out from x=100 to x=109). Vs region 2,
        the bbox is entirely left of region 2 — overhang = (110-95)=15
        on the left side. Min overhang = 9 (vs region 1)."""
        regions = [
            {"x0": 0, "y0": 0, "x1": 100, "y1": 200},
            {"x0": 110, "y0": 0, "x1": 210, "y1": 200},
        ]
        bbox = (95, 50, 109, 150)
        oh = _min_overhang_against_regions(bbox, regions)
        assert oh == 9.0

    @staticmethod
    def test_content_inside_one_repeat_returns_zero() -> None:
        """When content sits entirely inside repeat #2, the answer is 0
        even though it would look "outside" the merged envelope of
        repeat #1's bbox treated alone."""
        regions = [
            {"x0": 0, "y0": 0, "x1": 100, "y1": 200},
            {"x0": 110, "y0": 0, "x1": 210, "y1": 200},
        ]
        bbox = (130, 60, 180, 140)
        assert _min_overhang_against_regions(bbox, regions) == 0.0

    @staticmethod
    def test_no_regions_returns_zero() -> None:
        assert _min_overhang_against_regions((0, 0, 50, 50), []) == 0.0
