"""LintPDF analyzers — preflight detection modules.

Each analyzer focuses on a specific domain (images, fonts, color, etc.)
and consumes SemanticDocument data plus content stream events to produce
Findings.
"""

from siftpdf.analyzers.accessibility import AccessibilityAnalyzer
from siftpdf.analyzers.advanced_color_analyzer import AdvancedColorAnalyzer
from siftpdf.analyzers.annotation import AnnotationAnalyzer
from siftpdf.analyzers.barcode import BarcodeAnalyzer
from siftpdf.analyzers.base import BaseAnalyzer
from siftpdf.analyzers.color import ColorAnalyzer
from siftpdf.analyzers.document import DocumentAnalyzer
from siftpdf.analyzers.finding import Finding, Severity
from siftpdf.analyzers.font import FontAnalyzer
from siftpdf.analyzers.hairline import HairlineAnalyzer
from siftpdf.analyzers.icc_profile_analyzer import IccProfileAnalyzer
from siftpdf.analyzers.image import ImageAnalysisResult, ImageAnalyzer
from siftpdf.analyzers.ink_coverage_analyzer import InkCoverageAnalyzer
from siftpdf.analyzers.metadata import MetadataAnalyzer
from siftpdf.analyzers.overprint import OverprintAnalyzer
from siftpdf.analyzers.packaging import PackagingAnalyzer
from siftpdf.analyzers.page_geometry import PageGeometryAnalyzer
from siftpdf.analyzers.prepress import PrepressAnalyzer
from siftpdf.analyzers.processing import ProcessingStepAnalyzer
from siftpdf.analyzers.spot_color_analyzer import SpotColorAnalyzer
from siftpdf.analyzers.structure import StructureAnalyzer
from siftpdf.analyzers.transparency import TransparencyAnalyzer

__all__ = [
    "AccessibilityAnalyzer",
    "AdvancedColorAnalyzer",
    "AnnotationAnalyzer",
    "BarcodeAnalyzer",
    "BaseAnalyzer",
    "ColorAnalyzer",
    "DocumentAnalyzer",
    "Finding",
    "FontAnalyzer",
    "HairlineAnalyzer",
    "IccProfileAnalyzer",
    "ImageAnalysisResult",
    "ImageAnalyzer",
    "InkCoverageAnalyzer",
    "MetadataAnalyzer",
    "OverprintAnalyzer",
    "PackagingAnalyzer",
    "PageGeometryAnalyzer",
    "PrepressAnalyzer",
    "ProcessingStepAnalyzer",
    "Severity",
    "SpotColorAnalyzer",
    "StructureAnalyzer",
    "TransparencyAnalyzer",
]
