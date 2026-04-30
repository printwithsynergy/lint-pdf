"""BaseAIAnalyzer — base class for AI-powered analyzers.

AI analyzers follow the same detection-only principle as core engine analyzers
but produce findings with source="ai" and include a category tag.

Subclasses override **one** of two entry points:

- ``analyze_v2(ctx)`` — preferred. Pulls the AI config from
  ``ctx.config["ai_config"]`` (plain dict) and reaches SaaS-coupled
  features (cost cap, metering, GPU client) via ``ctx.services.*``.
- ``analyze(document, events, pdf_bytes, ai_config)`` — legacy
  4-arg shape. The default ``analyze_v2`` reconstitutes
  ``ai_config`` and forwards here.

Phase 2 (Q&A 1b-B) relaxed the abstract requirement on ``analyze``:
the class now ships a ``NotImplementedError`` default so AI analyzers
can override only ``analyze_v2`` without satisfying a phantom abstract
method. Subclasses that override neither method instantiate cleanly
but raise NotImplementedError on first invocation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig
    from lintpdf.plugin.protocol import AnalyzerContext
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


class BaseAIAnalyzer:
    """Base class for AI-powered preflight analyzers.

    Subclasses implement **one** of:

    - ``analyze_v2(ctx)`` — preferred plugin-protocol entry point.
    - ``analyze(document, events, pdf_bytes, ai_config)`` — legacy
      4-arg shape (the default ``analyze_v2`` reconstitutes
      ``ai_config`` and forwards here).
    """

    # Subclasses must define these
    category: str = ""
    feature_slug: str = ""
    tier: str = "cpu"  # "cpu" or "gpu"
    credits_per_run: int = 1

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        """Legacy AI-analyzer hook (default raises ``NotImplementedError``).

        Override this OR ``analyze_v2(ctx)``. The default
        ``analyze_v2`` reconstitutes ``ai_config`` from
        ``ctx.config["ai_config"]`` and forwards here, so analyzers
        that don't need ``ctx.services`` can keep using this 4-arg
        shape unchanged.

        Args:
            document: Enriched semantic document.
            events: Content stream events from the interpreter.
            pdf_bytes: Raw PDF file bytes (needed for image rendering).
            ai_config: Tenant's AI configuration (thresholds, brand palette, etc).

        Returns:
            List of findings (may be empty).
        """

        raise NotImplementedError(
            f"{type(self).__name__} must override either `analyze` "
            "(legacy 4-arg signature) or `analyze_v2(ctx)` (preferred)."
        )

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        """Plugin-protocol entry point. Default forwards to ``analyze``.

        Pulls the legacy ``ai_config`` parameter from
        ``ctx.config["ai_config"]``. The host bridge in
        ``lintpdf.plugin.host`` reconstitutes the plain dict back into a
        ``TenantAIConfig`` (or attribute-access fallback) so legacy code
        that does ``ai_config.attribute`` keeps working through Phase 1.

        New AI analyzers should override this method directly and skip
        the legacy ``analyze`` signature entirely.
        """

        ai_config_dict = ctx.config.get("ai_config") if ctx.config else None
        ai_config_obj = _reconstitute_ai_config(ai_config_dict)
        return self.analyze(
            ctx.document,
            ctx.events,
            ctx.pdf_bytes,
            ai_config_obj,
        )

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


def _reconstitute_ai_config(d: dict[str, Any] | None) -> Any:
    """Turn a plain ai_config dict back into a TenantAIConfig (or AttrDict).

    Phase 1 keeps every legacy AI analyzer working by preserving the
    object-with-attribute-access shape they expect. Phase 2 will strip
    this layer once analyzers read ``ctx.config["ai_config"]`` directly.
    """

    if d is None:
        return None
    try:
        from lintpdf.api.models import TenantAIConfig

        return TenantAIConfig(**d)
    except Exception:
        # Pydantic validation failure or import failure (OSS host) — fall
        # back to a thin attribute-access wrapper so legacy analyzers
        # don't crash on a plain dict.
        class _AttrDict:
            def __init__(self, data: dict[str, Any]) -> None:
                self._data = data

            def __getattr__(self, item: str) -> Any:
                return self._data.get(item)

        return _AttrDict(d)
