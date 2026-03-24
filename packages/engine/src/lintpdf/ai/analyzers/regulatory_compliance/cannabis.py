"""Cannabis labeling compliance analyzer (state-specific requirements)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer

if TYPE_CHECKING:
    from lintpdf.analyzers.finding import Finding
    from lintpdf.api.models import TenantAIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


@register_ai_analyzer
class CannabisLabelingAnalyzer(BaseAIAnalyzer):
    """Validates cannabis product labeling per state-specific regulations.

    Check IDs:
        AI_CANN_001: Missing required cannabis warning symbols or statements.
        AI_CANN_002: THC/CBD content declaration formatting violations.
    """

    category = "regulatory_compliance"
    feature_slug = "cannabis_labeling"
    tier = "gpu"
    credits_per_run = 3

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        """Analyze for cannabis labeling compliance. Requires GPU inference."""
        return []  # Stub — requires inference service
