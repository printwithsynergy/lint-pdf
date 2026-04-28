"""Tests for ContentStreamInterpreter — operator handling and event emission."""

from __future__ import annotations

from lintpdf.semantic.events import (
    ClippingPathSetEvent,
    ColorChangedEvent,
    FormXObjectEnteredEvent,
    ImagePlacedEvent,
    LineStyleChangedEvent,
    OpacityChangedEvent,
    OverprintChangedEvent,
    PathPaintingEvent,
    TextRenderedEvent,
)
from lintpdf.semantic.interpreter import ContentStreamInterpreter


def _make_interpreter(resources: dict | None = None, page_num: int = 1) -> ContentStreamInterpreter:
    """Helper to create interpreter with optional resources."""
    return ContentStreamInterpreter(
        page_num=page_num,
        resources=resources or {},
    )


# --- Graphics State Tests (q, Q, cm) ---


class TestGraphicsState:
    """Test q/Q state stack and cm matrix concatenation."""

    @staticmethod
    def test_q_Q_stack_balance() -> None:
        interp = _make_interpreter()
        instructions = [
            ([], "q"),
            ([], "Q"),
        ]
        interp.interpret(instructions)
        assert len(interp._state_stack) == 1

    @staticmethod
    def test_q_pushes_copy() -> None:
        interp = _make_interpreter()
        interp.state.font_name = "F1"
        instructions = [
            ([], "q"),
        ]
        interp.interpret(instructions)
        assert len(interp._state_stack) == 2
        assert interp.state.font_name == "F1"

    @staticmethod
    def test_Q_restores_state() -> None:
        interp = _make_interpreter()
        interp.state.font_name = "F1"
        instructions = [
            ([], "q"),
            # Change state in nested scope
        ]
        interp.interpret(instructions)
        interp.state.font_name = "F2"
        interp.interpret([([], "Q")])
        assert interp.state.font_name == "F1"

    @staticmethod
    def test_Q_without_q_no_crash() -> None:
        interp = _make_interpreter()
        interp.interpret([([], "Q")])
        assert len(interp._state_stack) == 1

    @staticmethod
    def test_cm_concatenates_matrix() -> None:
        interp = _make_interpreter()
        instructions = [
            ([200, 0, 0, 300, 100, 400], "cm"),
        ]
        interp.interpret(instructions)
        # cm concatenates: new_matrix x CTM
        # new_matrix = [200,0,0,300,100,400], CTM = identity
        assert interp.state.ctm.a == 200.0
        assert interp.state.ctm.d == 300.0
        assert interp.state.ctm.e == 100.0
        assert interp.state.ctm.f == 400.0

    @staticmethod
    def test_cm_cumulative() -> None:
        interp = _make_interpreter()
        instructions = [
            ([2, 0, 0, 2, 0, 0], "cm"),  # Scale 2x
            ([1, 0, 0, 1, 50, 100], "cm"),  # Translate 50, 100
        ]
        interp.interpret(instructions)
        # After scale 2x: CTM = [2,0,0,2,0,0]
        # Then translate: new=[1,0,0,1,50,100] x CTM=[2,0,0,2,0,0]
        # Result: a=2, d=2, e=100, f=200
        assert interp.state.ctm.a == 2.0
        assert interp.state.ctm.e == 100.0
        assert interp.state.ctm.f == 200.0


# --- ExtGState Tests (gs) ---


