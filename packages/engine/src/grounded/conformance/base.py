"""BaseConformanceValidator — abstract base for conformance validators.

Conformance validators check a document against a specific PDF standard
(e.g., PDF/X-4). They consume the semantic document, content stream events,
and optionally findings from analyzers to produce conformance findings.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grounded.analyzers.finding import Finding
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument


class BaseConformanceValidator(ABC):
    """Abstract base class for PDF conformance validators.

    Subclasses implement ``validate()`` to check a document against a
    specific PDF standard and return a list of conformance findings.
    """

    @abstractmethod
    def validate(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        analyzer_findings: list[Finding] | None = None,
    ) -> list[Finding]:
        """Validate document conformance.

        Args:
            document: Enriched semantic document.
            events: Content stream events from the interpreter.
            analyzer_findings: Optional findings from analyzers (for reuse).

        Returns:
            List of conformance findings.
        """
