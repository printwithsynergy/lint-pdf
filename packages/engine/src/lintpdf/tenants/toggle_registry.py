"""Phase 0.7 PR-B1 — declarative registry of unified-config toggle categories.

Ships nine top-level :class:`Toggle` rows that anchor the unified
configuration cascade. Each row is a *category container*: its
``default_value`` is a dict (or list) keyed by the per-instance id
(brand spec id, profile id, mapping name, etc.), and the merge
strategy is :class:`MergeStrategy.MERGE` so tenant + workflow + call
scopes can each contribute their own keys without clobbering.

This pattern (DQ-A1 — one Toggle per category, value=dict) keeps the
registry small (one row per category, not per instance) while still
letting tenants own arbitrary numbers of brand specs, profiles, and
import mappings without exploding the registry table.

Categories
----------

* ``profile_rules`` — preflight rule packs keyed by profile_id
* ``brand`` — brand specifications keyed by spec_id
* ``approval_template`` — approval chain templates keyed by template_id
* ``import_mapping`` — external-format mappings keyed by mapping_name
* ``endpoint_defaults`` — workflow-level defaults (profile_id, brand_spec_id)
* ``epm_thresholds`` — rich-black recipe + TAC limits + ΔE/ΔC ceilings (lockable)
* ``ai_cost_cap`` — per-tenant LLM cost cap (lockable)
* ``response_format`` — sync/async, webhook hooks, render flags
* ``viewer_capabilities`` — viewer feature toggles + branding knobs

The seed is idempotent: re-running :func:`seed_category_toggles`
inserts only the rows that are missing. Consumers who need to mutate
defaults should ship a follow-up alembic data migration that updates
the ``default_value`` JSON in place rather than re-running this seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from lintpdf.tenants.toggle_models import (
    MergeStrategy,
    Toggle,
    ToggleScope,
    ToggleType,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(frozen=True)
class _CategorySpec:
    """Declarative spec for a top-level category Toggle."""

    toggle_id: str
    category: str
    human_name: str
    type: ToggleType
    default_value: Any
    override_at: tuple[ToggleScope, ...]
    lockable: bool = False
    merge_strategy: MergeStrategy = MergeStrategy.MERGE
    description: str = ""


# Defaults are intentionally minimal — sensible empty containers for
# instance-keyed categories, conservative non-zero defaults for
# threshold-bearing categories. A live tenant inherits these unless its
# own override row sets a different value.

_DEFAULT_EPM_THRESHOLDS: dict[str, Any] = {
    # Q-C2: Enfocus de facto standard for rich-black recipe.
    "rich_black": {"c": 40, "m": 20, "y": 20, "k": 80},
    # Q-C3: coated default substrate; higher TAC budget (320%) than
    # uncoated (240%) to reduce false positives on mainstream stocks.
    "tac_limit_coated_pct": 320,
    "tac_limit_uncoated_pct": 240,
    # Conservative ΔE / ΔC ceilings; per-tenant overrides typical for
    # tighter brand-color compliance regimes.
    "delta_e_max": 4.0,
    "delta_c_max": 3.0,
}

_DEFAULT_AI_COST_CAP: dict[str, Any] = {
    # Q-C5: off-by-default + opt-in cap.
    "enabled": False,
    "monthly_cap_cents": 0,
    "alert_threshold_pct": 80,
}

_DEFAULT_RESPONSE_FORMAT: dict[str, Any] = {
    "mode": "async",
    "webhook_url": None,
    "immediate_render": False,
}

_DEFAULT_VIEWER_CAPABILITIES: dict[str, Any] = {
    "enable_separations": True,
    "enable_layers": True,
    "enable_fonts": True,
    "enable_images": True,
    "enable_tac": True,
    "enable_metadata": True,
}

_DEFAULT_ENDPOINT_DEFAULTS: dict[str, Any] = {
    "profile_id": "lintpdf-default",
    "default_brand_spec_id": None,
}


CATEGORY_REGISTRY: tuple[_CategorySpec, ...] = (
    _CategorySpec(
        toggle_id="profile_rules",
        category="profile_rules",
        human_name="Preflight rule packs",
        type=ToggleType.OBJECT,
        default_value={},
        override_at=(ToggleScope.TENANT, ToggleScope.WORKFLOW, ToggleScope.CALL),
        description=(
            "Registry of preflight rule packs keyed by profile_id."
            " Each value is a full PreflightProfile JSON (workflow,"
            " conformance, checks, thresholds, ai, color, report)."
        ),
    ),
    _CategorySpec(
        toggle_id="brand",
        category="brand",
        human_name="Brand specifications",
        type=ToggleType.OBJECT,
        default_value={},
        override_at=(ToggleScope.TENANT, ToggleScope.WORKFLOW, ToggleScope.CALL),
        description=(
            "Brand specs keyed by spec_id. Each value carries name,"
            " customer_name, colors[], rich_black_spec, etc."
        ),
    ),
    _CategorySpec(
        toggle_id="approval_template",
        category="approval_template",
        human_name="Approval chain templates",
        type=ToggleType.OBJECT,
        default_value={},
        override_at=(ToggleScope.TENANT, ToggleScope.WORKFLOW),
        description=(
            "Approval-chain templates keyed by template_id. Each value"
            " carries name, description, steps[]."
        ),
    ),
    _CategorySpec(
        toggle_id="import_mapping",
        category="import_mapping",
        human_name="External format import mappings",
        type=ToggleType.OBJECT,
        default_value={},
        override_at=(ToggleScope.TENANT,),
        description=(
            "External-format mappings keyed by mapping_name. Each value"
            " carries format ('xml'|'json'), config (selectors,"
            " field_paths, severity_map), sample_payload, sample_mime."
        ),
    ),
    _CategorySpec(
        toggle_id="endpoint_defaults",
        category="endpoint_defaults",
        human_name="Endpoint / workflow defaults",
        type=ToggleType.OBJECT,
        default_value=_DEFAULT_ENDPOINT_DEFAULTS,
        override_at=(ToggleScope.TENANT, ToggleScope.WORKFLOW, ToggleScope.CALL),
        description=(
            "Defaults applied when a job is submitted without an"
            " explicit profile_id or brand_spec_id. Set at WORKFLOW"
            " scope to pin a profile to a specific named workflow"
            " (replaces legacy CustomEndpoint behavior)."
        ),
    ),
    _CategorySpec(
        toggle_id="epm_thresholds",
        category="epm_thresholds",
        human_name="EPM thresholds (rich-black, TAC, ΔE/ΔC)",
        type=ToggleType.OBJECT,
        default_value=_DEFAULT_EPM_THRESHOLDS,
        override_at=(ToggleScope.TENANT, ToggleScope.WORKFLOW, ToggleScope.CALL),
        # Q-E2: pharma BR-05 + regulatory R-* checks need the lock.
        lockable=True,
        description=(
            "Rich-black recipe (CMYK percentages), TAC limits per"
            " substrate, ΔE/ΔC color difference ceilings. Lockable at"
            " TENANT scope for compliance regimes."
        ),
    ),
    _CategorySpec(
        toggle_id="ai_cost_cap",
        category="ai_cost_cap",
        human_name="Per-tenant LLM cost cap",
        type=ToggleType.OBJECT,
        default_value=_DEFAULT_AI_COST_CAP,
        # Cost cap is a tenant-level concern — workflows and calls"
        # cannot raise it.
        override_at=(ToggleScope.TENANT,),
        lockable=True,
        description=(
            "Per-tenant LLM cost ceiling (cents/month). Off by default"
            " (enabled=false). Lockable so finance can prevent rogue"
            " escalation by individual administrators."
        ),
    ),
    _CategorySpec(
        toggle_id="response_format",
        category="response_format",
        human_name="Response format",
        type=ToggleType.OBJECT,
        default_value=_DEFAULT_RESPONSE_FORMAT,
        override_at=(ToggleScope.TENANT, ToggleScope.WORKFLOW, ToggleScope.CALL),
        description=(
            "Job response shape — sync vs async, webhook delivery hook,"
            " immediate-render flag for low-latency dashboards."
        ),
    ),
    _CategorySpec(
        toggle_id="viewer_capabilities",
        category="viewer_capabilities",
        human_name="Viewer capabilities",
        type=ToggleType.OBJECT,
        default_value=_DEFAULT_VIEWER_CAPABILITIES,
        override_at=(ToggleScope.TENANT, ToggleScope.WORKFLOW, ToggleScope.CALL),
        description=(
            "Per-feature viewer toggles (enable_separations, layers,"
            " fonts, images, tac, metadata). Tenants can disable"
            " expensive analyses per workflow for cost reasons."
        ),
    ),
)


def seed_category_toggles(session: Session, *, dry_run: bool = False) -> int:
    """Idempotently insert any missing category :class:`Toggle` rows.

    Returns the number of rows created. Safe to call on every app
    startup; existing rows are left alone (no overwrites of
    ``default_value`` even if the spec changed). Use a follow-up
    alembic data migration to mutate live defaults.
    """
    created = 0
    for spec in CATEGORY_REGISTRY:
        existing = session.get(Toggle, spec.toggle_id)
        if existing is not None:
            continue
        if dry_run:
            created += 1
            continue
        session.add(
            Toggle(
                id=spec.toggle_id,
                category=spec.category,
                human_name=spec.human_name,
                type=spec.type,
                default_value=spec.default_value,
                override_at=list(spec.override_at),
                merge_strategy=spec.merge_strategy,
                lockable=spec.lockable,
                description=spec.description,
            )
        )
        created += 1
    if not dry_run and created > 0:
        session.flush()
    return created


__all__ = ["CATEGORY_REGISTRY", "seed_category_toggles"]