class TestExtGState:
    """Test gs operator — opacity, blend mode, overprint."""

    @staticmethod
    def test_gs_sets_opacity() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/CA": 0.5, "/ca": 0.8},
            },
        }
        interp = _make_interpreter(resources)
        events = interp.interpret([(["/GS1"], "gs")])

        assert interp.state.stroking_alpha == 0.5
        assert interp.state.non_stroking_alpha == 0.8

        opacity_events = [e for e in events if isinstance(e, OpacityChangedEvent)]
        assert len(opacity_events) == 1
        assert opacity_events[0].stroking_alpha == 0.5
        assert opacity_events[0].non_stroking_alpha == 0.8

    @staticmethod
    def test_gs_sets_blend_mode() -> None:
        resources = {
            "/ExtGState": {
                "/GS2": {"/BM": "/Multiply"},
            },
        }
        interp = _make_interpreter(resources)
        events = interp.interpret([(["/GS2"], "gs")])

        assert interp.state.blend_mode == "Multiply"
        opacity_events = [e for e in events if isinstance(e, OpacityChangedEvent)]
        assert len(opacity_events) == 1
        assert opacity_events[0].blend_mode == "Multiply"

    @staticmethod
    def test_gs_sets_overprint() -> None:
        resources = {
            "/ExtGState": {
                "/GS3": {"/OP": True, "/op": True, "/OPM": 1},
            },
        }
        interp = _make_interpreter(resources)
        events = interp.interpret([(["/GS3"], "gs")])

        assert interp.state.overprint_stroking is True
        assert interp.state.overprint_non_stroking is True
        assert interp.state.overprint_mode == 1

        op_events = [e for e in events if isinstance(e, OverprintChangedEvent)]
        assert len(op_events) == 1
        assert op_events[0].overprint_mode == 1

    @staticmethod
    def test_gs_unknown_name_no_crash() -> None:
        interp = _make_interpreter()
        events = interp.interpret([(["/Unknown"], "gs")])
        assert len(events) == 0


# --- Text Tests (BT, ET, Tf, Tj, TJ, Tm) ---


class TestTextOperators:
    """Test text object operators."""

    @staticmethod
    def test_Tf_sets_font() -> None:
        interp = _make_interpreter()
        interp.interpret([(["/F1", 12], "Tf")])
        assert interp.state.font_name == "F1"
        assert interp.state.font_size == 12.0

    @staticmethod
    def test_Tj_emits_text_event() -> None:
        interp = _make_interpreter()
        instructions = [
            ([], "BT"),
            (["/F1", 12], "Tf"),
            (["Hello"], "Tj"),
            ([], "ET"),
        ]
        events = interp.interpret(instructions)
        text_events = [e for e in events if isinstance(e, TextRenderedEvent)]
        assert len(text_events) == 1
        assert text_events[0].font_name == "F1"
        assert text_events[0].font_size == 12.0
        assert text_events[0].operator == "Tj"

    @staticmethod
    def test_TJ_emits_text_event() -> None:
        interp = _make_interpreter()
        instructions = [
            ([], "BT"),
            (["/F1", 10], "Tf"),
            ([["Hello", -50, "World"]], "TJ"),
            ([], "ET"),
        ]
        events = interp.interpret(instructions)
        text_events = [e for e in events if isinstance(e, TextRenderedEvent)]
        assert len(text_events) == 1
        assert text_events[0].operator == "TJ"

    @staticmethod
    def test_Tm_sets_text_matrix() -> None:
        interp = _make_interpreter()
        instructions = [
            ([], "BT"),
            ([1, 0, 0, 1, 72, 720], "Tm"),
        ]
        interp.interpret(instructions)
        assert interp.state.text_matrix.e == 72.0
        assert interp.state.text_matrix.f == 720.0

    @staticmethod
    def test_Td_moves_text_position() -> None:
        interp = _make_interpreter()
        instructions = [
            ([], "BT"),
            ([100, 700], "Td"),
        ]
        interp.interpret(instructions)
        assert interp.state.text_matrix.e == 100.0
        assert interp.state.text_matrix.f == 700.0

    @staticmethod
    def test_text_event_captures_color() -> None:
        interp = _make_interpreter()
        instructions = [
            ([1.0, 0.0, 0.0], "rg"),
            ([], "BT"),
            (["/F1", 12], "Tf"),
            (["Text"], "Tj"),
            ([], "ET"),
        ]
        events = interp.interpret(instructions)
        text_events = [e for e in events if isinstance(e, TextRenderedEvent)]
        assert len(text_events) == 1
        assert text_events[0].color_space == "DeviceRGB"
        assert text_events[0].color_values == (1.0, 0.0, 0.0)


