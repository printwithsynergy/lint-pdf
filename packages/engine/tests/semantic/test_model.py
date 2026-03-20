"""Tests for SemanticModel dataclasses — PdfBox, PdfFont, PdfColorSpace, PdfImage, SemanticPage."""

from __future__ import annotations

import pytest

from grounded.exceptions import InvalidBoxError
from grounded.semantic.model import (
    STANDARD_14_FONTS,
    PdfBox,
    PdfColorSpace,
    PdfFont,
    PdfImage,
    SemanticDocument,
    SemanticPage,
)

# --- PdfBox Tests ---


class TestPdfBox:
    """Test PdfBox validation and geometry."""

    @staticmethod
    def test_valid_box() -> None:
        box = PdfBox(0, 0, 612, 792)
        assert box.x0 == 0.0
        assert box.y1 == 792.0

    @staticmethod
    def test_invalid_x_raises() -> None:
        with pytest.raises(InvalidBoxError, match=r"x0.*x1"):
            PdfBox(612, 0, 0, 792)

    @staticmethod
    def test_invalid_y_raises() -> None:
        with pytest.raises(InvalidBoxError, match=r"y0.*y1"):
            PdfBox(0, 792, 612, 0)

    @staticmethod
    def test_equal_x_raises() -> None:
        with pytest.raises(InvalidBoxError):
            PdfBox(100, 0, 100, 792)

    @staticmethod
    def test_equal_y_raises() -> None:
        with pytest.raises(InvalidBoxError):
            PdfBox(0, 100, 612, 100)

    @staticmethod
    def test_width_and_height() -> None:
        box = PdfBox(10, 20, 610, 820)
        assert box.width == 600.0
        assert box.height == 800.0

    @staticmethod
    def test_area() -> None:
        box = PdfBox(0, 0, 100, 200)
        assert box.area() == 20_000.0

    @staticmethod
    def test_contains_point_inside() -> None:
        box = PdfBox(0, 0, 612, 792)
        assert box.contains_point(306, 396) is True

    @staticmethod
    def test_contains_point_on_boundary() -> None:
        box = PdfBox(0, 0, 612, 792)
        assert box.contains_point(0, 0) is True
        assert box.contains_point(612, 792) is True

    @staticmethod
    def test_contains_point_outside() -> None:
        box = PdfBox(0, 0, 612, 792)
        assert box.contains_point(-1, 0) is False
        assert box.contains_point(613, 0) is False

    @staticmethod
    def test_contains_box_true() -> None:
        outer = PdfBox(0, 0, 612, 792)
        inner = PdfBox(10, 10, 600, 780)
        assert outer.contains_box(inner) is True

    @staticmethod
    def test_contains_box_false() -> None:
        outer = PdfBox(10, 10, 600, 780)
        inner = PdfBox(0, 0, 612, 792)
        assert outer.contains_box(inner) is False

    @staticmethod
    def test_contains_box_same() -> None:
        box = PdfBox(0, 0, 612, 792)
        assert box.contains_box(box) is True

    @staticmethod
    def test_as_tuple() -> None:
        box = PdfBox(10, 20, 30, 40)
        assert box.as_tuple() == (10, 20, 30, 40)

    @staticmethod
    def test_from_tuple() -> None:
        box = PdfBox.from_tuple((10.0, 20.0, 30.0, 40.0))
        assert box.x0 == 10.0
        assert box.y1 == 40.0

    @staticmethod
    def test_frozen() -> None:
        box = PdfBox(0, 0, 100, 100)
        with pytest.raises(AttributeError):
            box.x0 = 50.0  # type: ignore[misc]


# --- PdfFont Tests ---


