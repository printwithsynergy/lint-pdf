"""FDA OTC Drug Facts labeling compliance analyzer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer

if TYPE_CHECKING:
    from lintpdf.ai.types import AIConfig
    from lintpdf.analyzers.finding import Finding
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


@register_ai_analyzer
class FdaOtcAnalyzer(BaseAIAnalyzer):
    """Validates OTC Drug Facts panel per FDA 21 CFR 201.66."""

    category = "regulatory_compliance"
    feature_slug = "fda_otc"
    tier = "gpu"
    credits_per_run = 3

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: AIConfig = None,
    ) -> list[Finding]:
        """Analyze for FDA OTC compliance. Requires GPU inference."""
        return []  # Stub — requires inference service