# --- Color Tests ---


class TestColorOperators:
    """Test color operator handling."""

    @staticmethod
    def test_rg_sets_fill_rgb() -> None:
        interp = _make_interpreter()
        events = interp.interpret([([1.0, 0.0, 0.0], "rg")])
        assert interp.state.non_stroking_color_space == "DeviceRGB"
        assert interp.state.non_stroking_color == [1.0, 0.0, 0.0]
        color_events = [e for e in events if isinstance(e, ColorChangedEvent)]
        assert len(color_events) == 1
        assert color_events[0].stroking is False
        assert color_events[0].color_space == "DeviceRGB"

    @staticmethod
    def test_RG_sets_stroke_rgb() -> None:
        interp = _make_interpreter()
        events = interp.interpret([([0.0, 1.0, 0.0], "RG")])
        assert interp.state.stroking_color_space == "DeviceRGB"
        color_events = [e for e in events if isinstance(e, ColorChangedEvent)]
        assert len(color_events) == 1
        assert color_events[0].stroking is True

    @staticmethod
    def test_k_sets_fill_cmyk() -> None:
        interp = _make_interpreter()
        interp.interpret([([0.0, 1.0, 1.0, 0.0], "k")])
        assert interp.state.non_stroking_color_space == "DeviceCMYK"
        assert interp.state.non_stroking_color == [0.0, 1.0, 1.0, 0.0]

    @staticmethod
    def test_K_sets_stroke_cmyk() -> None:
        interp = _make_interpreter()
        interp.interpret([([0.5, 0.5, 0.5, 0.5], "K")])
        assert interp.state.stroking_color_space == "DeviceCMYK"

    @staticmethod
    def test_g_sets_fill_gray() -> None:
        interp = _make_interpreter()
        interp.interpret([([0.5], "g")])
        assert interp.state.non_stroking_color_space == "DeviceGray"
        assert interp.state.non_stroking_color == [0.5]

    @staticmethod
    def test_G_sets_stroke_gray() -> None:
        interp = _make_interpreter()
        interp.interpret([([0.8], "G")])
        assert interp.state.stroking_color_space == "DeviceGray"

    @staticmethod
    def test_cs_sets_color_space() -> None:
        interp = _make_interpreter()
        interp.interpret([(["/CS1"], "cs")])
        assert interp.state.non_stroking_color_space == "CS1"

    @staticmethod
    def test_CS_sets_stroking_color_space() -> None:
        interp = _make_interpreter()
        interp.interpret([(["/CS2"], "CS")])
        assert interp.state.stroking_color_space == "CS2"


# --- XObject Tests (Do) ---


class TestDoOperator:
    """Test Do operator for images and forms."""

    @staticmethod
    def test_image_xobject_emits_event() -> None:
        resources = {
            "/XObject": {
                "/Im1": {
                    "/Subtype": "/Image",
                    "/Width": 1000,
                    "/Height": 800,
                    "/BitsPerComponent": 8,
                    "/ColorSpace": "/DeviceRGB",
                },
            },
        }
        interp = _make_interpreter(resources)
        # Set CTM to place image
        interp.interpret([([200, 0, 0, 300, 100, 400], "cm")])
        events = interp.interpret([(["/Im1"], "Do")])

        img_events = [e for e in events if isinstance(e, ImagePlacedEvent)]
        assert len(img_events) == 1
        assert img_events[0].image_name == "Im1"
        assert img_events[0].pixel_width == 1000
        assert img_events[0].pixel_height == 800
        assert img_events[0].ctm.a == 200.0

    @staticmethod
    def test_form_xobject_emits_event() -> None:
        resources = {
            "/XObject": {
                "/Fm1": {
                    "/Subtype": "/Form",
                    "/Matrix": [1, 0, 0, 1, 50, 100],
                    "/Resources": {},
                },
            },
        }
        interp = _make_interpreter(resources)
        events = interp.interpret([(["/Fm1"], "Do")])

        form_events = [e for e in events if isinstance(e, FormXObjectEnteredEvent)]
        assert len(form_events) == 1
        assert form_events[0].form_name == "Fm1"
        assert form_events[0].nesting_depth == 1

    @staticmethod
    def test_unknown_xobject_no_crash() -> None:
        interp = _make_interpreter()
        events = interp.interpret([(["/Unknown"], "Do")])
        assert len(events) == 0

    @staticmethod
    def test_image_with_soft_mask() -> None:
        resources = {
            "/XObject": {
                "/Im2": {
                    "/Subtype": "/Image",
                    "/Width": 500,
                    "/Height": 500,
                    "/BitsPerComponent": 8,
                    "/ColorSpace": "/DeviceCMYK",
                    "/SMask": {"some": "mask"},
                },
            },
        }
        interp = _make_interpreter(resources)
        events = interp.interpret([(["/Im2"], "Do")])
        img_events = [e for e in events if isinstance(e, ImagePlacedEvent)]
        assert img_events[0].has_soft_mask is True