class TestPdfFont:
    """Test PdfFont creation and Standard 14 detection."""

    @staticmethod
    def test_create_font() -> None:
        font = PdfFont(
            name="F1",
            base_font="Helvetica",
            font_type="Type1",
            embedded=False,
            subset=False,
        )
        assert font.name == "F1"
        assert font.base_font == "Helvetica"

    @staticmethod
    def test_is_standard_14_true() -> None:
        for font_name in STANDARD_14_FONTS:
            font = PdfFont(
                name="F1",
                base_font=font_name,
                font_type="Type1",
                embedded=False,
                subset=False,
            )
            assert font.is_standard_14() is True, f"{font_name} should be Standard 14"

    @staticmethod
    def test_is_standard_14_false() -> None:
        font = PdfFont(
            name="F1",
            base_font="CustomFont",
            font_type="TrueType",
            embedded=True,
            subset=False,
        )
        assert font.is_standard_14() is False

    @staticmethod
    def test_is_standard_14_with_subset_prefix() -> None:
        font = PdfFont(
            name="F1",
            base_font="ABCDEF+Helvetica",
            font_type="Type1",
            embedded=True,
            subset=True,
        )
        assert font.is_standard_14() is True

    @staticmethod
    def test_is_type3() -> None:
        font = PdfFont(
            name="F1",
            base_font="UserFont",
            font_type="Type3",
            embedded=True,
            subset=False,
        )
        assert font.is_type3() is True

    @staticmethod
    def test_is_not_type3() -> None:
        font = PdfFont(
            name="F1",
            base_font="Helvetica",
            font_type="Type1",
            embedded=False,
            subset=False,
        )
        assert font.is_type3() is False

    @staticmethod
    def test_is_cid_font() -> None:
        for font_type in ("CIDFontType0", "CIDFontType2"):
            font = PdfFont(
                name="F1",
                base_font="STSong-Light",
                font_type=font_type,
                embedded=True,
                subset=False,
            )
            assert font.is_cid_font() is True

    @staticmethod
    def test_is_not_cid_font() -> None:
        font = PdfFont(
            name="F1",
            base_font="Helvetica",
            font_type="Type1",
            embedded=False,
            subset=False,
        )
        assert font.is_cid_font() is False

    @staticmethod
    def test_frozen() -> None:
        font = PdfFont(
            name="F1",
            base_font="Helvetica",
            font_type="Type1",
            embedded=False,
            subset=False,
        )
        with pytest.raises(AttributeError):
            font.name = "F2"  # type: ignore[misc]


# --- PdfColorSpace Tests ---


class TestPdfColorSpace:
    """Test PdfColorSpace creation and type checks."""

    @staticmethod
    def test_device_rgb() -> None:
        cs = PdfColorSpace(name=None, cs_type="DeviceRGB", components=3)
        assert cs.is_device_space() is True
        assert cs.is_cie_based() is False
        assert cs.is_cmyk() is False

    @staticmethod
    def test_device_cmyk() -> None:
        cs = PdfColorSpace(name=None, cs_type="DeviceCMYK", components=4)
        assert cs.is_device_space() is True
        assert cs.is_cmyk() is True

    @staticmethod
    def test_icc_based_cmyk() -> None:
        cs = PdfColorSpace(
            name="CS1",
            cs_type="ICCBased",
            components=4,
            icc_profile_ref="5 0 R",
        )
        assert cs.is_cie_based() is True
        assert cs.is_cmyk() is True

    @staticmethod
    def test_icc_based_rgb() -> None:
        cs = PdfColorSpace(
            name="CS2",
            cs_type="ICCBased",
            components=3,
            icc_profile_ref="6 0 R",
        )
        assert cs.is_cie_based() is True
        assert cs.is_cmyk() is False

    @staticmethod
    def test_lab() -> None:
        cs = PdfColorSpace(name=None, cs_type="Lab", components=3)
        assert cs.is_cie_based() is True
        assert cs.is_device_space() is False

    @staticmethod
    def test_separation_colorant_names() -> None:
        cs = PdfColorSpace(
            name="CS1",
            cs_type="Separation",
            components=1,
            colorant_names=("PANTONE 485 C",),
        )
        assert cs.colorant_names == ("PANTONE 485 C",)

    @staticmethod
    def test_devicen_colorant_names() -> None:
        cs = PdfColorSpace(
            name="CS2",
            cs_type="DeviceN",
            components=3,
            colorant_names=("Cyan", "Magenta", "PANTONE 485 C"),
        )
        assert cs.colorant_names == ("Cyan", "Magenta", "PANTONE 485 C")
        assert len(cs.colorant_names) == 3

    @staticmethod
    def test_default_colorant_names_empty() -> None:
        cs = PdfColorSpace(name=None, cs_type="DeviceRGB", components=3)
        assert cs.colorant_names == ()

    @staticmethod
    def test_frozen() -> None:
        cs = PdfColorSpace(name=None, cs_type="DeviceRGB", components=3)
        with pytest.raises(AttributeError):
            cs.cs_type = "DeviceCMYK"  # type: ignore[misc]


