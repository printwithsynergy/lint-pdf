"""LintPDF semantic layer — enriched PDF document model.

This package provides:
- SemanticModel classes (PdfBox, PdfFont, PdfColorSpace, PdfImage, SemanticPage, SemanticDocument)
- GraphicsState and TransformationMatrix for content stream interpretation
- Semantic events emitted by the ContentStreamInterpreter
- SemanticModel builder for inheritance resolution and enrichment
"""

from siftpdf.semantic.events import (
    ClippingPathSetEvent,
    ColorChangedEvent,
    ContentStreamEvent,
    FormXObjectEnteredEvent,
    ImagePlacedEvent,
    OpacityChangedEvent,
    OverprintChangedEvent,
    PathPaintingEvent,
    TextRenderedEvent,
)
from siftpdf.semantic.graphics_state import GraphicsState, TransformationMatrix
from siftpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    PdfFont,
    PdfImage,
    SemanticDocument,
    SemanticPage,
)

__all__ = [
    "ClippingPathSetEvent",
    "ColorChangedEvent",
    "ContentStreamEvent",
    "FormXObjectEnteredEvent",
    "GraphicsState",
    "ImagePlacedEvent",
    "OpacityChangedEvent",
    "OverprintChangedEvent",
    "PathPaintingEvent",
    "PdfBox",
    "PdfColorSpace",
    "PdfFont",
    "PdfImage",
    "SemanticDocument",
    "SemanticPage",
    "TextRenderedEvent",
    "TransformationMatrix",
]