# --- Path Tests ---


class TestPathOperators:
    """Test path construction and painting."""

    @staticmethod
    def test_stroke_path() -> None:
        interp = _make_interpreter()
        instructions = [
            ([100, 200], "m"),
            ([300, 400], "l"),
            ([], "S"),
        ]
        events = interp.interpret(instructions)
        path_events = [e for e in events if isinstance(e, PathPaintingEvent)]
        assert len(path_events) == 1
        assert path_events[0].stroke is True
        assert path_events[0].fill is False

    @staticmethod
    def test_fill_path() -> None:
        interp = _make_interpreter()
        instructions = [
            ([0, 0, 100, 100], "re"),
            ([], "f"),
        ]
        events = interp.interpret(instructions)
        path_events = [e for e in events if isinstance(e, PathPaintingEvent)]
        assert len(path_events) == 1
        assert path_events[0].fill is True
        assert path_events[0].stroke is False
        assert path_events[0].even_odd is False

    @staticmethod
    def test_fill_even_odd() -> None:
        interp = _make_interpreter()
        instructions = [
            ([0, 0, 100, 100], "re"),
            ([], "f*"),
        ]
        events = interp.interpret(instructions)
        path_events = [e for e in events if isinstance(e, PathPaintingEvent)]
        assert path_events[0].even_odd is True

    @staticmethod
    def test_fill_and_stroke() -> None:
        interp = _make_interpreter()
        instructions = [
            ([0, 0, 100, 100], "re"),
            ([], "B"),
        ]
        events = interp.interpret(instructions)
        path_events = [e for e in events if isinstance(e, PathPaintingEvent)]
        assert path_events[0].fill is True
        assert path_events[0].stroke is True

    @staticmethod
    def test_path_captures_colors() -> None:
        interp = _make_interpreter()
        instructions = [
            ([0.0, 1.0, 1.0, 0.0], "k"),  # Fill CMYK
            ([1.0, 0.0, 0.0], "RG"),  # Stroke RGB
            ([0, 0, 100, 100], "re"),
            ([], "B"),
        ]
        events = interp.interpret(instructions)
        path_events = [e for e in events if isinstance(e, PathPaintingEvent)]
        assert path_events[0].fill_color_space == "DeviceCMYK"
        assert path_events[0].stroke_color_space == "DeviceRGB"

    @staticmethod
    def test_line_width_tracked() -> None:
        interp = _make_interpreter()
        instructions = [
            ([0.25], "w"),
            ([0, 0, 100, 0], "m"),
            ([100, 0], "l"),
            ([], "S"),
        ]
        events = interp.interpret(instructions)
        path_events = [e for e in events if isinstance(e, PathPaintingEvent)]
        assert path_events[0].line_width == 0.25


# --- Clipping Tests ---


