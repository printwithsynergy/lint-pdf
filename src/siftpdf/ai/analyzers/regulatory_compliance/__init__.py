"""Regulatory compliance AI analyzers."""

from siftpdf.ai.analyzers.regulatory_compliance.alcohol import AlcoholLabelingAnalyzer
from siftpdf.ai.analyzers.regulatory_compliance.cannabis import CannabisLabelingAnalyzer
from siftpdf.ai.analyzers.regulatory_compliance.cosmetics import CosmeticsLabelingAnalyzer
from siftpdf.ai.analyzers.regulatory_compliance.eu_fir_1169 import EuFir1169Analyzer
from siftpdf.ai.analyzers.regulatory_compliance.fda_nutrition import FdaNutritionAnalyzer
from siftpdf.ai.analyzers.regulatory_compliance.ghs_clp import GhsClpAnalyzer
from siftpdf.ai.analyzers.regulatory_compliance.pharma_font import PharmaFontAnalyzer
from siftpdf.ai.analyzers.regulatory_compliance.tobacco import TobaccoWarningAnalyzer

__all__ = [
    "AlcoholLabelingAnalyzer",
    "CannabisLabelingAnalyzer",
    "CosmeticsLabelingAnalyzer",
    "EuFir1169Analyzer",
    "FdaNutritionAnalyzer",
    "GhsClpAnalyzer",
    "PharmaFontAnalyzer",
    "TobaccoWarningAnalyzer",
]
