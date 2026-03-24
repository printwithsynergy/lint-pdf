"""LintPDF analyzers — preflight detection modules.

Each analyzer focuses on a specific domain (images, fonts, color, etc.)
and consumes SemanticDocument data plus content stream events to produce
Findings.
"""

from lintpdf.analyzers.accessibility import AccessibilityAnalyzer
from lintpdf.analyzers.advanced_color_analyzer import AdvancedColorAnalyzer
from lintpdf.analyzers.annotation import AnnotationAnalyzer
from lintpdf.analyzers.barcode import BarcodeAnalyzer
from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.color import ColorAnalyzer
from lintpdf.analyzers.document import DocumentAnalyzer
from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.analyzers.font import FontAnalyzer
from lintpdf.analyzers.hairline import HairlineAnalyzer
from lintpdf.analyzers.icc_profile_analyzer import IccProfileAnalyzer
from lintpdf.analyzers.image import ImageAnalysisResult, ImageAnalyzer
from lintpdf.analyzers.ink_coverage_analyzer import InkCoverageAnalyzer
from lintpdf.analyzers.metadata import MetadataAnalyzer
from lintpdf.analyzers.overprint import OverprintAnalyzer
from lintpdf.analyzers.packaging import PackagingAnalyzer
from lintpdf.analyzers.page_geometry import PageGeometryAnalyzer
from lintpdf.analyzers.prepress import PrepressAnalyzer
from lintpdf.analyzers.processing import ProcessingStepAnalyzer
from lintpdf.analyzers.spot_color_analyzer import SpotColorAnalyzer
from lintpdf.analyzers.structure import StructureAnalyzer
from lintpdf.analyzers.transparency import TransparencyAnalyzer

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