class TestClippingOperators:
    """Test clipping path operators."""

    @staticmethod
    def test_W_emits_event() -> None:
        interp = _make_interpreter()
        events = interp.interpret([([], "W")])
        clip_events = [e for e in events if isinstance(e, ClippingPathSetEvent)]
        assert len(clip_events) == 1
        assert clip_events[0].even_odd is False

    @staticmethod
    def test_W_star_emits_event() -> None:
        interp = _make_interpreter()
        events = interp.interpret([([], "W*")])
        clip_events = [e for e in events if isinstance(e, ClippingPathSetEvent)]
        assert clip_events[0].even_odd is True


# --- Inline Image Tests ---


class TestInlineImage:
    """Test inline image handling."""

    @staticmethod
    def test_inline_image_emits_event() -> None:
        interp = _make_interpreter()
        events = interp.interpret([([], "BI_ID_EI")])
        img_events = [e for e in events if isinstance(e, ImagePlacedEvent)]
        assert len(img_events) == 1
        assert img_events[0].is_inline is True


# --- Integration Tests ---


class TestIntegration:
    """Integration tests: realistic content stream sequences."""

    @staticmethod
    def test_typical_text_page() -> None:
        """Simulate a page with text in different fonts and colors."""
        resources = {
            "/ExtGState": {
                "/GS0": {"/ca": 1.0, "/CA": 1.0},
            },
        }
        interp = _make_interpreter(resources)
        instructions = [
            (["/GS0"], "gs"),
            ([], "BT"),
            (["/F1", 12], "Tf"),
            ([1, 0, 0, 1, 72, 720], "Tm"),
            ([0.0, 0.0, 0.0], "rg"),
            (["Hello World"], "Tj"),
            (["/F2", 10], "Tf"),
            ([0, -14], "Td"),
            ([0.5, 0.5, 0.5], "rg"),
            (["Second line"], "Tj"),
            ([], "ET"),
        ]
        events = interp.interpret(instructions)

        text_events = [e for e in events if isinstance(e, TextRenderedEvent)]
        assert len(text_events) == 2
        assert text_events[0].font_name == "F1"
        assert text_events[1].font_name == "F2"

    @staticmethod
    def test_image_with_ctm() -> None:
        """Simulate placing an image with specific CTM."""
        resources = {
            "/XObject": {
                "/Im1": {
                    "/Subtype": "/Image",
                    "/Width": 2000,
                    "/Height": 1500,
                    "/BitsPerComponent": 8,
                    "/ColorSpace": "/DeviceRGB",
                },
            },
        }
        interp = _make_interpreter(resources)
        instructions = [
            ([], "q"),
            ([200, 0, 0, 150, 72, 500], "cm"),
            (["/Im1"], "Do"),
            ([], "Q"),
        ]
        events = interp.interpret(instructions)

        img_events = [e for e in events if isinstance(e, ImagePlacedEvent)]
        assert len(img_events) == 1
        assert img_events[0].ctm.a == 200.0
        assert img_events[0].ctm.d == 150.0
        assert img_events[0].pixel_width == 2000
        assert img_events[0].pixel_height == 1500

        # After Q, CTM should be restored to identity
        assert interp.state.ctm.is_identity()

    @staticmethod
    def test_mixed_content() -> None:
        """Simulate a page with text, images, and paths."""
        resources = {
            "/XObject": {
                "/Im1": {
                    "/Subtype": "/Image",
                    "/Width": 100,
                    "/Height": 100,
                    "/BitsPerComponent": 8,
                    "/ColorSpace": "/DeviceRGB",
                },
            },
        }
        interp = _make_interpreter(resources)
        instructions = [
            # Draw a rectangle
            ([0.0, 0.0, 0.0, 1.0], "k"),
            ([10, 10, 200, 300], "re"),
            ([], "f"),
            # Place an image
            ([], "q"),
            ([100, 0, 0, 100, 50, 50], "cm"),
            (["/Im1"], "Do"),
            ([], "Q"),
            # Render text
            ([], "BT"),
            (["/F1", 12], "Tf"),
            ([72, 700], "Td"),
            (["Title"], "Tj"),
            ([], "ET"),
        ]
        events = interp.interpret(instructions)

        color_events = [e for e in events if isinstance(e, ColorChangedEvent)]
        path_events = [e for e in events if isinstance(e, PathPaintingEvent)]
        img_events = [e for e in events if isinstance(e, ImagePlacedEvent)]
        text_events = [e for e in events if isinstance(e, TextRenderedEvent)]

        assert len(color_events) >= 1
        assert len(path_events) == 1
        assert len(img_events) == 1
        assert len(text_events) == 1

    @staticmethod
    def test_unrecognized_operator_no_crash() -> None:
        """Unrecognized operators should be silently skipped."""
        interp = _make_interpreter()
        events = interp.interpret(
            [
                ([], "BMC"),  # Deferrable marked content
                ([], "EMC"),
                ([42], "SomeWeirdOp"),
            ]
        )
        # No crash, no events for unrecognized operators
        assert len(events) == 0


