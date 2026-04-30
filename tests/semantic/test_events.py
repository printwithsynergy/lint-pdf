"""Tests for semantic events — frozen dataclasses emitted by the interpreter."""

from __future__ import annotations

import pytest

from siftpdf.semantic.events import (
    ClippingPathSetEvent,
    ColorChangedEvent,
    ContentStreamEvent,
    FormXObjectEnteredEvent,
    ImagePlacedEvent,
    LineStyleChangedEvent,
    OpacityChangedEvent,
    OverprintChangedEvent,
    PathPaintingEvent,
    TextRenderedEvent,
)
from siftpdf.semantic.graphics_state import TransformationMatrix


class TestContentStreamEvent:
    """Test base event creation."""

    @staticmethod
    def test_create_base_event() -> None:
        event = ContentStreamEvent(operator="q", page_num=1, operator_index=0)
        assert event.operator == "q"
        assert event.page_num == 1
        assert event.operator_index == 0

    @staticmethod
    def test_frozen() -> None:
        event = ContentStreamEvent(operator="q", page_num=1, operator_index=0)
        with pytest.raises(AttributeError):
            event.operator = "Q"  # type: ignore[misc]


class TestImagePlacedEvent:
    """Test ImagePlacedEvent creation."""

    @staticmethod
    def test_create() -> None:
        ctm = TransformationMatrix(a=200, b=0, c=0, d=300, e=100, f=400)
        event = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=5,
            image_name="Im1",
            ctm=ctm,
            pixel_width=1000,
            pixel_height=800,
            bits_per_component=8,
            color_space="DeviceRGB",
        )
        assert event.image_name == "Im1"
        assert event.pixel_width == 1000
        assert event.ctm.a == 200.0

    @staticmethod
    def test_inline_image() -> None:
        event = ImagePlacedEvent(
            operator="BI_ID_EI",
            page_num=1,
            operator_index=10,
            image_name="inline_1",
            ctm=TransformationMatrix(),
            pixel_width=50,
            pixel_height=50,
            is_inline=True,
        )
        assert event.is_inline is True

    @staticmethod
    def test_frozen() -> None:
        event = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im1",
            ctm=TransformationMatrix(),
            pixel_width=100,
            pixel_height=100,
        )
        with pytest.raises(AttributeError):
            event.pixel_width = 200  # type: ignore[misc]


class TestTextRenderedEvent:
    """Test TextRenderedEvent creation."""

    @staticmethod
    def test_create() -> None:
        event = TextRenderedEvent(
            operator="Tj",
            page_num=1,
            operator_index=8,
            font_name="F1",
            font_size=12.0,
            ctm=TransformationMatrix(),
            text_matrix=TransformationMatrix(a=1, b=0, c=0, d=1, e=72, f=720),
            color_space="DeviceGray",
            color_values=(0.0,),
            opacity=1.0,
        )
        assert event.font_name == "F1"
        assert event.font_size == 12.0
        assert event.text_matrix.e == 72.0

    @staticmethod
    def test_defaults() -> None:
        event = TextRenderedEvent(
            operator="Tj",
            page_num=1,
            operator_index=0,
            font_name="F1",
            font_size=10.0,
            ctm=TransformationMatrix(),
            text_matrix=TransformationMatrix(),
        )
        assert event.color_space == "DeviceGray"
        assert event.opacity == 1.0
        assert event.rendering_mode == 0


class TestColorChangedEvent:
    """Test ColorChangedEvent creation."""

    @staticmethod
    def test_fill_color() -> None:
        event = ColorChangedEvent(
            operator="rg",
            page_num=1,
            operator_index=3,
            stroking=False,
            color_space="DeviceRGB",
            color_values=(1.0, 0.0, 0.0),
        )
        assert event.stroking is False
        assert event.color_space == "DeviceRGB"
        assert event.color_values == (1.0, 0.0, 0.0)

    @staticmethod
    def test_stroke_color() -> None:
        event = ColorChangedEvent(
            operator="K",
            page_num=1,
            operator_index=4,
            stroking=True,
            color_space="DeviceCMYK",
            color_values=(0.0, 1.0, 1.0, 0.0),
        )
        assert event.stroking is True
        assert event.color_space == "DeviceCMYK"


class TestOpacityChangedEvent:
    """Test OpacityChangedEvent creation."""

    @staticmethod
    def test_create() -> None:
        event = OpacityChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=2,
            stroking_alpha=0.5,
            non_stroking_alpha=0.8,
            blend_mode="Multiply",
        )
        assert event.stroking_alpha == 0.5
        assert event.non_stroking_alpha == 0.8
        assert event.blend_mode == "Multiply"

    @staticmethod
    def test_partial_update() -> None:
        event = OpacityChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=2,
            non_stroking_alpha=0.3,
        )
        assert event.stroking_alpha is None
        assert event.non_stroking_alpha == 0.3
        assert event.blend_mode is None


class TestOverprintChangedEvent:
    """Test OverprintChangedEvent creation."""

    @staticmethod
    def test_create() -> None:
        event = OverprintChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=2,
            overprint_stroking=True,
            overprint_non_stroking=True,
            overprint_mode=1,
        )
        assert event.overprint_stroking is True
        assert event.overprint_mode == 1

    @staticmethod
    def test_partial_update() -> None:
        event = OverprintChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=2,
            overprint_mode=1,
        )
        assert event.overprint_stroking is None
        assert event.overprint_non_stroking is None
        assert event.overprint_mode == 1


