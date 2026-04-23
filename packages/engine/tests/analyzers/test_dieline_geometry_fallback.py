"""WS-19 — geometry fallback for the dieline detector.

The 2026-04-23 Test3 DailyFiber 10-up fixture has no named
Separation or OCG matching the dieline vocabulary, yet it shows
the canonical "4 corner cut marks + bounding rectangle" pattern
on page 1. Before WS-19 the detector returned ``source='missing'``
and all downstream art-size / legend inspectors got nothing.

These tests lock the shape-heuristic contract: stroked corner
marks + a stroked bounding rectangle trigger a geometry hit at
confidence 0.9; otherwise the heuristic stays quiet and the
Sonnet fallback still has first refusal.
"""

from __future__ import annotations

from io import BytesIO

import pikepdf
import pytest

from lintpdf.analyzers.dieline import detect_dieline


def _build_pdf(content_stream: str, width: float = 612.0, height: float = 792.0) -> bytes:
    """Minimal single-page PDF whose page-1 content stream is the
    caller-supplied operators. The stream is rendered as-is so the
    detector's parser sees exactly those instructions.
    """
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(width, height))
    page = pdf.pages[0]
    page.Contents = pdf.make_stream(content_stream.encode("ascii"))
    buf = BytesIO()
    pdf.save(buf)
    return buf.getvalue()


def _corner_mark_ops(
    cx: float, cy: float, size: float = 10.0, inward_x: int = 1, inward_y: int = 1
) -> str:
    """Two short strokes forming an L/crosshair at ``(cx, cy)`` that
    extend inward by ``size`` pt. Each stroke is its own subpath
    terminated with ``S`` so the detector treats them as individual
    corner marks.
    """
    x1 = cx + size * inward_x
    y1 = cy + size * inward_y
    return (
        f"{cx} {cy} m {x1} {cy} l S\n"
        f"{cx} {cy} m {cx} {y1} l S\n"
    )


def _bounding_rect_ops(x0: float, y0: float, x1: float, y1: float) -> str:
    w = x1 - x0
    h = y1 - y0
    return f"{x0} {y0} {w} {h} re S\n"


class TestGeometryFallbackFires:
    @staticmethod
    def test_four_corner_marks_plus_rect_returns_geometry() -> None:
        """Canonical dieline pattern: 4 corner marks + trim-rect ≥ 60 %
        of MediaBox. Expect source='geometry' with confidence 0.9."""
        w, h = 612.0, 792.0
        # Corner marks just inside each MediaBox corner.
        marks = (
            _corner_mark_ops(10, 10, size=10, inward_x=1, inward_y=1)
            + _corner_mark_ops(w - 10, 10, size=10, inward_x=-1, inward_y=1)
            + _corner_mark_ops(10, h - 10, size=10, inward_x=1, inward_y=-1)
            + _corner_mark_ops(w - 10, h - 10, size=10, inward_x=-1, inward_y=-1)
        )
        # Trim rect ~77 % of MediaBox (~ real packaging ratio).
        rect = _bounding_rect_ops(30, 30, w - 30, h - 30)
        pdf_bytes = _build_pdf(marks + rect, width=w, height=h)

        result = detect_dieline(pdf_bytes, ai_features=frozenset())
        assert result.source == "geometry"
        assert result.confidence == pytest.approx(0.9, abs=0.01)
        assert result.spot_name is None

    @staticmethod
    def test_named_spot_still_wins_over_geometry() -> None:
        """Name-match must run first. Even with a textbook geometric
        dieline, a matching spot colour should return source='name'
        so the existing art-size pathway keeps working unchanged."""
        w, h = 612.0, 792.0
        marks = (
            _corner_mark_ops(10, 10, size=10, inward_x=1, inward_y=1)
            + _corner_mark_ops(w - 10, 10, size=10, inward_x=-1, inward_y=1)
            + _corner_mark_ops(10, h - 10, size=10, inward_x=1, inward_y=-1)
            + _corner_mark_ops(w - 10, h - 10, size=10, inward_x=-1, inward_y=-1)
        )
        rect = _bounding_rect_ops(30, 30, w - 30, h - 30)
        # Inject a Separation colourspace named "Dieline" on the page
        # resources so name-match fires before geometry.
        pdf = pikepdf.new()
        pdf.add_blank_page(page_size=(w, h))
        page = pdf.pages[0]
        page.Contents = pdf.make_stream((marks + rect).encode("ascii"))
        cs = pikepdf.Array(
            [
                pikepdf.Name("/Separation"),
                pikepdf.Name("/Dieline"),
                pikepdf.Name("/DeviceCMYK"),
                pikepdf.Dictionary(
                    FunctionType=2,
                    Domain=pikepdf.Array([0, 1]),
                    C0=pikepdf.Array([0, 0, 0, 0]),
                    C1=pikepdf.Array([0, 1, 0, 0]),
                    N=1,
                ),
            ]
        )
        page.Resources = pikepdf.Dictionary(
            ColorSpace=pikepdf.Dictionary(CS0=cs),
        )
        buf = BytesIO()
        pdf.save(buf)

        result = detect_dieline(buf.getvalue(), ai_features=frozenset())
        assert result.source == "name"
        assert result.spot_name == "Dieline"


class TestGeometryFallbackMisses:
    @staticmethod
    def test_only_two_corner_marks_no_match() -> None:
        """Incomplete corner set (2 of 4). Heuristic must NOT fire —
        geometry confidence would be wrong if it did."""
        w, h = 612.0, 792.0
        marks = (
            _corner_mark_ops(10, 10, size=10, inward_x=1, inward_y=1)
            + _corner_mark_ops(w - 10, 10, size=10, inward_x=-1, inward_y=1)
        )
        rect = _bounding_rect_ops(30, 30, w - 30, h - 30)
        pdf_bytes = _build_pdf(marks + rect, width=w, height=h)

        result = detect_dieline(pdf_bytes, ai_features=frozenset())
        assert result.source == "missing"

    @staticmethod
    def test_corner_marks_but_no_bounding_rect_no_match() -> None:
        """Corner marks present but no large stroked rectangle."""
        w, h = 612.0, 792.0
        marks = (
            _corner_mark_ops(10, 10, size=10, inward_x=1, inward_y=1)
            + _corner_mark_ops(w - 10, 10, size=10, inward_x=-1, inward_y=1)
            + _corner_mark_ops(10, h - 10, size=10, inward_x=1, inward_y=-1)
            + _corner_mark_ops(w - 10, h - 10, size=10, inward_x=-1, inward_y=-1)
        )
        # A small rectangle (< 60 % of MediaBox) shouldn't count.
        tiny_rect = _bounding_rect_ops(200, 300, 300, 400)
        pdf_bytes = _build_pdf(marks + tiny_rect, width=w, height=h)

        result = detect_dieline(pdf_bytes, ai_features=frozenset())
        assert result.source == "missing"

    @staticmethod
    def test_empty_page_no_match() -> None:
        """Blank page → nothing to match."""
        pdf_bytes = _build_pdf("", width=612.0, height=792.0)

        result = detect_dieline(pdf_bytes, ai_features=frozenset())
        assert result.source == "missing"
