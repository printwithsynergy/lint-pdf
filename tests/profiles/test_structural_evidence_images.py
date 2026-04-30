"""Tests for ``_build_structural_evidence`` — the dict the Opus audit
harness reads to adjudicate findings vision can't verify.

PR-G (audit-uncertain v2) added an ``images`` array so Opus can
adjudicate ``LPDF_IMG_*`` findings (DPI, color space, compression,
masks) which previously dominated the "uncertain" bucket (57 of 101
in the post-merge audit). These tests assert the array shape and the
field surfaces.
"""

from __future__ import annotations

from siftpdf.profiles.orchestrator import _build_structural_evidence
from siftpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    PdfImage,
    SemanticDocument,
    SemanticPage,
)


def _doc_with_images(*images: PdfImage) -> SemanticDocument:
    page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792), images=list(images))
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


class TestImagesField:
    @staticmethod
    def test_no_images_yields_empty_array() -> None:
        page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))
        doc = SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])
        ev = _build_structural_evidence(doc)
        assert ev["images"] == []

    @staticmethod
    def test_single_image_surfaces_pixel_dims_and_filters() -> None:
        cs = PdfColorSpace(name="DeviceCMYK", cs_type="DeviceCMYK", components=4)
        img = PdfImage(
            name="Im1",
            width=2048,
            height=1536,
            bits_per_component=8,
            color_space=cs,
            filters=("/DCTDecode",),
            has_soft_mask=False,
            inline=False,
            page_num=1,
        )
        ev = _build_structural_evidence(_doc_with_images(img))
        assert len(ev["images"]) == 1
        e = ev["images"][0]
        assert e["pixel_width"] == 2048
        assert e["pixel_height"] == 1536
        assert e["bits_per_component"] == 8
        assert e["color_space_type"] == "DeviceCMYK"
        assert e["color_space_name"] == "DeviceCMYK"
        assert e["filters"] == ["/DCTDecode"]
        assert e["page_num"] == 1
        assert e["inline"] is False

    @staticmethod
    def test_inline_image_surfaces_inline_flag() -> None:
        img = PdfImage(
            name="inline_0",
            width=64,
            height=48,
            bits_per_component=8,
            color_space=None,
            filters=(),
            inline=True,
            page_num=1,
        )
        ev = _build_structural_evidence(_doc_with_images(img))
        e = ev["images"][0]
        assert e["inline"] is True
        assert e["color_space_type"] is None
        assert e["color_space_name"] is None

    @staticmethod
    def test_image_with_soft_mask_surfaces_flag() -> None:
        cs = PdfColorSpace(name="DeviceRGB", cs_type="DeviceRGB", components=3)
        img = PdfImage(
            name="Im_with_mask",
            width=512,
            height=512,
            bits_per_component=8,
            color_space=cs,
            filters=("/FlateDecode",),
            has_soft_mask=True,
            page_num=1,
        )
        ev = _build_structural_evidence(_doc_with_images(img))
        assert ev["images"][0]["has_soft_mask"] is True

    @staticmethod
    def test_multiple_pages_aggregate_all_images() -> None:
        img1 = PdfImage(
            name="Im1",
            width=300,
            height=200,
            bits_per_component=8,
            color_space=None,
            page_num=1,
        )
        img2 = PdfImage(
            name="Im2",
            width=400,
            height=300,
            bits_per_component=8,
            color_space=None,
            page_num=2,
        )
        page1 = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792), images=[img1])
        page2 = SemanticPage(page_num=2, media_box=PdfBox(0, 0, 612, 792), images=[img2])
        doc = SemanticDocument(
            version="1.7", page_count=2, is_encrypted=False, pages=[page1, page2]
        )
        ev = _build_structural_evidence(doc)
        assert len(ev["images"]) == 2
        pages = sorted(e["page_num"] for e in ev["images"])
        assert pages == [1, 2]
