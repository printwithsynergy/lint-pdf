"""Tests for the shared OCR text-region pass.

Covers:

* ``DetectedTextRegion`` shape + default values.
* ``should_run_for_page`` heuristic on synthetic events.
* ``_scale_bbox`` pixel→points conversion (with y-axis flip).
* ``run`` end-to-end — delegates to codex in-process (mocked).
* ``run`` graceful handling when codex is unavailable (ImportError).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lintpdf.ai import text_region_pass
from lintpdf.semantic.events import (
    ImagePlacedEvent,
    PathPaintingEvent,
    TextRenderedEvent,
)
from lintpdf.semantic.graphics_state import TransformationMatrix
from lintpdf.semantic.model import (
    DetectedTextRegion,
    PdfBox,
    SemanticDocument,
    SemanticPage,
)


def _make_page(num: int = 1, w: float = 612, h: float = 792) -> SemanticPage:
    return SemanticPage(page_num=num, media_box=PdfBox(0, 0, w, h))


def _make_doc(pages: list[SemanticPage]) -> SemanticDocument:
    return SemanticDocument(version="1.7", page_count=len(pages), is_encrypted=False, pages=pages)


def _ctm(scale: float = 1.0) -> TransformationMatrix:
    return TransformationMatrix(scale, 0, 0, scale, 0, 0)


def _make_codex_region(text: str, x0: float, y0: float, x1: float, y1: float) -> MagicMock:
    """Build a mock CodexDetectedTextRegion with the given geometry."""
    region = MagicMock()
    region.text = text
    region.confidence = 0.92
    region.polygon = []
    region.source = "pymupdf"
    bbox = MagicMock()
    bbox.x0 = x0
    bbox.y0 = y0
    bbox.x1 = x1
    bbox.y1 = y1
    region.bbox = bbox
    return region


# ── DetectedTextRegion ────────────────────────────────────────────────────────


class TestDetectedTextRegion:
    @staticmethod
    def test_defaults() -> None:
        r = DetectedTextRegion(bbox=PdfBox(0, 0, 100, 50))
        assert r.text is None
        assert r.confidence == 0.0
        assert r.polygon is None
        assert r.source == "paddleocr"

    @staticmethod
    def test_with_polygon() -> None:
        poly = ((0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0))
        r = DetectedTextRegion(
            bbox=PdfBox(0, 0, 100, 50), text="hello", confidence=0.9, polygon=poly
        )
        assert r.text == "hello"
        assert r.confidence == 0.9
        assert r.polygon == poly


# ── trigger heuristic ────────────────────────────────────────────────────────


class TestShouldRunForPage:
    @staticmethod
    def test_image_heavy_page_qualifies() -> None:
        page = _make_page(1, w=612, h=792)
        # Single placed image at scale 500x500 → covers ~52% of 612*792.
        events = [
            ImagePlacedEvent(
                operator="Do",
                page_num=1,
                operator_index=0,
                image_name="Im1",
                ctm=_ctm(scale=500.0),
                pixel_width=500,
                pixel_height=500,
            )
        ]
        assert text_region_pass.should_run_for_page(page, events)

    @staticmethod
    def test_path_heavy_text_light_qualifies() -> None:
        page = _make_page(1)
        events = [
            PathPaintingEvent(operator="f", page_num=1, operator_index=i, fill=True, stroke=False)
            for i in range(60)
        ]
        assert text_region_pass.should_run_for_page(page, events)

    @staticmethod
    def test_clean_text_only_page_does_not_qualify() -> None:
        page = _make_page(1)
        events = [
            TextRenderedEvent(
                operator="Tj",
                page_num=1,
                operator_index=i,
                font_name="F1",
                font_size=12.0,
                ctm=_ctm(),
                text_matrix=_ctm(),
            )
            for i in range(20)
        ]
        assert not text_region_pass.should_run_for_page(page, events)


# ── bbox scaling ─────────────────────────────────────────────────────────────


class TestScaleBbox:
    @staticmethod
    def test_pixel_to_pdf_points_with_y_flip() -> None:
        # Image was rendered at 200 dpi for an A4 page (8.5×11 in → 612×792 pt).
        # Picking image dims = 612 × 792 pixels = 1:1 pt-to-px mapping for clarity.
        page = _make_page(1, w=612, h=792)
        bbox = {"x1": 100, "y1": 50, "x2": 300, "y2": 80}
        pdf_box, polygon = text_region_pass._scale_bbox(bbox, 612.0, 792.0, page)
        # x maps directly; y inverts.
        assert pdf_box.x0 == 100
        assert pdf_box.x1 == 300
        # y0 in PDF points = page_h - y2_px = 792 - 80 = 712
        assert pdf_box.y0 == 712
        assert pdf_box.y1 == 742
        assert polygon is None

    @staticmethod
    def test_polygon_preserved() -> None:
        page = _make_page(1, w=100, h=100)
        bbox = {
            "x1": 0,
            "y1": 0,
            "x2": 50,
            "y2": 30,
            "polygon": [[0, 0], [50, 0], [50, 30], [0, 30]],
        }
        _, polygon = text_region_pass._scale_bbox(bbox, 100.0, 100.0, page)
        assert polygon is not None
        # All four points present, y-flipped.
        assert len(polygon) == 4


# ── run() end-to-end ─────────────────────────────────────────────────────────


class TestRunPass:
    @staticmethod
    def test_populates_qualifying_pages_only() -> None:
        # Page 1 is path-heavy (qualifies), page 2 is text-only (does not).
        # Codex extraction should populate page 1 only.
        page1 = _make_page(1)
        page2 = _make_page(2)
        doc = _make_doc([page1, page2])
        events: list = [
            PathPaintingEvent(operator="f", page_num=1, operator_index=i, fill=True, stroke=False)
            for i in range(60)
        ] + [
            TextRenderedEvent(
                operator="Tj",
                page_num=2,
                operator_index=i,
                font_name="F1",
                font_size=12.0,
                ctm=_ctm(),
                text_matrix=_ctm(),
            )
            for i in range(20)
        ]

        codex_region = _make_codex_region("OUTLINED", 10.0, 752.0, 200.0, 782.0)

        with patch(
            "codex_pdf.extract.text_regions.extract_text_regions_for_page",
            return_value=[codex_region],
        ):
            text_region_pass.run(doc, events, b"%PDF-1.7\n%fake\n")

        assert page1.detected_text_regions is not None
        assert len(page1.detected_text_regions) == 1
        assert page1.detected_text_regions[0].text == "OUTLINED"
        assert page1.detected_text_regions[0].source == "pymupdf"
        # Untriggered pages stay None.
        assert page2.detected_text_regions is None

    @staticmethod
    def test_codex_unavailable_leaves_field_none() -> None:
        # When codex_pdf is not importable, detected_text_regions stays None.
        page = _make_page(1)
        doc = _make_doc([page])
        events: list = [
            PathPaintingEvent(operator="f", page_num=1, operator_index=i, fill=True, stroke=False)
            for i in range(60)
        ]

        with patch.dict("sys.modules", {"codex_pdf.extract.text_regions": None}):
            text_region_pass.run(doc, events, b"%PDF-1.7\n%fake\n")

        assert page.detected_text_regions is None

    @staticmethod
    def test_codex_extraction_error_leaves_field_none() -> None:
        # When codex raises during extraction, that page stays None.
        page = _make_page(1)
        doc = _make_doc([page])
        events: list = [
            PathPaintingEvent(operator="f", page_num=1, operator_index=i, fill=True, stroke=False)
            for i in range(60)
        ]

        with patch(
            "codex_pdf.extract.text_regions.extract_text_regions_for_page",
            side_effect=RuntimeError("fitz failed"),
        ):
            text_region_pass.run(doc, events, b"%PDF-1.7\n%fake\n")

        assert page.detected_text_regions is None

    @staticmethod
    def test_no_pages_qualify_skips_codex_entirely() -> None:
        # Clean text-only document — codex should never be called.
        page = _make_page(1)
        doc = _make_doc([page])
        events: list = [
            TextRenderedEvent(
                operator="Tj",
                page_num=1,
                operator_index=i,
                font_name="F1",
                font_size=12.0,
                ctm=_ctm(),
                text_matrix=_ctm(),
            )
            for i in range(20)
        ]

        codex_fn = MagicMock()
        with patch(
            "codex_pdf.extract.text_regions.extract_text_regions_for_page",
            codex_fn,
        ):
            text_region_pass.run(doc, events, b"%PDF-1.7\n")

        assert page.detected_text_regions is None
        codex_fn.assert_not_called()
