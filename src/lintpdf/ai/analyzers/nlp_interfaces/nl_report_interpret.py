"""Natural language report interpretation — NLP interface stub.

This analyzer registers the ``nl_report_interpretation`` feature in the AI
feature catalogue but does NOT perform inspection logic itself.  The actual
natural-language report explanation is handled by the API endpoint that
accepts preflight reports and generates human-readable summaries.

The analyzer always returns an empty findings list and costs 0 credits.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer

if TYPE_CHECKING:
    from lintpdf.analyzers.finding import Finding
    from lintpdf.plugin.protocol import AnalyzerContext

logger = logging.getLogger(__name__)


@register_ai_analyzer
class NLReportInterpretAnalyzer(BaseAIAnalyzer):
    """Placeholder for natural language report interpretation feature.

    The actual NL report interpretation logic lives in the API endpoint.
    This class exists solely to register the feature in the AI catalogue.
    """

    category = "nlp_interfaces"
    feature_slug = "nl_report_interpretation"
    tier = "gpu"
    credits_per_run = 0

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        # Phase 2 alpha-stream: signature migration. No inspection logic
        # — feature is implemented at the API layer.
        return []
