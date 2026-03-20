"""GraphicsState and TransformationMatrix — PDF graphics state tracking.

The graphics state tracks all rendering parameters as the content stream
interpreter processes operators. The q/Q operators push/pop the state stack.

TransformationMatrix implements the 3x3 affine transformation matrix used
by the Current Transformation Matrix (CTM). It tracks scaling, rotation,
and translation applied to page content.

Reference: ISO 32000-2 §8.3 (Coordinate Systems), §8.4 (Graphics State)
Reference: grounded-research/implementation-plan.md Module 3
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field


@dataclass
class TransformationMatrix:
    """3x3 affine transformation matrix for PDF coordinate systems.

    Stored as 6 values [a, b, c, d, e, f] representing:
        [a  b  0]
        [c  d  0]
        [e  f  1]

    Identity matrix: a=1, b=0, c=0, d=1, e=0, f=0.

    Point transformation: [x' y' 1] = [x y 1] x matrix
        x' = a*x + c*y + e
        y' = b*x + d*y + f
    """

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0

    def multiply(self, other: TransformationMatrix) -> TransformationMatrix:
        """Matrix multiplication: self x other.

        Per ISO 32000-2 section 8.3.4:
        [a  b  0]   [a' b' 0]
        [c  d  0] x [c' d' 0]
        [e  f  1]   [e' f' 1]
        """
        return TransformationMatrix(
            a=self.a * other.a + self.b * other.c,
            b=self.a * other.b + self.b * other.d,
            c=self.c * other.a + self.d * other.c,
            d=self.c * other.b + self.d * other.d,
            e=self.e * other.a + self.f * other.c + other.e,
            f=self.e * other.b + self.f * other.d + other.f,
        )

    def extract_scale(self) -> tuple[float, float]:
        """Extract horizontal and vertical scale factors.

        Returns:
            (sx, sy) where sx = sqrt(a² + c²), sy = sqrt(b² + d²).
            These represent the scaling effect of the matrix on each axis.
        """
        sx = math.sqrt(self.a**2 + self.c**2)
        sy = math.sqrt(self.b**2 + self.d**2)
        return (sx, sy)

    def transform_point(self, x: float, y: float) -> tuple[float, float]:
        """Transform a point through this matrix.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Transformed (x', y').
        """
        x_prime = self.a * x + self.c * y + self.e
        y_prime = self.b * x + self.d * y + self.f
        return (x_prime, y_prime)

    def is_identity(self) -> bool:
        """Check if this is the identity matrix."""
        return (
            self.a == 1.0
            and self.b == 0.0
            and self.c == 0.0
            and self.d == 1.0
            and self.e == 0.0
            and self.f == 0.0
        )

    @classmethod
    def identity(cls) -> TransformationMatrix:
        """Create an identity matrix."""
        return cls()

    @classmethod
    def translation(cls, tx: float, ty: float) -> TransformationMatrix:
        """Create a translation matrix."""
        return cls(a=1.0, b=0.0, c=0.0, d=1.0, e=tx, f=ty)

    @classmethod
    def scaling(cls, sx: float, sy: float) -> TransformationMatrix:
        """Create a scaling matrix."""
        return cls(a=sx, b=0.0, c=0.0, d=sy, e=0.0, f=0.0)

    @classmethod
    def rotation(cls, angle_degrees: float) -> TransformationMatrix:
        """Create a rotation matrix (counter-clockwise).

        Args:
            angle_degrees: Rotation angle in degrees.
        """
        rad = math.radians(angle_degrees)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        return cls(a=cos_a, b=sin_a, c=-sin_a, d=cos_a, e=0.0, f=0.0)


def _identity_matrix() -> TransformationMatrix:
    """Factory for default CTM value."""
    return TransformationMatrix()


@dataclass
class GraphicsState:
    """Complete PDF graphics state (one stack frame).

    Tracks all rendering parameters that affect detection:
    - CTM: for DPI calculation and coordinate mapping
    - Color: for color space and TAC analysis
    - Opacity/blend mode: for transparency analysis
    - Overprint: for overprint analysis
    - Font: for font detection
    - Text matrix: for text position tracking
    - Clipping path: for visibility analysis

    Reference: ISO 32000-2 §8.4, Table 51
    """

    # Current Transformation Matrix
    ctm: TransformationMatrix = field(default_factory=_identity_matrix)

    # Color state
    stroking_color_space: str = "DeviceGray"
    stroking_color: list[float] = field(default_factory=lambda: [0.0])
    non_stroking_color_space: str = "DeviceGray"
    non_stroking_color: list[float] = field(default_factory=lambda: [0.0])

    # Opacity and blending (from ExtGState)
    stroking_alpha: float = 1.0  # CA
    non_stroking_alpha: float = 1.0  # ca
    blend_mode: str = "Normal"  # BM

    # Overprint (from ExtGState)
    overprint_stroking: bool = False  # OP
    overprint_non_stroking: bool = False  # op
    overprint_mode: int = 0  # OPM

    # Font
    font_name: str | None = None
    font_size: float = 0.0

    # Text state
    text_matrix: TransformationMatrix = field(default_factory=_identity_matrix)
    text_line_matrix: TransformationMatrix = field(default_factory=_identity_matrix)
    char_spacing: float = 0.0  # Tc
    word_spacing: float = 0.0  # Tw
    text_leading: float = 0.0  # TL
    text_rise: float = 0.0  # Ts
    text_rendering_mode: int = 0  # Tr
    horizontal_scaling: float = 100.0  # Tz (percentage)

    # Line width (for thin line detection)
    line_width: float = 1.0  # w

    # Line style (for hairline and print quality detection)
    line_cap: int = 0  # J: 0=butt, 1=round, 2=projecting square
    line_join: int = 0  # j: 0=miter, 1=round, 2=bevel
    miter_limit: float = 10.0  # M: default per spec
    dash_pattern: tuple[tuple[float, ...], float] = ((), 0.0)  # d: ([array], phase)
    flatness: float = 0.0  # i: curve flatness tolerance
    rendering_intent: str = "RelativeColorimetric"  # ri

    # Prepress state (from ExtGState)
    has_halftone: bool = False  # /HT
    has_transfer_function: bool = False  # /TR, /TR2
    has_bg_ucr: bool = False  # /BG, /BG2, /UCR, /UCR2

    def copy(self) -> GraphicsState:
        """Deep copy for q (save) operator.

        Mutable fields (lists, matrices) are deep-copied to prevent
        shared state between stack frames.
        """
        new = GraphicsState(
            ctm=TransformationMatrix(
                self.ctm.a,
                self.ctm.b,
                self.ctm.c,
                self.ctm.d,
                self.ctm.e,
                self.ctm.f,
            ),
            stroking_color_space=self.stroking_color_space,
            stroking_color=copy.copy(self.stroking_color),
            non_stroking_color_space=self.non_stroking_color_space,
            non_stroking_color=copy.copy(self.non_stroking_color),
            stroking_alpha=self.stroking_alpha,
            non_stroking_alpha=self.non_stroking_alpha,
            blend_mode=self.blend_mode,
            overprint_stroking=self.overprint_stroking,
            overprint_non_stroking=self.overprint_non_stroking,
            overprint_mode=self.overprint_mode,
            font_name=self.font_name,
            font_size=self.font_size,
            text_matrix=TransformationMatrix(
                self.text_matrix.a,
                self.text_matrix.b,
                self.text_matrix.c,
                self.text_matrix.d,
                self.text_matrix.e,
                self.text_matrix.f,
            ),
            text_line_matrix=TransformationMatrix(
                self.text_line_matrix.a,
                self.text_line_matrix.b,
                self.text_line_matrix.c,
                self.text_line_matrix.d,
                self.text_line_matrix.e,
                self.text_line_matrix.f,
            ),
            char_spacing=self.char_spacing,
            word_spacing=self.word_spacing,
            text_leading=self.text_leading,
            text_rise=self.text_rise,
            text_rendering_mode=self.text_rendering_mode,
            horizontal_scaling=self.horizontal_scaling,
            line_width=self.line_width,
            line_cap=self.line_cap,
            line_join=self.line_join,
            miter_limit=self.miter_limit,
            dash_pattern=self.dash_pattern,
            flatness=self.flatness,
            rendering_intent=self.rendering_intent,
            has_halftone=self.has_halftone,
            has_transfer_function=self.has_transfer_function,
            has_bg_ucr=self.has_bg_ucr,
        )
        return new
