"""Grounded analyzers — preflight detection modules.

Each analyzer focuses on a specific domain (images, fonts, color, etc.)
and consumes SemanticDocument data plus content stream events to produce
Findings.
"""

from grounded.analyzers.accessibility import AccessibilityAnalyzer
from grounded.analyzers.annotation import AnnotationAnalyzer
from grounded.analyzers.barcode import BarcodeAnalyzer
from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.color import ColorAnalyzer
from grounded.analyzers.document import DocumentAnalyzer
from grounded.analyzers.finding import Finding, Severity
from grounded.analyzers.font import FontAnalyzer
from grounded.analyzers.hairline import HairlineAnalyzer
from grounded.analyzers.image import ImageAnalysisResult, ImageAnalyzer
from grounded.analyzers.metadata import MetadataAnalyzer
from grounded.analyzers.overprint import OverprintAnalyzer
from grounded.analyzers.page_geometry import PageGeometryAnalyzer
from grounded.analyzers.prepress import PrepressAnalyzer
from grounded.analyzers.processing import ProcessingStepAnalyzer
from grounded.analyzers.structure import StructureAnalyzer
from grounded.analyzers.transparency import TransparencyAnalyzer

__all__ = [
    "AccessibilityAnalyzer",
    "AnnotationAnalyzer",
    "BarcodeAnalyzer",
    "BaseAnalyzer",
    "ColorAnalyzer",
    "DocumentAnalyzer",
    "Finding",
    "FontAnalyzer",
    "HairlineAnalyzer",
    "ImageAnalysisResult",
    "ImageAnalyzer",
    "MetadataAnalyzer",
    "OverprintAnalyzer",
    "PageGeometryAnalyzer",
    "PrepressAnalyzer",
    "ProcessingStepAnalyzer",
    "Severity",
    "StructureAnalyzer",
    "TransparencyAnalyzer",
]