# --- Line Style Operator Tests (J, j, d, M, i, ri) ---


class TestLineStyleOperators:
    """Test line style operator handling."""

    @staticmethod
    def test_J_sets_line_cap() -> None:
        interp = _make_interpreter()
        events = interp.interpret([([1], "J")])
        assert interp.state.line_cap == 1
        ls_events = [e for e in events if isinstance(e, LineStyleChangedEvent)]
        assert len(ls_events) == 1
        assert ls_events[0].line_cap == 1
        assert ls_events[0].operator == "J"

    @staticmethod
    def test_j_sets_line_join() -> None:
        interp = _make_interpreter()
        events = interp.interpret([([2], "j")])
        assert interp.state.line_join == 2
        ls_events = [e for e in events if isinstance(e, LineStyleChangedEvent)]
        assert len(ls_events) == 1
        assert ls_events[0].line_join == 2

    @staticmethod
    def test_d_sets_dash_pattern() -> None:
        interp = _make_interpreter()
        events = interp.interpret([([[3.0, 2.0], 0.0], "d")])
        assert interp.state.dash_pattern == ((3.0, 2.0), 0.0)
        ls_events = [e for e in events if isinstance(e, LineStyleChangedEvent)]
        assert len(ls_events) == 1
        assert ls_events[0].dash_pattern == ((3.0, 2.0), 0.0)

    @staticmethod
    def test_d_solid_line() -> None:
        """Empty dash array = solid line."""
        interp = _make_interpreter()
        interp.interpret([([[], 0.0], "d")])
        assert interp.state.dash_pattern == ((), 0.0)

    @staticmethod
    def test_M_sets_miter_limit() -> None:
        interp = _make_interpreter()
        events = interp.interpret([([5.0], "M")])
        assert interp.state.miter_limit == 5.0
        ls_events = [e for e in events if isinstance(e, LineStyleChangedEvent)]
        assert len(ls_events) == 1
        assert ls_events[0].miter_limit == 5.0

    @staticmethod
    def test_i_sets_flatness() -> None:
        interp = _make_interpreter()
        interp.interpret([([0.5], "i")])
        assert interp.state.flatness == 0.5

    @staticmethod
    def test_i_no_event() -> None:
        """Flatness does not emit a LineStyleChangedEvent."""
        interp = _make_interpreter()
        events = interp.interpret([([0.5], "i")])
        ls_events = [e for e in events if isinstance(e, LineStyleChangedEvent)]
        assert len(ls_events) == 0

    @staticmethod
    def test_ri_sets_rendering_intent() -> None:
        interp = _make_interpreter()
        events = interp.interpret([(["/Perceptual"], "ri")])
        assert interp.state.rendering_intent == "Perceptual"
        ls_events = [e for e in events if isinstance(e, LineStyleChangedEvent)]
        assert len(ls_events) == 1
        assert ls_events[0].rendering_intent == "Perceptual"

    @staticmethod
    def test_line_style_in_path_event() -> None:
        """Path events should carry current line style."""
        interp = _make_interpreter()
        instructions = [
            ([1], "J"),  # round cap
            ([2], "j"),  # bevel join
            ([[4.0, 2.0], 1.0], "d"),  # dash pattern
            ([0, 0, 100, 0], "m"),
            ([100, 0], "l"),
            ([], "S"),
        ]
        events = interp.interpret(instructions)
        path_events = [e for e in events if isinstance(e, PathPaintingEvent)]
        assert len(path_events) == 1
        assert path_events[0].line_cap == 1
        assert path_events[0].line_join == 2
        assert path_events[0].dash_pattern == ((4.0, 2.0), 1.0)

    @staticmethod
    def test_line_style_saved_restored() -> None:
        """Line style should be saved/restored with q/Q."""
        interp = _make_interpreter()
        instructions = [
            ([1], "J"),  # round cap
            ([], "q"),
            ([2], "J"),  # projecting square cap in nested scope
        ]
        interp.interpret(instructions)
        assert interp.state.line_cap == 2
        interp.interpret([([], "Q")])
        assert interp.state.line_cap == 1