class TestFormXObjectEnteredEvent:
    """Test FormXObjectEnteredEvent creation."""

    @staticmethod
    def test_create() -> None:
        event = FormXObjectEnteredEvent(
            operator="Do",
            page_num=1,
            operator_index=5,
            form_name="Fm1",
            form_matrix=TransformationMatrix(a=1, b=0, c=0, d=1, e=50, f=100),
            ctm=TransformationMatrix(a=2, b=0, c=0, d=2, e=0, f=0),
            nesting_depth=1,
        )
        assert event.form_name == "Fm1"
        assert event.nesting_depth == 1
        assert event.ctm.a == 2.0


class TestPathPaintingEvent:
    """Test PathPaintingEvent creation."""

    @staticmethod
    def test_fill_only() -> None:
        event = PathPaintingEvent(
            operator="f",
            page_num=1,
            operator_index=10,
            fill=True,
            stroke=False,
            fill_color_space="DeviceCMYK",
            fill_color_values=(0.0, 1.0, 1.0, 0.0),
        )
        assert event.fill is True
        assert event.stroke is False
        assert event.even_odd is False

    @staticmethod
    def test_fill_and_stroke() -> None:
        event = PathPaintingEvent(
            operator="B",
            page_num=1,
            operator_index=11,
            fill=True,
            stroke=True,
        )
        assert event.fill is True
        assert event.stroke is True

    @staticmethod
    def test_even_odd_fill() -> None:
        event = PathPaintingEvent(
            operator="f*",
            page_num=1,
            operator_index=12,
            fill=True,
            stroke=False,
            even_odd=True,
        )
        assert event.even_odd is True


class TestClippingPathSetEvent:
    """Test ClippingPathSetEvent creation."""

    @staticmethod
    def test_winding() -> None:
        event = ClippingPathSetEvent(
            operator="W",
            page_num=1,
            operator_index=6,
        )
        assert event.even_odd is False

    @staticmethod
    def test_even_odd() -> None:
        event = ClippingPathSetEvent(
            operator="W*",
            page_num=1,
            operator_index=7,
            even_odd=True,
        )
        assert event.even_odd is True


class TestLineStyleChangedEvent:
    """Test LineStyleChangedEvent creation."""

    @staticmethod
    def test_create_line_cap() -> None:
        event = LineStyleChangedEvent(
            operator="J",
            page_num=1,
            operator_index=5,
            line_cap=1,
        )
        assert event.line_cap == 1
        assert event.line_join is None
        assert event.dash_pattern is None
        assert event.miter_limit is None
        assert event.rendering_intent is None

    @staticmethod
    def test_create_line_join() -> None:
        event = LineStyleChangedEvent(
            operator="j",
            page_num=1,
            operator_index=6,
            line_join=2,
        )
        assert event.line_join == 2

    @staticmethod
    def test_create_dash_pattern() -> None:
        event = LineStyleChangedEvent(
            operator="d",
            page_num=1,
            operator_index=7,
            dash_pattern=((3.0, 2.0), 0.0),
        )
        assert event.dash_pattern == ((3.0, 2.0), 0.0)

    @staticmethod
    def test_create_miter_limit() -> None:
        event = LineStyleChangedEvent(
            operator="M",
            page_num=1,
            operator_index=8,
            miter_limit=5.0,
        )
        assert event.miter_limit == 5.0

    @staticmethod
    def test_create_rendering_intent() -> None:
        event = LineStyleChangedEvent(
            operator="ri",
            page_num=1,
            operator_index=9,
            rendering_intent="Perceptual",
        )
        assert event.rendering_intent == "Perceptual"

    @staticmethod
    def test_frozen() -> None:
        event = LineStyleChangedEvent(
            operator="J",
            page_num=1,
            operator_index=0,
            line_cap=1,
        )
        with pytest.raises(AttributeError):
            event.line_cap = 2  # type: ignore[misc]


class TestPathPaintingEventLineStyle:
    """Test PathPaintingEvent line style fields."""

    @staticmethod
    def test_line_style_defaults() -> None:
        event = PathPaintingEvent(
            operator="S",
            page_num=1,
            operator_index=0,
            fill=False,
            stroke=True,
        )
        assert event.line_cap == 0
        assert event.line_join == 0
        assert event.dash_pattern == ((), 0.0)

    @staticmethod
    def test_line_style_custom() -> None:
        event = PathPaintingEvent(
            operator="S",
            page_num=1,
            operator_index=0,
            fill=False,
            stroke=True,
            line_width=0.5,
            line_cap=1,
            line_join=2,
            dash_pattern=((4.0, 2.0), 1.0),
        )
        assert event.line_cap == 1
        assert event.line_join == 2
        assert event.dash_pattern == ((4.0, 2.0), 1.0)
        assert event.line_width == 0.5


class TestTextRenderedEventRenderingIntent:
    """Test TextRenderedEvent rendering_intent field."""

    @staticmethod
    def test_default_rendering_intent() -> None:
        event = TextRenderedEvent(
            operator="Tj",
            page_num=1,
            operator_index=0,
            font_name="F1",
            font_size=12.0,
            ctm=TransformationMatrix(),
            text_matrix=TransformationMatrix(),
        )
        assert event.rendering_intent == "RelativeColorimetric"

    @staticmethod
    def test_custom_rendering_intent() -> None:
        event = TextRenderedEvent(
            operator="Tj",
            page_num=1,
            operator_index=0,
            font_name="F1",
            font_size=12.0,
            ctm=TransformationMatrix(),
            text_matrix=TransformationMatrix(),
            rendering_intent="Perceptual",
        )
        assert event.rendering_intent == "Perceptual"
