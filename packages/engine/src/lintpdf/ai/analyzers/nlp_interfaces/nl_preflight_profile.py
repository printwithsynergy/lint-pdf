"""Natural language preflight profile creation — NLP interface stub.

This analyzer registers the ``nl_preflight_profile_creation`` feature in the AI
feature catalogue but does NOT perform inspection logic itself.  The actual
natural-language-to-preflight-profile conversion is handled by the API endpoint
that accepts free-text instructions and translates them into a structured
preflight profile configuration.

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
class NLPreflightProfileAnalyzer(BaseAIAnalyzer):
    """Placeholder for natural language preflight profile creation feature.

    The actual NL-to-preflight-profile logic lives in the API endpoint.
    This class exists solely to register the feature in the AI catalogue.
    """

    category = "nlp_interfaces"
    feature_slug = "nl_preflight_profile_creation"
    tier = "gpu"
    credits_per_run = 0

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        # Phase 2 alpha-stream: signature migration. No inspection logic
        # — feature is implemented at the API layer.
        return []
