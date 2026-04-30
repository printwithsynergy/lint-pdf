"""BaseAnalyzer — base class for all analyzers.

Each analyzer focuses on a specific preflight domain (images, fonts, color, etc.)
and processes a SemanticDocument plus content stream events to produce Findings.

Analyzers are pure detection modules: they never modify the document.

Subclasses override **one** of two entry points:

- ``analyze_v2(ctx)`` — preferred. Receives the full ``AnalyzerContext``
  (services, capabilities, config). Required for any analyzer that
  needs SaaS-coupled features (metering, cost cap, GPU client, tenant
  AI config, etc.) — those reach through ``ctx.services.*`` and
  ``ctx.config["ai_config"]`` rather than direct imports.
- ``analyze(document, events)`` — legacy 2-arg shape. The default
  ``analyze_v2`` forwards here, so analyzers that don't need ``ctx``
  can keep overriding the legacy method.

Phase 2 (Q&A 1b-B) relaxed the abstract requirement on ``analyze``:
the class now ships a ``NotImplementedError`` default so new analyzers
can override only ``analyze_v2`` without satisfying a phantom abstract
method. Subclasses that override neither method instantiate cleanly
but raise NotImplementedError on first invocation — discovered at
analyzer-call time, surfaced through the orchestrator's normal error
path with a clear "override one of analyze() or analyze_v2(ctx)"
message.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from siftpdf.analyzers.finding import Finding
    from siftpdf.plugin.protocol import AnalyzerContext
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument


class BaseAnalyzer:
    """Base class for preflight analyzers.

    Subclasses implement **one** of:

    - ``analyze_v2(ctx)`` — preferred plugin-protocol entry point.
    - ``analyze(document, events)`` — legacy 2-arg shape (the
      default ``analyze_v2`` forwards here).
    """

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Legacy analyzer hook (default raises ``NotImplementedError``).

        Override this OR ``analyze_v2(ctx)``. The default
        ``analyze_v2`` forwards here, so analyzers that don't need
        ``ctx.services`` / ``ctx.config`` can keep using this 2-arg
        shape unchanged. Authors that need ``ctx`` should override
        ``analyze_v2`` directly and skip this method.

        Args:
            document: Enriched semantic document with resolved properties.
            events: Content stream events from the interpreter.

        Returns:
            List of findings (may be empty if no issues detected).
        """

        raise NotImplementedError(
            f"{type(self).__name__} must override either `analyze` "
            "(legacy 2-arg signature) or `analyze_v2(ctx)` (preferred)."
        )

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        """Plugin-protocol entry point. Default forwards to ``analyze``.

        Override this directly in new analyzers to receive the full
        ``AnalyzerContext`` (services, capabilities, config). Legacy
        analyzers keep overriding ``analyze`` and inherit this default.
        """

        return self.analyze(ctx.document, ctx.events)
