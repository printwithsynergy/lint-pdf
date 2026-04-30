"""Tests for Part 3 graphics state additions — prepress fields."""

from __future__ import annotations

from siftpdf.semantic.graphics_state import GraphicsState


class TestPrepressState:
    """Test halftone, transfer function, and BG/UCR fields."""

    @staticmethod
    def test_defaults_false() -> None:
        gs = GraphicsState()
        assert gs.has_halftone is False
        assert gs.has_transfer_function is False
        assert gs.has_bg_ucr is False

    @staticmethod
    def test_set_halftone() -> None:
        gs = GraphicsState()
        gs.has_halftone = True
        assert gs.has_halftone is True

    @staticmethod
    def test_set_transfer_function() -> None:
        gs = GraphicsState()
        gs.has_transfer_function = True
        assert gs.has_transfer_function is True

    @staticmethod
    def test_set_bg_ucr() -> None:
        gs = GraphicsState()
        gs.has_bg_ucr = True
        assert gs.has_bg_ucr is True

    @staticmethod
    def test_copy_preserves_prepress() -> None:
        gs = GraphicsState()
        gs.has_halftone = True
        gs.has_transfer_function = True
        gs.has_bg_ucr = True

        copied = gs.copy()
        assert copied.has_halftone is True
        assert copied.has_transfer_function is True
        assert copied.has_bg_ucr is True

    @staticmethod
    def test_copy_independent() -> None:
        gs = GraphicsState()
        gs.has_halftone = True
        copied = gs.copy()
        copied.has_halftone = False
        assert gs.has_halftone is True
