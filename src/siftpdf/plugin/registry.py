"""Plugin registry — entry-point + decorator-driven discovery.

Two discovery paths in Phase 1:

1. **Entry points** (forward-looking): packages declare plugins via
   ``[project.entry-points."siftpdf.plugins"]`` in their pyproject.toml.
   The registry walks ``importlib.metadata.entry_points(group=...)`` and
   loads each one. This is how Phase 3+ third-party plugin packs install.

2. **Decorator fallback** (existing): the legacy
   ``@register_ai_analyzer`` decorator in ``siftpdf.ai.registry`` adds
   classes to its own list. This registry's ``discover_legacy_ai()``
   wraps each one in a ``LegacyAdapter`` so callers see a uniform
   ``Analyzer`` Protocol.

Phase 2 unifies both paths and deletes the legacy registry. Phase 1 keeps
both for parity.

Discovered plugins are returned as a list — the orchestrator decides
selection / ordering. This keeps the registry policy-free.
"""

from __future__ import annotations

import logging
from importlib.metadata import EntryPoint, entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from siftpdf.plugin.protocol import Analyzer

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "siftpdf.plugins"


def discover_entry_points(group: str = ENTRY_POINT_GROUP) -> list[Analyzer]:
    """Load every entry-point-declared plugin in ``group``.

    Each entry point must resolve to either:
    - A class implementing the Analyzer Protocol (instantiated with no args), or
    - A factory callable returning such an instance.

    Failures during load are logged and skipped — one broken third-party
    plugin must not take down the whole engine.
    """

    plugins: list[Analyzer] = []
    eps: list[EntryPoint] = list(entry_points(group=group))
    for ep in eps:
        try:
            obj = ep.load()
            instance = obj() if callable(obj) else obj
            plugins.append(instance)
        except Exception as exc:
            logger.warning("plugin entry-point load failed: %s — %s", ep.name, exc)
    return plugins


def discover_legacy_ai() -> list[Analyzer]:
    """Wrap every decorator-registered AI analyzer in a LegacyAdapter.

    Imported lazily so the plugin module doesn't pull in the SaaS-coupled
    AI registry at import time (the OSS host won't have it).
    """

    try:
        from siftpdf.ai.registry import get_all_ai_analyzers
        from siftpdf.plugin.host import LegacyAIAdapter
    except ImportError as exc:
        logger.debug("legacy AI registry unavailable: %s", exc)
        return []

    plugins: list[Analyzer] = []
    for analyzer_cls in get_all_ai_analyzers():
        try:
            plugins.append(LegacyAIAdapter(analyzer_cls()))
        except Exception as exc:
            logger.warning(
                "legacy AI analyzer adapter failed: %s — %s",
                analyzer_cls.__name__,
                exc,
            )
    return plugins


def discover_all() -> list[Analyzer]:
    """Discover plugins from every available source.

    Phase 1 source order: entry points first, then legacy AI registry.
    Phase 2 will retire the legacy fallback once all analyzers expose a
    PluginManifest.
    """

    return discover_entry_points() + discover_legacy_ai()
