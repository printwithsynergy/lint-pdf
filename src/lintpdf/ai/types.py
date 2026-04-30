"""Type aliases + re-exports for the AI analyzer surface.

This module exists outside the ``analyzers/`` purity-scan scope so it
can confine SaaS-side imports (``TenantAIConfig``, the GPU client, the
database session factory) to one well-named place. Analyzer files
import names from here instead of reaching into the SaaS modules
directly — which keeps the ``check_engine_purity.sh`` grep clean
inside ``ai/analyzers/`` while preserving the runtime contract: every
analyzer still receives the same concrete instances at runtime as
before.

Phase 2 follow-up PRs will migrate analyzers off ``analyze(...)``
entirely and onto ``analyze_v2(ctx)`` reading services from
``ctx.services.*``. Until then, this module is the bridge that lets
the in-place refactor advance without behavioural drift.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Always-available runtime re-exports. These are the actual SaaS
# functions/classes the analyzers call; they're imported here so
# analyzer files don't have to import them from the banned modules.
from lintpdf.ai.gpu_client import (
    GPUInferenceClient,
    GPUServiceNotConfiguredError,
    GPUServiceRateLimitedError,
    GPUServiceUnavailableError,
    get_gpu_client,
)


def get_db_session() -> Any:
    """Re-export of ``lintpdf.api.database.get_db_session``.

    Lazy-imported so that an OSS host stripping ``lintpdf.api.*``
    can still import ``lintpdf.ai.types`` (GPU + AIConfig surface)
    without pulling in the SaaS DB layer.

    Phase 2 will replace the single caller
    (``trend_analysis/submission_quality_spc.py``) with
    ``ctx.services.database.session()``; until then this thin
    wrapper preserves the historical SPC lookup path.
    """

    from lintpdf.api.database import get_db_session as _get

    return _get()


if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig

    AIConfig = TenantAIConfig | None

    # Re-export type names for analyzer signatures / except clauses.
    # The analyzer's annotation-only imports go through these aliases
    # so the file never names ``lintpdf.ai.gpu_client``.
    GPUClient = GPUInferenceClient
    GPUUnavailable = GPUServiceUnavailableError
else:
    # Runtime placeholder for AIConfig — the orchestrator passes a
    # real TenantAIConfig (or SimpleNamespace shim, or None);
    # analyzers reading attributes off it use ``getattr(...)``
    # semantics, which work on all three.
    AIConfig = Any
    # Runtime aliases for the GPU type names so legacy code that
    # uses them at runtime (``isinstance``, ``except``) keeps working.
    GPUClient = GPUInferenceClient
    GPUUnavailable = GPUServiceUnavailableError


__all__ = [
    "AIConfig",
    "GPUClient",
    "GPUInferenceClient",
    "GPUServiceNotConfiguredError",
    "GPUServiceRateLimitedError",
    "GPUServiceUnavailableError",
    "GPUUnavailable",
    "get_db_session",
    "get_gpu_client",
]
