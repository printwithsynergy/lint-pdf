"""Shared text-metrics helpers.

Every AI compliance rule that decides "is this text visibly too
small on-page?" must compose the text matrix (``Tm``) and current
transformation matrix (``CTM``) with the nominal font size, not
just read the ``Tf`` operand off the ``TextRenderedEvent``. On
artwork with scaled logo text, the Tf value is often ``1.0 pt``
while the composed scale is 70-100x, which is why the 2026-04-23
Opus audit flagged 14 false positives of the form *"x-height
0.17mm at 1.0 pt"* on the Nutrops back-panel wordmark.

Keep the math in one place so every consumer (``AI_EU1169_001``,
``AI_PHARMA_001``, future legibility rules) stays consistent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from siftpdf.semantic.events import TextRenderedEvent
    from siftpdf.semantic.model import PdfFont

# Typographic fallback when the font descriptor doesn't expose an
# explicit ``XHeight`` / ``sxHeight`` value. 0.52 is calibrated
# against the sans-serif-heavy packaging corpus (Helvetica, Arial,
# Inter, Futura) and is slightly tighter than the previous 0.48
# fallback that lived in ``eu_fir_1169.py`` — 0.52 matches the
# median cap-height / x-height ratio observed in the audit fixtures.
_X_HEIGHT_RATIO_FALLBACK = 0.52

# Points-to-millimetre conversion (1 pt = 1/72 inch, 1 inch = 25.4 mm).
_PT_TO_MM = 25.4 / 72.0


def _descriptor_x_height_ratio(font: PdfFont | None) -> float:
    """Return ``XHeight / UnitsPerEm`` from the PDF font descriptor
    when both keys are present; otherwise the calibrated fallback."""
    if font is None:
        return _X_HEIGHT_RATIO_FALLBACK
    fd = getattr(font, "font_descriptor", None)
    if not fd:
        return _X_HEIGHT_RATIO_FALLBACK
    # Readers in the codebase look at these keys in this order.
    # ``StemH`` is really stem thickness, not x-height, but the
    # old implementation accepted it as a fallback — keep the same
    # behaviour so tighter rules don't regress against fonts that
    # only expose StemH.
    raw_x = fd.get("XHeight") or fd.get("sxHeight") or fd.get("StemH")
    raw_units = fd.get("UnitsPerEm")
    try:
        if raw_x is None or raw_units is None:
            return _X_HEIGHT_RATIO_FALLBACK
        x = float(raw_x)
        units = float(raw_units)
    except (TypeError, ValueError):
        return _X_HEIGHT_RATIO_FALLBACK
    if units <= 0 or x <= 0:
        return _X_HEIGHT_RATIO_FALLBACK
    ratio = x / units
    # Anything wildly outside the plausible 0.3–0.8 band is suspect
    # (broken descriptor, wrong units). Fall back rather than trust
    # a weird value that would defeat the whole point of the helper.
    if 0.3 <= ratio <= 0.8:
        return ratio
    return _X_HEIGHT_RATIO_FALLBACK


def effective_font_size_pt(event: TextRenderedEvent) -> float:
    """On-page font size in points, composing ``Tf * Tm * CTM``.

    The PDF rendering pipeline scales text by the composed
    ``text_matrix x ctm`` before drawing, so a Tf value of ``1.0``
    with ``Tm.a = 72`` and ``CTM.a = 1.5`` renders at ``108 pt``.
    Analyzers that look at raw ``event.font_size`` miss this
    composition and flag large logo text as ``1 pt``.

    Uses ``TransformationMatrix.extract_scale()`` so rotated /
    sheared matrices still report a sensible magnitude
    (``sqrt(a*a + c*c)`` for the x-axis).
    """
    if event.font_size is None:
        return 0.0
    nominal = abs(float(event.font_size))
    if nominal <= 0:
        return 0.0
    composed = event.text_matrix.multiply(event.ctm)
    scale_x, _ = composed.extract_scale()
    return nominal * scale_x


def effective_x_height_mm(
    event: TextRenderedEvent,
    font: PdfFont | None = None,
) -> float | None:
    """Rendered x-height in millimetres, or ``None`` when the text
    is invisible (``rendering_mode == 3``) and legibility rules
    should skip it — the rendered pixels carry no ink.

    Callers that still need a geometric size for invisible text
    (e.g. OCR overlays) should fall back to
    :func:`glyph_bbox_height_mm`.
    """
    if event.rendering_mode == 3:
        # Invisible text (rendered for OCR / selection only). No
        # legibility concern — skip.
        return None
    size_pt = effective_font_size_pt(event)
    if size_pt <= 0:
        return 0.0
    ratio = _descriptor_x_height_ratio(font)
    return size_pt * ratio * _PT_TO_MM


def glyph_bbox_height_mm(event: TextRenderedEvent) -> float | None:
    """Fallback for events where ``effective_x_height_mm`` can't
    be trusted — reads the glyph bounding-box height and multiplies
    by the calibrated x-height ratio.

    Returns ``None`` when the event has no bbox (the pipeline
    sometimes omits it for zero-advance glyphs).
    """
    bbox = getattr(event, "bbox", None)
    if not bbox:
        return None
    try:
        _x0, y0, _x1, y1 = bbox
    except (TypeError, ValueError):
        return None
    height_pt = abs(float(y1) - float(y0))
    if height_pt <= 0:
        return None
    return height_pt * _X_HEIGHT_RATIO_FALLBACK * _PT_TO_MM