# --- PdfImage Tests ---


class TestPdfImage:
    """Test PdfImage creation."""

    @staticmethod
    def test_create_image() -> None:
        cs = PdfColorSpace(name=None, cs_type="DeviceRGB", components=3)
        img = PdfImage(
            name="Im1",
            width=1000,
            height=800,
            bits_per_component=8,
            color_space=cs,
        )
        assert img.width == 1000
        assert img.height == 800
        assert img.inline is False

    @staticmethod
    def test_inline_image() -> None:
        img = PdfImage(
            name="inline_1",
            width=50,
            height=50,
            bits_per_component=8,
            color_space=None,
            inline=True,
            page_num=1,
        )
        assert img.inline is True

    @staticmethod
    def test_frozen() -> None:
        img = PdfImage(
            name="Im1",
            width=100,
            height=100,
            bits_per_component=8,
            color_space=None,
        )
        with pytest.raises(AttributeError):
            img.width = 200  # type: ignore[misc]


# --- SemanticPage Tests ---


class TestSemanticPage:
    """Test SemanticPage creation and computed properties."""

    @staticmethod
    def test_effective_dimensions_no_rotation() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
        )
        assert page.effective_width == 612.0
        assert page.effective_height == 792.0

    @staticmethod
    def test_effective_dimensions_90_rotation() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            rotate=90,
        )
        assert page.effective_width == 792.0
        assert page.effective_height == 612.0

    @staticmethod
    def test_effective_dimensions_180_rotation() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            rotate=180,
        )
        assert page.effective_width == 612.0
        assert page.effective_height == 792.0

    @staticmethod
    def test_effective_dimensions_270_rotation() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            rotate=270,
        )
        assert page.effective_width == 792.0
        assert page.effective_height == 612.0

    @staticmethod
    def test_effective_dimensions_uses_crop_box() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            crop_box=PdfBox(10, 10, 602, 782),
        )
        assert page.effective_width == 592.0
        assert page.effective_height == 772.0

    @staticmethod
    def test_effective_width_mm() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
        )
        # 612 points * 0.352778 = ~215.9 mm (US Letter width)
        assert abs(page.effective_width_mm - 215.9) < 0.1

    @staticmethod
    def test_effective_height_mm() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
        )
        # 792 points * 0.352778 = ~279.4 mm (US Letter height)
        assert abs(page.effective_height_mm - 279.4) < 0.1

    @staticmethod
    def test_user_unit_scaling() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            user_unit=2.0,
        )
        # With user_unit=2.0, dimensions in mm should double
        base_page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
        )
        assert abs(page.effective_width_mm - base_page.effective_width_mm * 2.0) < 0.1


# --- SemanticDocument Tests ---


class TestSemanticDocument:
    """Test SemanticDocument creation."""

    @staticmethod
    def test_create_minimal() -> None:
        doc = SemanticDocument(
            version="1.7",
            page_count=0,
            is_encrypted=False,
        )
        assert doc.version == "1.7"
        assert doc.pages == []

    @staticmethod
    def test_create_with_pages() -> None:
        pages = [
            SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792)),
            SemanticPage(page_num=2, media_box=PdfBox(0, 0, 612, 792)),
        ]
        doc = SemanticDocument(
            version="2.0",
            page_count=2,
            is_encrypted=False,
            pages=pages,
        )
        assert len(doc.pages) == 2
        assert doc.pages[0].page_num == 1
