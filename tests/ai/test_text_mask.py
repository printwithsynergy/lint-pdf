"""Tests for ``lintpdf.ai.text_mask.build_text_mask``.

PR C Slot 3A: builds a numpy mask from ``page.detected_text_regions`` so
color analyzers can exclude text-edge pixels from sampling.
"""

from __future__ import annotations

import numpy as np

from lintpdf.ai.text_mask import build_text_mask
from lintpdf.semantic.model import (
    DetectedTextRegion,
    PdfBox,
    SemanticPage,
)


def _page(regions: list[DetectedTextRegion] | None) -> SemanticPage:
    p = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))
    p.detected_text_regions = regions
    return p


class TestBuildTextMask:
    @staticmethod
    def test_no_regions_returns_none() -> None:
        assert build_text_mask(_page(None), dpi=150) is None
        assert build_text_mask(_page([]), dpi=150) is None

    @staticmethod
    def test_single_region_marked_at_correct_pixel_box() -> None:
        # 1:1 dpi mapping (72 dpi) -> 612x792 px = pt direct.
        # Region from x=100..200 in PDF points; y=50..80 in PDF points
        # (origin bottom-left). After flip: top-left y = page_h - 80 =
        # 712, bottom-left y = page_h - 50 = 742.
        regions = [DetectedTextRegion(bbox=PdfBox(100, 50, 200, 80))]
        mask = build_text_mask(_page(regions), dpi=72, dilation_px=0)
        assert mask is not None
        assert mask.shape == (792, 612)
        # Region pixels (top-left coords): x=100..200, y=712..742
        assert mask[720, 150] == 255  # inside region
        assert mask[760, 150] == 0  # below the region (clean)
        assert mask[600, 150] == 0  # above the region

    @staticmethod
    def test_dilation_grows_region_outwards() -> None:
        regions = [DetectedTextRegion(bbox=PdfBox(100, 50, 200, 80))]
        mask = build_text_mask(_page(regions), dpi=72, dilation_px=5)
        assert mask is not None
        # 5-px dilation on a 100..200 x bbox should mark x=95 too.
        # y=712 (top edge of flipped region, page_h=792-80), x=95 is
        # within dilation. The y-row 712-5=707 should also be inside.
        assert mask[710, 95] == 255

    @staticmethod
    def test_zero_size_mediabox_returns_none() -> None:
        # PdfBox enforces x0 < x1 in __post_init__; force a degenerate
        # mediabox via object.__setattr__ to mimic a parser malformation.
        page = _page([DetectedTextRegion(bbox=PdfBox(0, 0, 100, 50))])
        # Forge a zero-size media_box.
        bad_mb = PdfBox(0, 0, 1, 1)
        object.__setattr__(bad_mb, "x1", 0)
        page.media_box = bad_mb
        assert build_text_mask(page, dpi=150) is None

    @staticmethod
    def test_region_outside_page_clipped() -> None:
        """A region whose pixel bbox lies entirely outside the page
        bounds shouldn't crash; mask returns None when nothing was
        marked."""
        regions = [DetectedTextRegion(bbox=PdfBox(700, 800, 711, 811))]
        # Page is 612x792 pt. The region is mostly above and to the
        # right; after flipping to pixel space at 72 dpi the bbox
        # falls outside the canvas.
        mask = build_text_mask(_page(regions), dpi=72)
        assert mask is None

    @staticmethod
    def test_dpi_scales_pixel_dimensions() -> None:
        regions = [DetectedTextRegion(bbox=PdfBox(0, 0, 100, 100))]
        mask = build_text_mask(_page(regions), dpi=150, dilation_px=0)
        assert mask is not None
        # Page is 612×792 pt → 150 dpi yields ~1275×1650 px.
        h, w = mask.shape
        assert abs(w - round(612 * 150 / 72)) <= 1
        assert abs(h - round(792 * 150 / 72)) <= 1

    @staticmethod
    def test_returns_uint8_dtype() -> None:
        regions = [DetectedTextRegion(bbox=PdfBox(0, 0, 100, 100))]
        mask = build_text_mask(_page(regions), dpi=72)
        assert mask is not None
        assert mask.dtype == np.uint8
