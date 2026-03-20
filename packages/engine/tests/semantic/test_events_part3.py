"""Tests for Part 3 event additions — PrepressStateChangedEvent, ImagePlacedEvent enrichment."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.semantic.events import ImagePlacedEvent, PrepressStateChangedEvent
from grounded.semantic.graphics_state import TransformationMatrix


class TestPrepressStateChangedEvent:
    """Test PrepressStateChangedEvent."""

    def test_defaults(self) -> None:
        event = PrepressStateChangedEvent(operator="gs", page_num=1, operator_index=0)
        assert event.has_halftone is False
        assert event.has_transfer_function is False
        assert event.has_bg_ucr is False

    def test_halftone(self) -> None:
        event = PrepressStateChangedEvent(
            operator="gs", page_num=1, operator_index=0, has_halftone=True
        )
        assert event.has_halftone is True

    def test_transfer_function(self) -> None:
        event = PrepressStateChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=0,
            has_transfer_function=True,
        )
        assert event.has_transfer_function is True

    def test_bg_ucr(self) -> None:
        event = PrepressStateChangedEvent(
            operator="gs", page_num=1, operator_index=0, has_bg_ucr=True
        )
        assert event.has_bg_ucr is True

    def test_frozen(self) -> None:
        event = PrepressStateChangedEvent(operator="gs", page_num=1, operator_index=0)
        try:
            event.has_halftone = True  # type: ignore[misc]
            raise AssertionError("Should not allow mutation")
        except AttributeError:
            pass


class TestImagePlacedEventEnrichment:
    """Test has_opi and has_alternate fields on ImagePlacedEvent."""

    def test_defaults_false(self) -> None:
        event = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im1",
            ctm=TransformationMatrix(),
            pixel_width=100,
            pixel_height=100,
        )
        assert event.has_opi is False
        assert event.has_alternate is False

    def test_has_opi(self) -> None:
        event = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im1",
            ctm=TransformationMatrix(),
            pixel_width=100,
            pixel_height=100,
            has_opi=True,
        )
        assert event.has_opi is True

    def test_has_alternate(self) -> None:
        event = ImagePlacedEvent(
            operator="Do",
            page_num=1,
            operator_index=0,
            image_name="Im1",
            ctm=TransformationMatrix(),
            pixel_width=100,
            pixel_height=100,
            has_alternate=True,
        )
        assert event.has_alternate is True
