"""BaseAnalyzer — abstract base class for all analyzers.

Each analyzer focuses on a specific preflight domain (images, fonts, color, etc.)
and processes a SemanticDocument plus content stream events to produce Findings.

Analyzers are pure detection modules: they never modify the document.

Phase 1 introduces ``analyze_v2(ctx)`` as a default-implemented hook on top
of the legacy ``analyze(document, events)`` signature. Existing subclasses
keep working unchanged; the orchestrator drives them via ``analyze_v2``,
which the default impl forwards to ``analyze``. New analyzers should
override ``analyze_v2`` directly and skip the legacy method entirely.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lintpdf.analyzers.finding import Finding
    from lintpdf.plugin.protocol import AnalyzerContext
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


class BaseAnalyzer(ABC):
    """Abstract base class for preflight analyzers.

    Subclasses implement ``analyze()`` to inspect a document and its
    content stream events, returning a list of Findings.
    """

    @abstractmethod
    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze a document and return findings.

        Args:
            document: Enriched semantic document with resolved properties.
            events: Content stream events from the interpreter.

        Returns:
            List of findings (may be empty if no issues detected).
        """

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        """Plugin-protocol entry point. Default forwards to ``analyze``.

        Override this directly in new analyzers to receive the full
        ``AnalyzerContext`` (services, capabilities, config). Legacy
        analyzers keep overriding ``analyze`` and inherit this default.
        """

        return self.analyze(ctx.document, ctx.events)
