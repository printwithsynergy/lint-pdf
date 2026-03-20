"""Tests for semantic events — frozen dataclasses emitted by the interpreter."""

from __future__ import annotations

# skipcq: PYL-R0201
import pytest

from grounded.semantic.events import (
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
from grounded.semantic.graphics_state import TransformationMatrix


class TestContentStreamEvent:
    """Test base event creation."""

    def test_create_base_event(self) -> None:
        event = ContentStreamEvent(operator="q", page_num=1, operator_index=0)
        assert event.operator == "q"
        assert event.page_num == 1
        assert event.operator_index == 0

    def test_frozen(self) -> None:
        event = ContentStreamEvent(operator="q", page_num=1, operator_index=0)
        with pytest.raises(AttributeError):
            event.operator = "Q"  # type: ignore[misc]


class TestImagePlacedEvent:
    """Test ImagePlacedEvent creation."""

    def test_create(self) -> None:
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

    def test_inline_image(self) -> None:
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

    def test_frozen(self) -> None:
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

    def test_create(self) -> None:
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

    def test_defaults(self) -> None:
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

    def test_fill_color(self) -> None:
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

    def test_stroke_color(self) -> None:
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

    def test_create(self) -> None:
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

    def test_partial_update(self) -> None:
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

    def test_create(self) -> None:
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

    def test_partial_update(self) -> None:
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

    def test_create(self) -> None:
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

    def test_fill_only(self) -> None:
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

    def test_fill_and_stroke(self) -> None:
        event = PathPaintingEvent(
            operator="B",
            page_num=1,
            operator_index=11,
            fill=True,
            stroke=True,
        )
        assert event.fill is True
        assert event.stroke is True

    def test_even_odd_fill(self) -> None:
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

    def test_winding(self) -> None:
        event = ClippingPathSetEvent(
            operator="W",
            page_num=1,
            operator_index=6,
        )
        assert event.even_odd is False

    def test_even_odd(self) -> None:
        event = ClippingPathSetEvent(
            operator="W*",
            page_num=1,
            operator_index=7,
            even_odd=True,
        )
        assert event.even_odd is True


class TestLineStyleChangedEvent:
    """Test LineStyleChangedEvent creation."""

    def test_create_line_cap(self) -> None:
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

    def test_create_line_join(self) -> None:
        event = LineStyleChangedEvent(
            operator="j",
            page_num=1,
            operator_index=6,
            line_join=2,
        )
        assert event.line_join == 2

    def test_create_dash_pattern(self) -> None:
        event = LineStyleChangedEvent(
            operator="d",
            page_num=1,
            operator_index=7,
            dash_pattern=((3.0, 2.0), 0.0),
        )
        assert event.dash_pattern == ((3.0, 2.0), 0.0)

    def test_create_miter_limit(self) -> None:
        event = LineStyleChangedEvent(
            operator="M",
            page_num=1,
            operator_index=8,
            miter_limit=5.0,
        )
        assert event.miter_limit == 5.0

    def test_create_rendering_intent(self) -> None:
        event = LineStyleChangedEvent(
            operator="ri",
            page_num=1,
            operator_index=9,
            rendering_intent="Perceptual",
        )
        assert event.rendering_intent == "Perceptual"

    def test_frozen(self) -> None:
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

    def test_line_style_defaults(self) -> None:
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

    def test_line_style_custom(self) -> None:
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

    def test_default_rendering_intent(self) -> None:
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

    def test_custom_rendering_intent(self) -> None:
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
