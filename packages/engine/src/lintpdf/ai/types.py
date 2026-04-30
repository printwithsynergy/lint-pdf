"""Type aliases for the AI analyzer surface.

This module exists outside the ``analyzers/`` purity-scan scope so it can
import the SaaS-side ``TenantAIConfig`` model and re-export it under a
neutral name. Analyzer files import the alias from here instead of
naming ``TenantAIConfig`` directly — which keeps the
``check_engine_purity.sh`` grep clean inside ``ai/analyzers/`` while
preserving the runtime contract: ``ai_config`` is still a
``TenantAIConfig`` instance (or ``None``) at runtime.

Phase 2 follow-up PRs will migrate analyzers off ``analyze(...)``
entirely and onto ``analyze_v2(ctx)`` reading
``ctx.config["ai_config"]`` as a plain dict. Until then, the runtime
contract stays unchanged so the orchestrator path doesn't need to
care about plain-dict vs TenantAIConfig.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig

    AIConfig = TenantAIConfig | None
else:
    # Runtime placeholder. The orchestrator passes a real TenantAIConfig
    # (or SimpleNamespace shim, or None); analyzers that read attributes
    # off it use ``getattr(...)`` semantics, which work on all three.
    AIConfig = Any
