"""Regulatory compliance AI analyzers."""

from lintpdf.ai.analyzers.regulatory_compliance.eu_fir_1169 import EuFir1169Analyzer
from lintpdf.ai.analyzers.regulatory_compliance.fda_nutrition import FdaNutritionAnalyzer
from lintpdf.ai.analyzers.regulatory_compliance.ghs_clp import GhsClpAnalyzer
from lintpdf.ai.analyzers.regulatory_compliance.pharma_font import PharmaFontAnalyzer

__all__ = [
    "EuFir1169Analyzer",
    "FdaNutritionAnalyzer",
    "GhsClpAnalyzer",
    "PharmaFontAnalyzer",
]
