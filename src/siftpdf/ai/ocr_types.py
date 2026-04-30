"""Data shapes returned by the Claude OCR pass (WS-C).

Kept separate from ``ocr_claude.py`` so the API schema module can
import these dataclasses without pulling the Anthropic SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OCRTextBlock:
    """One recovered text region on a page.

    ``bbox`` is ``[x0, y0, x1, y1]`` in PDF user-space points
    (bottom-left origin, matching ``JobFinding.bbox_*`` columns).
    ``confidence`` is 0.0-1.0; pass-through from Claude's verdict.
    """

    text: str
    bbox: list[float]
    confidence: float


@dataclass(frozen=True)
class OCRPage:
    """Recovered text layer for a single page."""

    page_num: int
    blocks: list[OCRTextBlock] = field(default_factory=list)
