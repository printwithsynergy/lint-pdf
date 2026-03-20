"""BaseAIAnalyzer — abstract base class for AI-powered analyzers.

AI analyzers follow the same detection-only principle as core engine analyzers
but produce findings with source="ai" and include a category tag.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.api.models import TenantAIConfig
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument


class BaseAIAnalyzer(ABC):
    """Abstract base class for AI-powered preflight analyzers.

    Subclasses implement ``analyze()`` to detect issues using AI/ML techniques.
    All findings are tagged with source="ai" and the analyzer's category.
    """

    # Subclasses must define these
    category: str = ""
    feature_slug: str = ""
    tier: str = "cpu"  # "cpu" or "gpu"
    credits_per_run: int = 1

    @abstractmethod
    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        """Analyze a document and return AI findings.

        Args:
            document: Enriched semantic document.
            events: Content stream events from the interpreter.
            pdf_bytes: Raw PDF file bytes (needed for image rendering).
            ai_config: Tenant's AI configuration (thresholds, brand palette, etc).

        Returns:
            List of findings (may be empty).
        """

    def _make_finding(
        self,
        inspection_id: str,
        severity: Severity,
        message: str,
        page_num: int = 0,
        details: dict[str, Any] | None = None,
        iso_clause: str = "",
        object_id: str | None = None,
        object_type: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> Finding:
        """Create a Finding pre-tagged with source='ai' and this analyzer's category."""
        return Finding(
            inspection_id=inspection_id,
            severity=severity,
            message=message,
            page_num=page_num,
            details=details or {},
            iso_clause=iso_clause,
            object_id=object_id,
            object_type=object_type,
            bbox=bbox,
            source="ai",
            category=self.category,
        )
