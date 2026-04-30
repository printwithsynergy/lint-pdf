"""Tests for GraphicsState and TransformationMatrix."""

from __future__ import annotations

import math

from siftpdf.semantic.graphics_state import GraphicsState, TransformationMatrix

# --- TransformationMatrix Tests ---


class TestTransformationMatrix:
    """Test matrix operations per ISO 32000-2 §8.3.4."""

    @staticmethod
    def test_identity() -> None:
        m = TransformationMatrix()
        assert m.is_identity() is True
        assert m.a == 1.0
        assert m.d == 1.0

    @staticmethod
    def test_identity_factory() -> None:
        m = TransformationMatrix.identity()
        assert m.is_identity() is True

    @staticmethod
    def test_non_identity() -> None:
        m = TransformationMatrix(a=2.0, d=2.0)
        assert m.is_identity() is False

    @staticmethod
    def test_multiply_identity() -> None:
        """Identity x any = any."""
        m = TransformationMatrix(a=2, b=0, c=0, d=3, e=100, f=200)
        result = TransformationMatrix.identity().multiply(m)
        assert result.a == 2.0
        assert result.d == 3.0
        assert result.e == 100.0
        assert result.f == 200.0

    @staticmethod
    def test_multiply_any_by_identity() -> None:
        """Any x identity = any."""
        m = TransformationMatrix(a=2, b=0, c=0, d=3, e=100, f=200)
        result = m.multiply(TransformationMatrix.identity())
        assert result.a == 2.0
        assert result.d == 3.0
        assert result.e == 100.0
        assert result.f == 200.0

    @staticmethod
    def test_multiply_scale() -> None:
        """Scale(2,3) x Scale(4,5) = Scale(8,15)."""
        s1 = TransformationMatrix.scaling(2, 3)
        s2 = TransformationMatrix.scaling(4, 5)
        result = s1.multiply(s2)
        assert result.a == 8.0
        assert result.d == 15.0
        assert result.e == 0.0
        assert result.f == 0.0

    @staticmethod
    def test_multiply_translation() -> None:
        """Translation(10,20) x Translation(30,40) = Translation(40,60)."""
        t1 = TransformationMatrix.translation(10, 20)
        t2 = TransformationMatrix.translation(30, 40)
        result = t1.multiply(t2)
        assert result.e == 40.0
        assert result.f == 60.0
        assert result.a == 1.0
        assert result.d == 1.0

    @staticmethod
    def test_multiply_scale_then_translate() -> None:
        """Scale(2,2) x Translate(10,20) should translate by 10,20 in scaled space."""
        scale = TransformationMatrix.scaling(2, 2)
        translate = TransformationMatrix.translation(10, 20)
        result = scale.multiply(translate)
        # e = 2*0 + 0*0 + 10 = 10, f = 0*0 + 2*0 + 20 = 20
        # Wait: in PDF, cm concatenates by multiplying new_matrix on LEFT of CTM
        # Result: a=2, d=2, e=10, f=20
        assert result.a == 2.0
        assert result.d == 2.0
        assert result.e == 10.0
        assert result.f == 20.0

    @staticmethod
    def test_extract_scale_identity() -> None:
        m = TransformationMatrix()
        sx, sy = m.extract_scale()
        assert sx == 1.0
        assert sy == 1.0

    @staticmethod
    def test_extract_scale_known() -> None:
        m = TransformationMatrix(a=3, b=0, c=0, d=4, e=0, f=0)
        sx, sy = m.extract_scale()
        assert sx == 3.0
        assert sy == 4.0

    @staticmethod
    def test_extract_scale_rotation() -> None:
        """90-degree rotation should have scale factors ≈ 1.0."""
        m = TransformationMatrix.rotation(90)
        sx, sy = m.extract_scale()
        assert abs(sx - 1.0) < 1e-10
        assert abs(sy - 1.0) < 1e-10

    @staticmethod
    def test_extract_scale_scaled_rotation() -> None:
        """Rotation x Scale(2,3) should extract sx~2, sy~3."""
        rot = TransformationMatrix.rotation(45)
        scale = TransformationMatrix.scaling(2, 3)
        combined = rot.multiply(scale)
        sx, sy = combined.extract_scale()
        assert abs(sx - 2.0) < 1e-10
        assert abs(sy - 3.0) < 1e-10

    @staticmethod
    def test_transform_point_identity() -> None:
        m = TransformationMatrix()
        x, y = m.transform_point(100, 200)
        assert x == 100.0
        assert y == 200.0

    @staticmethod
    def test_transform_point_translation() -> None:
        m = TransformationMatrix.translation(50, 100)
        x, y = m.transform_point(10, 20)
        assert x == 60.0
        assert y == 120.0

    @staticmethod
    def test_transform_point_scaling() -> None:
        m = TransformationMatrix.scaling(2, 3)
        x, y = m.transform_point(10, 20)
        assert x == 20.0
        assert y == 60.0

    @staticmethod
    def test_transform_point_rotation_90() -> None:
        """Rotating (1, 0) by 90° should give approximately (0, 1)."""
        m = TransformationMatrix.rotation(90)
        x, y = m.transform_point(1, 0)
        assert abs(x - 0.0) < 1e-10
        assert abs(y - 1.0) < 1e-10

    @staticmethod
    def test_rotation_factory() -> None:
        m = TransformationMatrix.rotation(0)
        assert m.is_identity()

    @staticmethod
    def test_rotation_180() -> None:
        m = TransformationMatrix.rotation(180)
        assert abs(m.a - (-1)) < 1e-10
        assert abs(m.d - (-1)) < 1e-10

    @staticmethod
    def test_known_image_ctm() -> None:
        """Typical image placement: cm 200 0 0 300 100 400.
        Image is 200pt wide, 300pt tall, placed at (100, 400)."""
        m = TransformationMatrix(a=200, b=0, c=0, d=300, e=100, f=400)
        sx, sy = m.extract_scale()
        assert sx == 200.0
        assert sy == 300.0

    @staticmethod
    def test_skew_matrix_scale() -> None:
        """Skewed matrix: a=200, b=50, c=30, d=300."""
        m = TransformationMatrix(a=200, b=50, c=30, d=300, e=0, f=0)
        sx, sy = m.extract_scale()
        expected_sx = math.sqrt(200**2 + 30**2)
        expected_sy = math.sqrt(50**2 + 300**2)
        assert abs(sx - expected_sx) < 1e-10
        assert abs(sy - expected_sy) < 1e-10


