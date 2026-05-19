"""Semantic events emitted by the ContentStreamInterpreter.

Events represent meaningful preflight-relevant occurrences found during
content stream interpretation. Analyzers consume these events to produce
findings — they never parse content streams directly.

All events are frozen dataclasses (immutable after creation).

Reference: lintpdf-research/implementation-plan.md Module 3
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lintpdf.semantic.graphics_state import TransformationMatrix


@dataclass(frozen=True)
class ContentStreamEvent:
    """Base class for all semantic events.

    Attributes:
        operator: The PDF operator that triggered this event.
        page_num: 1-indexed page number.
        operator_index: Sequential index of this operator in the stream.
    """

    operator: str
    page_num: int
    operator_index: int


@dataclass(frozen=True)
class ImagePlacedEvent(ContentStreamEvent):
    """Emitted when an image XObject is invoked (Do operator).

    Analyzers use CTM to calculate effective DPI.

    Attributes:
        image_name: XObject resource name (e.g., "Im1").
        ctm: Current Transformation Matrix at placement.
        pixel_width: Image width in pixels.
        pixel_height: Image height in pixels.
        bits_per_component: Bits per color component.
        color_space: Color space name.
        filters: Compression filters applied.
        has_soft_mask: Whether a soft mask is present.
        is_inline: Whether this is an inline image.
    """

    image_name: str
    ctm: TransformationMatrix
    pixel_width: int
    pixel_height: int
    bits_per_component: int = 8
    color_space: str = ""
    filters: tuple[str, ...] = ()
    has_soft_mask: bool = False
    is_inline: bool = False
    has_opi: bool = False
    has_alternate: bool = False


@dataclass(frozen=True)
class TextRenderedEvent(ContentStreamEvent):
    """Emitted when text is rendered (Tj, TJ, ', " operators).

    Attributes:
        font_name: Current font resource name.
        font_size: Font size in text space units.
        ctm: Current Transformation Matrix.
        text_matrix: Current text matrix (Tm).
        color_space: Current non-stroking color space.
        color_values: Current non-stroking color values.
        opacity: Current non-stroking alpha (ca).
        rendering_mode: Text rendering mode (0-7).
    """

    font_name: str
    font_size: float
    ctm: TransformationMatrix
    text_matrix: TransformationMatrix
    color_space: str = "DeviceGray"
    color_values: tuple[float, ...] = (0.0,)
    opacity: float = 1.0
    rendering_mode: int = 0
    rendering_intent: str = "RelativeColorimetric"
    bbox: tuple[float, float, float, float] | None = None  # Approximate (x0, y0, x1, y1)
    raw_text: str = ""  # Decoded ASCII/latin-1 text; empty for CID/hex-encoded glyphs


@dataclass(frozen=True)
class ColorChangedEvent(ContentStreamEvent):
    """Emitted when color is set (sc, scn, SC, SCN, rg, RG, k, K, g, G).

    Attributes:
        stroking: True for stroking color, False for non-stroking.
        color_space: Color space name.
        color_values: Color component values.
    """

    stroking: bool
    color_space: str
    color_values: tuple[float, ...]


@dataclass(frozen=True)
class OpacityChangedEvent(ContentStreamEvent):
    """Emitted when opacity changes via ExtGState (gs operator).

    Attributes:
        stroking_alpha: Stroking opacity (CA), or None if unchanged.
        non_stroking_alpha: Non-stroking opacity (ca), or None if unchanged.
        blend_mode: Blend mode, or None if unchanged.
    """

    stroking_alpha: float | None = None
    non_stroking_alpha: float | None = None
    blend_mode: str | None = None


@dataclass(frozen=True)
class OverprintChangedEvent(ContentStreamEvent):
    """Emitted when overprint settings change via ExtGState (gs operator).

    Attributes:
        overprint_stroking: OP flag, or None if unchanged.
        overprint_non_stroking: op flag, or None if unchanged.
        overprint_mode: OPM value, or None if unchanged.
    """

    overprint_stroking: bool | None = None
    overprint_non_stroking: bool | None = None
    overprint_mode: int | None = None


@dataclass(frozen=True)
class FormXObjectEnteredEvent(ContentStreamEvent):
    """Emitted when a Form XObject is invoked (Do operator).

    Attributes:
        form_name: XObject resource name.
        form_matrix: The Form XObject's own /Matrix entry.
        ctm: Effective CTM (page CTM x form Matrix).
        nesting_depth: Current Form XObject nesting depth.
    """

    form_name: str
    form_matrix: TransformationMatrix
    ctm: TransformationMatrix
    nesting_depth: int


@dataclass(frozen=True)
class PathPaintingEvent(ContentStreamEvent):
    """Emitted for path painting (S, s, f, F, f*, B, B*, b, b*, n).

    Attributes:
        fill: Whether the path is filled.
        stroke: Whether the path is stroked.
        even_odd: Whether even-odd fill rule is used (f*, B*).
        fill_color_space: Fill color space (if filling).
        fill_color_values: Fill color values (if filling).
        stroke_color_space: Stroke color space (if stroking).
        stroke_color_values: Stroke color values (if stroking).
        line_width: Current line width (for thin line detection).
    """

    fill: bool
    stroke: bool
    even_odd: bool = False
    fill_color_space: str = ""
    fill_color_values: tuple[float, ...] = ()
    stroke_color_space: str = ""
    stroke_color_values: tuple[float, ...] = ()
    line_width: float = 1.0
    line_cap: int = 0  # 0=butt, 1=round, 2=projecting square
    line_join: int = 0  # 0=miter, 1=round, 2=bevel
    dash_pattern: tuple[tuple[float, ...], float] = ((), 0.0)  # ([array], phase)
    point_count: int = 0  # Number of path construction points
    bbox: tuple[float, float, float, float] | None = None  # Approximate (x0, y0, x1, y1)


@dataclass(frozen=True)
class LineStyleChangedEvent(ContentStreamEvent):
    """Emitted when line style parameters change (J, j, d, M, ri operators).

    Attributes:
        line_cap: Line cap style, or None if unchanged.
        line_join: Line join style, or None if unchanged.
        dash_pattern: Dash pattern, or None if unchanged.
        miter_limit: Miter limit, or None if unchanged.
        rendering_intent: Rendering intent, or None if unchanged.
    """

    line_cap: int | None = None
    line_join: int | None = None
    dash_pattern: tuple[tuple[float, ...], float] | None = None
    miter_limit: float | None = None
    rendering_intent: str | None = None


@dataclass(frozen=True)
class PrepressStateChangedEvent(ContentStreamEvent):
    """Emitted when prepress-relevant ExtGState keys are encountered.

    Detects halftone (/HT), transfer functions (/TR, /TR2),
    and BG/UCR functions (/BG, /BG2, /UCR, /UCR2).

    Attributes:
        has_halftone: Whether a custom halftone dictionary was set.
        has_transfer_function: Whether a transfer function was set.
        has_bg_ucr: Whether a custom BG/UCR function was set.
    """

    has_halftone: bool = False
    has_transfer_function: bool = False
    has_bg_ucr: bool = False


@dataclass(frozen=True)
class ClippingPathSetEvent(ContentStreamEvent):
    """Emitted when clipping path is modified (W, W*).

    Attributes:
        even_odd: Whether even-odd rule is used (W*).
    """

    even_odd: bool = False
