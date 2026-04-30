"""Plugin manifest — declarative metadata for an analyzer plugin.

A plugin manifest declares:
- Identity: id, version.
- Tier: CPU, GPU, or EXTERNAL_AI (used for scheduling + tier-gating).
- Required capabilities: page rendering, text regions, content stream events.
- Required services: which protocol entries on Services the plugin reads.
- Declared check IDs: every Finding inspection_id this plugin can emit.
- Optional config schema: JSON-schema dict the host uses to validate config.

Manifests are immutable (frozen dataclass) so the registry can compare them
across reloads cheaply. `declared_check_ids` lets the orchestrator know up
front which findings a plugin owns — useful for dedupe and override resolution.

Phase 1 introduces this manifest alongside the existing decorator-driven
`@register_ai_analyzer` registry. Both paths coexist; Phase 2 unifies them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Tier(StrEnum):
    """Plugin tier — drives scheduling and feature gating."""

    CPU = "cpu"
    GPU = "gpu"
    EXTERNAL_AI = "external_ai"


@dataclass(frozen=True)
class PluginManifest:
    """Declarative metadata for an analyzer plugin.

    Attributes:
        id: Stable plugin identifier (e.g., "siftpdf.barcode.qr_validation").
        version: SemVer string. Increment on signature/finding-format changes.
        tier: Scheduling tier — CPU, GPU, or EXTERNAL_AI.
        requires_capabilities: Capability protocol names the plugin reads
            via ``ctx.capabilities`` (e.g., ``("page_images",)``).
        requires_services: Service protocol names the plugin reads via
            ``ctx.services`` (e.g., ``("metering", "cost_cap")``). Missing
            services → plugin self-skips with a warning.
        declared_check_ids: Inspection IDs this plugin can emit. Used for
            override resolution + dedupe in the orchestrator.
        config_schema: Optional JSON-schema dict the host validates against
            ``ctx.config[plugin_id]`` before invoking ``analyze_v2``.
    """

    id: str
    version: str
    tier: Tier
    requires_capabilities: tuple[str, ...] = ()
    requires_services: tuple[str, ...] = ()
    declared_check_ids: tuple[str, ...] = ()
    config_schema: dict | None = field(default=None)