# --- GraphicsState Tests ---


class TestGraphicsState:
    """Test GraphicsState creation and copy."""

    @staticmethod
    def test_default_state() -> None:
        gs = GraphicsState()
        assert gs.ctm.is_identity()
        assert gs.stroking_color_space == "DeviceGray"
        assert gs.non_stroking_color == [0.0]
        assert gs.stroking_alpha == 1.0
        assert gs.non_stroking_alpha == 1.0
        assert gs.blend_mode == "Normal"
        assert gs.overprint_stroking is False
        assert gs.overprint_mode == 0
        assert gs.font_name is None
        assert gs.font_size == 0.0
        assert gs.line_width == 1.0

    @staticmethod
    def test_copy_is_independent() -> None:
        """Copy should produce a fully independent state."""
        gs = GraphicsState()
        gs.ctm = TransformationMatrix(a=2, b=0, c=0, d=3, e=10, f=20)
        gs.stroking_color = [1.0, 0.0, 0.0]
        gs.font_name = "F1"

        copy = gs.copy()

        # Verify copied values
        assert copy.ctm.a == 2.0
        assert copy.stroking_color == [1.0, 0.0, 0.0]
        assert copy.font_name == "F1"

        # Modify original, verify copy is unaffected
        gs.ctm.a = 99.0
        gs.stroking_color[0] = 0.5
        gs.font_name = "F2"

        assert copy.ctm.a == 2.0
        assert copy.stroking_color == [1.0, 0.0, 0.0]
        assert copy.font_name == "F1"

    @staticmethod
    def test_copy_preserves_all_fields() -> None:
        gs = GraphicsState(
            stroking_color_space="DeviceCMYK",
            stroking_color=[0.0, 1.0, 1.0, 0.0],
            non_stroking_color_space="DeviceRGB",
            non_stroking_color=[0.5, 0.5, 0.5],
            stroking_alpha=0.8,
            non_stroking_alpha=0.6,
            blend_mode="Multiply",
            overprint_stroking=True,
            overprint_non_stroking=True,
            overprint_mode=1,
            font_name="F2",
            font_size=14.0,
            char_spacing=1.5,
            word_spacing=2.0,
            text_leading=12.0,
            text_rise=3.0,
            text_rendering_mode=2,
            horizontal_scaling=110.0,
            line_width=0.5,
        )
        copy = gs.copy()

        assert copy.stroking_color_space == "DeviceCMYK"
        assert copy.stroking_color == [0.0, 1.0, 1.0, 0.0]
        assert copy.non_stroking_color_space == "DeviceRGB"
        assert copy.stroking_alpha == 0.8
        assert copy.non_stroking_alpha == 0.6
        assert copy.blend_mode == "Multiply"
        assert copy.overprint_stroking is True
        assert copy.overprint_non_stroking is True
        assert copy.overprint_mode == 1
        assert copy.font_name == "F2"
        assert copy.font_size == 14.0
        assert copy.char_spacing == 1.5
        assert copy.word_spacing == 2.0
        assert copy.text_leading == 12.0
        assert copy.text_rise == 3.0
        assert copy.text_rendering_mode == 2
        assert copy.horizontal_scaling == 110.0
        assert copy.line_width == 0.5

    @staticmethod
    def test_copy_text_matrix_independent() -> None:
        gs = GraphicsState()
        gs.text_matrix = TransformationMatrix(a=2, b=0, c=0, d=2, e=50, f=100)

        copy = gs.copy()
        gs.text_matrix.a = 99.0

        assert copy.text_matrix.a == 2.0

    # --- Line style fields ---

    @staticmethod
    def test_default_line_style() -> None:
        gs = GraphicsState()
        assert gs.line_cap == 0
        assert gs.line_join == 0
        assert gs.miter_limit == 10.0
        assert gs.dash_pattern == ((), 0.0)
        assert gs.flatness == 0.0
        assert gs.rendering_intent == "RelativeColorimetric"

    @staticmethod
    def test_copy_preserves_line_style() -> None:
        gs = GraphicsState(
            line_cap=1,
            line_join=2,
            miter_limit=5.0,
            dash_pattern=((3.0, 2.0), 1.0),
            flatness=0.5,
            rendering_intent="AbsoluteColorimetric",
        )
        copy = gs.copy()

        assert copy.line_cap == 1
        assert copy.line_join == 2
        assert copy.miter_limit == 5.0
        assert copy.dash_pattern == ((3.0, 2.0), 1.0)
        assert copy.flatness == 0.5
        assert copy.rendering_intent == "AbsoluteColorimetric"

    @staticmethod
    def test_copy_line_style_independent() -> None:
        gs = GraphicsState()
        gs.line_cap = 2
        gs.rendering_intent = "Perceptual"

        copy = gs.copy()
        gs.line_cap = 0
        gs.rendering_intent = "Saturation"

        assert copy.line_cap == 2
        assert copy.rendering_intent == "Perceptual"
