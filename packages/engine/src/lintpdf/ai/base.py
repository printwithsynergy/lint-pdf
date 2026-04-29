"""BaseAIAnalyzer — abstract base class for AI-powered analyzers.

AI analyzers follow the same detection-only principle as core engine analyzers
but produce findings with source="ai" and include a category tag.

Phase 1 introduces ``analyze_v2(ctx)`` as a default-implemented hook on top
of the legacy ``analyze(document, events, pdf_bytes, ai_config)`` signature.
The default impl pulls ``ai_config`` from ``ctx.config["ai_config"]`` (a
plain dict reconstituted into a TenantAIConfig object via the host bridge)
so existing subclasses keep working unchanged. New AI analyzers should
override ``analyze_v2`` directly and read services / capabilities / per-
plugin config straight from the ``AnalyzerContext``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig
    from lintpdf.plugin.protocol import AnalyzerContext
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


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
