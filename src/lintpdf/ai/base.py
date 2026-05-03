"""BaseAIAnalyzer — base class for AI-powered analyzers.

AI analyzers follow the same detection-only principle as core engine analyzers
but produce findings with source="ai" and include a category tag.

Subclasses override exactly one entry point: ``analyze_v2(ctx)``.

Phase 2 alpha-stream migrated every BaseAIAnalyzer subclass off the
legacy ``analyze(document, events, pdf_bytes, ai_config)`` 4-arg shape
onto ``analyze_v2(ctx: AnalyzerContext)``. Phase 2 beta-stream routed
SaaS coupling through ``ctx.services.*``. Phase 3b drops the legacy
``analyze`` method entirely — ``analyze_v2`` is now the only entry
point and the default raises ``NotImplementedError`` if a subclass
forgets to override it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext


class BaseAIAnalyzer:
    """Base class for AI-powered preflight analyzers.

    Subclasses MUST override ``analyze_v2(ctx)``.
    """

    # Subclasses must define these
    category: str = ""
    feature_slug: str = ""
    tier: str = "cpu"  # "cpu" or "gpu"
    credits_per_run: int = 1

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        """Plugin-protocol entry point. Subclasses MUST override.

        Read tenant AI config from ``ctx.config["ai_config"]`` (a plain
        dict) and reach SaaS-coupled features (cost cap, metering, GPU
        client, renderer, storage, tenants, verapdf_client) through
        ``ctx.services.*``. See ``packages/engine/CLAUDE.md`` and
        ``packages/engine/docs/plugin-api.md`` for the full contract.
        """

        raise NotImplementedError(f"{type(self).__name__} must override `analyze_v2(ctx)`.")

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
    """Wrap a plain ai_config dict in an attribute-access shim.

    Analyzers expect an object with attribute access
    (``config.brand_palette``, ``config.enabled_categories``, etc.);
    Celery serializes the AIConfigService output to a dict over the
    wire so we re-wrap on the worker side. Phase 2 strips this layer
    once analyzers read ``ctx.config["ai_config"]`` directly.
    """

    if d is None:
        return None

    class _AttrDict:
        def __init__(self, data: dict[str, Any]) -> None:
            self._data = data

        def __getattr__(self, item: str) -> Any:
            return self._data.get(item)

    return _AttrDict(d)
