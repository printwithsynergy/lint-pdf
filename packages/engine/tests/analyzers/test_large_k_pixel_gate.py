"""Unit tests for WS-8 pixel-composited large-K gate.

Covers the new ``_dark_ink_fraction`` helper and its integration
with ``AdvancedColorAnalyzer`` so declared pure-K fills that
don't render as visible dark ink on the page stop producing
``LPDF_ADV_005`` advisories.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from unittest.mock import patch

from lintpdf.analyzers.advanced_color_analyzer import (
    AdvancedColorAnalyzer,
    _dark_ink_fraction,
)
from lintpdf.semantic.events import PathPaintingEvent
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _path_event(
    *, page_num: int, k: float, op_index: int = 0
) -> PathPaintingEvent:
    return PathPaintingEvent(
        operator="f",
        page_num=page_num,
        operator_index=op_index,
        fill=True,
        stroke=False,
        fill_color_space="DeviceCMYK",
        fill_color_values=(0.0, 0.0, 0.0, k),
        bbox=(0.0, 0.0, 50.0, 50.0),
    )


def _doc() -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


def _png_from_gray_level(level: int, w: int = 100, h: int = 100) -> bytes:
    """Build a minimal in-memory PNG of a solid grayscale swatch for
    the pixel gate to analyse."""
    from PIL import Image

    img = Image.new("L", (w, h), color=level)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# -- _dark_ink_fraction unit tests -------------------------------------------


def test_dark_fraction_returns_none_when_no_bytes() -> None:
    assert _dark_ink_fraction(None, 1) is None


def test_dark_fraction_returns_none_on_bad_page_num() -> None:
    assert _dark_ink_fraction(b"%PDF-1.7\n", 0) is None


def test_dark_fraction_fully_dark_render() -> None:
    """A fully black render (gray level 0) = 100% dark pixels."""
    black_png = _png_from_gray_level(0)
    with patch(
        "lintpdf.ai.rendering.render_page_to_image",
        return_value=black_png,
    ):
        frac = _dark_ink_fraction(b"%PDF-1.7\n", 1)
    assert frac is not None
    assert frac == 1.0


def test_dark_fraction_fully_white_render() -> None:
    """A fully white render (gray 255) = 0% dark pixels."""
    white_png = _png_from_gray_level(255)
    with patch(
        "lintpdf.ai.rendering.render_page_to_image",
        return_value=white_png,
    ):
        frac = _dark_ink_fraction(b"%PDF-1.7\n", 1)
    assert frac is not None
    assert frac == 0.0


def test_dark_fraction_render_exception_returns_none() -> None:
    """Pixel gate degrades gracefully when rendering fails."""
    with patch(
        "lintpdf.ai.rendering.render_page_to_image",
        side_effect=RuntimeError("gs not available"),
    ):
        assert _dark_ink_fraction(b"%PDF-1.7\n", 1) is None


# -- integration: AdvancedColorAnalyzer suppresses when no visible K ---------


def _white_render(*_a, **_k) -> bytes:
    return _png_from_gray_level(255)


def _black_render(*_a, **_k) -> bytes:
    return _png_from_gray_level(0)


def test_advanced_color_suppresses_when_rendered_page_has_no_dark() -> None:
    """The Pink-Slush case: declared pure-K events exist, but the
    composited render shows zero dark pixels (knocked-out or
    covered). The gate suppresses the aggregate advisory."""
    events = [_path_event(page_num=1, k=0.99, op_index=i) for i in range(50)]
    analyzer = AdvancedColorAnalyzer(
        brand_palette_present=True,
        pdf_bytes=b"%PDF-1.7\n",
    )
    with patch(
        "lintpdf.ai.rendering.render_page_to_image",
        side_effect=_white_render,
    ):
        findings = analyzer.analyze(_doc(), events)
    pure_k = [
        f
        for f in findings
        if f.inspection_id == "LPDF_ADV_005"
        and (f.details or {}).get("classification") == "pure_k"
    ]
    assert pure_k == []


def test_advanced_color_emits_when_rendered_page_has_dark_patch() -> None:
    """True-positive path: declared pure-K events + the rendered
    page actually has a large dark patch. Aggregate advisory
    fires, with ``rendered_dark_fraction`` recorded on details."""
    events = [_path_event(page_num=1, k=0.99, op_index=i) for i in range(50)]
    analyzer = AdvancedColorAnalyzer(
        brand_palette_present=True,
        pdf_bytes=b"%PDF-1.7\n",
    )
    with patch(
        "lintpdf.ai.rendering.render_page_to_image",
        side_effect=_black_render,
    ):
        findings = analyzer.analyze(_doc(), events)
    pure_k = [
        f
        for f in findings
        if f.inspection_id == "LPDF_ADV_005"
        and (f.details or {}).get("classification") == "pure_k"
    ]
    assert len(pure_k) == 1
    details = pure_k[0].details or {}
    assert details.get("object_count") == 50
    assert details.get("rendered_dark_fraction") == 1.0


def test_advanced_color_degrades_gracefully_when_render_fails() -> None:
    """When the renderer raises (no Ghostscript, timeout, etc.) the
    pixel gate returns None and the analyzer falls back to the
    vector-only behaviour -- emitting the aggregate as before."""
    events = [_path_event(page_num=1, k=0.99, op_index=i) for i in range(50)]
    analyzer = AdvancedColorAnalyzer(
        brand_palette_present=True,
        pdf_bytes=b"%PDF-1.7\n",
    )
    with patch(
        "lintpdf.ai.rendering.render_page_to_image",
        side_effect=RuntimeError("no backend"),
    ):
        findings = analyzer.analyze(_doc(), events)
    pure_k = [
        f
        for f in findings
        if f.inspection_id == "LPDF_ADV_005"
        and (f.details or {}).get("classification") == "pure_k"
    ]
    assert len(pure_k) == 1
    # No ``rendered_dark_fraction`` in details when the gate didn't run.
    assert "rendered_dark_fraction" not in (pure_k[0].details or {})


@dataclass
class _SkippedRenderer:
    calls: int = 0

    def __call__(self, *_a: object, **_k: object) -> bytes:
        self.calls += 1
        return _png_from_gray_level(255)


def test_no_pdf_bytes_means_pixel_gate_is_skipped() -> None:
    """Constructing the analyzer without ``pdf_bytes`` -- the usual
    path in unit tests -- skips the pixel gate entirely."""
    events = [_path_event(page_num=1, k=0.99, op_index=i) for i in range(50)]
    renderer = _SkippedRenderer()
    analyzer = AdvancedColorAnalyzer(brand_palette_present=True)
    with patch(
        "lintpdf.ai.rendering.render_page_to_image",
        side_effect=renderer,
    ):
        findings = analyzer.analyze(_doc(), events)
    # Emits under the vector-only path.
    pure_k = [
        f
        for f in findings
        if f.inspection_id == "LPDF_ADV_005"
        and (f.details or {}).get("classification") == "pure_k"
    ]
    assert len(pure_k) == 1
    # Renderer was never invoked.
    assert renderer.calls == 0
