"""Tests for Part 3 event additions — PrepressStateChangedEvent, ImagePlacedEvent enrichment."""

from __future__ import annotations

from siftpdf.semantic.events import ImagePlacedEvent, PrepressStateChangedEvent
from siftpdf.semantic.graphics_state import TransformationMatrix


class TestPrepressStateChangedEvent:
    """Test PrepressStateChangedEvent."""

    @staticmethod
    def test_defaults() -> None:
        event = PrepressStateChangedEvent(operator="gs", page_num=1, operator_index=0)
        assert event.has_halftone is False
        assert event.has_transfer_function is False
        assert event.has_bg_ucr is False

    @staticmethod
    def test_halftone() -> None:
        event = PrepressStateChangedEvent(
            operator="gs", page_num=1, operator_index=0, has_halftone=True
        )
        assert event.has_halftone is True

    @staticmethod
    def test_transfer_function() -> None:
        event = PrepressStateChangedEvent(
            operator="gs",
            page_num=1,
            operator_index=0,
            has_transfer_function=True,
        )
        assert event.has_transfer_function is True

    @staticmethod
    def test_bg_ucr() -> None:
        event = PrepressStateChangedEvent(
            operator="gs", page_num=1, operator_index=0, has_bg_ucr=True
        )
        assert event.has_bg_ucr is True

    @staticmethod
    def test_frozen() -> None:
        event = PrepressStateChangedEvent(operator="gs", page_num=1, operator_index=0)
        try:
            event.has_halftone = True  # type: ignore[misc]
            raise AssertionError("Should not allow mutation")
        except AttributeError:
            pass


class TestImagePlacedEventEnrichment:
    """Test has_opi and has_alternate fields on ImagePlacedEvent."""

    @staticmethod
    def test_defaults_false() -> None:
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

    @staticmethod
    def test_has_opi() -> None:
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

    @staticmethod
    def test_has_alternate() -> None:
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