class TestExtGStateLineStyle:
    """Test gs operator line style extraction from ExtGState."""

    @staticmethod
    def test_gs_sets_line_cap() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/LC": 1},
            },
        }
        interp = _make_interpreter(resources)
        interp.interpret([(["/GS1"], "gs")])
        assert interp.state.line_cap == 1

    @staticmethod
    def test_gs_sets_line_join() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/LJ": 2},
            },
        }
        interp = _make_interpreter(resources)
        interp.interpret([(["/GS1"], "gs")])
        assert interp.state.line_join == 2

    @staticmethod
    def test_gs_sets_miter_limit() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/ML": 5.0},
            },
        }
        interp = _make_interpreter(resources)
        interp.interpret([(["/GS1"], "gs")])
        assert interp.state.miter_limit == 5.0

    @staticmethod
    def test_gs_sets_dash_pattern() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/D": [[3.0, 2.0], 0.0]},
            },
        }
        interp = _make_interpreter(resources)
        interp.interpret([(["/GS1"], "gs")])
        assert interp.state.dash_pattern == ((3.0, 2.0), 0.0)

    @staticmethod
    def test_gs_sets_flatness() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/FL": 0.5},
            },
        }
        interp = _make_interpreter(resources)
        interp.interpret([(["/GS1"], "gs")])
        assert interp.state.flatness == 0.5

    @staticmethod
    def test_gs_sets_rendering_intent() -> None:
        resources = {
            "/ExtGState": {
                "/GS1": {"/RI": "/AbsoluteColorimetric"},
            },
        }
        interp = _make_interpreter(resources)
        interp.interpret([(["/GS1"], "gs")])
        assert interp.state.rendering_intent == "AbsoluteColorimetric"


class TestTextRenderingIntent:
    """Test that text events carry rendering intent."""

    @staticmethod
    def test_text_event_default_rendering_intent() -> None:
        interp = _make_interpreter()
        instructions = [
            ([], "BT"),
            (["/F1", 12], "Tf"),
            (["Hello"], "Tj"),
            ([], "ET"),
        ]
        events = interp.interpret(instructions)
        text_events = [e for e in events if isinstance(e, TextRenderedEvent)]
        assert text_events[0].rendering_intent == "RelativeColorimetric"

    @staticmethod
    def test_text_event_custom_rendering_intent() -> None:
        interp = _make_interpreter()
        instructions = [
            (["/Perceptual"], "ri"),
            ([], "BT"),
            (["/F1", 12], "Tf"),
            (["Hello"], "Tj"),
            ([], "ET"),
        ]
        events = interp.interpret(instructions)
        text_events = [e for e in events if isinstance(e, TextRenderedEvent)]
        assert text_events[0].rendering_intent == "Perceptual"
