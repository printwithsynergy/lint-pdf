"""FDA OTC Drug Facts labeling compliance analyzer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer

if TYPE_CHECKING:
    from lintpdf.analyzers.finding import Finding
    from lintpdf.plugin.protocol import AnalyzerContext


@register_ai_analyzer
class FdaOtcAnalyzer(BaseAIAnalyzer):
    """Validates OTC Drug Facts panel per FDA 21 CFR 201.66."""

    category = "regulatory_compliance"
    feature_slug = "fda_otc"
    tier = "gpu"
    credits_per_run = 3

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        """Analyze for FDA OTC compliance. Requires GPU inference.

        Phase 2 alpha-stream: signature migration. Stub — feature
        requires GPU inference service.
        """
        return []  # Stub — requires inference service
