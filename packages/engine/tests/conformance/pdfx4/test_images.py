"""Tests for PDF/X-4 image checks (PDFX4-079-087)."""

from __future__ import annotations

from typing import Any

from grounded.analyzers.finding import Severity
from grounded.conformance.pdfx4._images import validate_images
from grounded.semantic.events import ImagePlacedEvent
from grounded.semantic.graphics_state import TransformationMatrix
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc(output_intents: list[dict[str, Any]] | None = None) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        output_intents=output_intents or [],
    )


def _img_event(
    filters: tuple[str, ...] = (),
    has_opi: bool = False,
    has_alternate: bool = False,
    color_space: str = "DeviceCMYK",
    is_inline: bool = False,
    pixel_width: int = 100,
    pixel_height: int = 100,
    bits_per_component: int = 8,
    name: str = "Im1",
) -> ImagePlacedEvent:
    return ImagePlacedEvent(
        operator="Do",
        page_num=1,
        operator_index=0,
        image_name=name,
        ctm=TransformationMatrix.identity(),
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        bits_per_component=bits_per_component,
        color_space=color_space,
        filters=filters,
        has_opi=has_opi,
        has_alternate=has_alternate,
        is_inline=is_inline,
    )


class TestLzwCompression:
    @staticmethod
    def test_lzw_squall() -> None:
        f = validate_images(_doc(), [_img_event(filters=("LZWDecode",))])
        ids = [x for x in f if x.inspection_id == "PDFX4-079"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.WARNING

    @staticmethod
    def test_flate_ok() -> None:
        f = validate_images(_doc(), [_img_event(filters=("FlateDecode",))])
        assert not [x for x in f if x.inspection_id == "PDFX4-079"]


class TestOpiReference:
    @staticmethod
    def test_opi_aground() -> None:
        f = validate_images(_doc(), [_img_event(has_opi=True)])
        ids = [x for x in f if x.inspection_id == "PDFX4-082i"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR


class TestAlternateImages:
    @staticmethod
    def test_alternate_squall() -> None:
        f = validate_images(_doc(), [_img_event(has_alternate=True)])
        ids = [x for x in f if x.inspection_id == "PDFX4-083i"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.WARNING


class TestColorSpaceCompat:
    @staticmethod
    def test_rgb_image_no_rgb_intent() -> None:
        f = validate_images(_doc(), [_img_event(color_space="DeviceRGB")])
        ids = [x for x in f if x.inspection_id == "PDFX4-085"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY

    @staticmethod
    def test_rgb_image_with_rgb_intent_ok() -> None:
        intent = {"/S": "/GTS_PDFX", "/DestOutputProfile": {"/ColorSpace": "RGB"}}
        f = validate_images(_doc(output_intents=[intent]), [_img_event(color_space="DeviceRGB")])
        assert not [x for x in f if x.inspection_id == "PDFX4-085"]

    @staticmethod
    def test_cmyk_image_ok() -> None:
        f = validate_images(_doc(), [_img_event(color_space="DeviceCMYK")])
        assert not [x for x in f if x.inspection_id == "PDFX4-085"]


class TestInlineImageSize:
    @staticmethod
    def test_inline_over_4kb() -> None:
        # 100x100x8 = 10000 bytes > 4096
        f = validate_images(_doc(), [_img_event(is_inline=True, pixel_width=100, pixel_height=100)])
        ids = [x for x in f if x.inspection_id == "PDFX4-086"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY

    @staticmethod
    def test_inline_under_4kb_ok() -> None:
        # 8x8x8 = 64 bytes
        f = validate_images(_doc(), [_img_event(is_inline=True, pixel_width=8, pixel_height=8)])
        assert not [x for x in f if x.inspection_id == "PDFX4-086"]


class TestJpeg2000:
    @staticmethod
    def test_jpx_advisory() -> None:
        f = validate_images(_doc(), [_img_event(filters=("JPXDecode",))])
        ids = [x for x in f if x.inspection_id == "PDFX4-087"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY


class TestNoImages:
    @staticmethod
    def test_no_events_ok() -> None:
        f = validate_images(_doc(), [])
        assert len(f) == 0
