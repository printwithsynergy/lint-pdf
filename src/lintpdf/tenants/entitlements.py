"""Tenant entitlement resolution — merges plan defaults with per-tenant overrides."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lintpdf.tenants.models import ALL_PREFLIGHT_SOURCES, PLAN_LIMITS, TenantPlan

# Canonical set of AI feature flag names. Unknown flags are rejected
# by the admin PATCH schema so typos never land silently in the DB.
# Keep this in lock-step with the PLAN_LIMITS baselines below.
AI_FEATURE_FLAGS: frozenset[str] = frozenset(
    {
        "audit",
        "ocr",
        "dieline",
        "art_size",
        "legend",
        "similarity",
        "internal_opus",
        "sonnet_fallback",
    }
)


@dataclass(frozen=True)
class TenantEntitlements:
    """Effective entitlements for a tenant (immutable within a request)."""

    rate_limit_daily: int
    max_file_size_mb: int
    max_custom_profiles: int
    overage_rate_cents: int
    report_storage_mb: int
    report_default_expiry_days: int
    allowed_report_formats: list[str]
    allowed_preflight_sources: list[str]
    capability_fillin_enabled: bool
    annotations_enabled: bool
    webhooks_enabled: bool
    whitelabel_enabled: bool
    priority_processing: bool
    custom_integrations: bool
    custom_profiles: bool
    max_webhooks: int
    ai_enabled: bool
    approval_chains_enabled: bool = False
    max_approval_templates: int | None = None
    desktop_app_enabled: bool = False
    # Metered-resource monthly allotments (see billing/metered_packs.py).
    # ``monthly_ai_credits`` is the monthly AI-credit grant in INTEGER
    # CENTS (500 = $5.00) — rescaled from whole dollars by Alembic
    # migration 037. Tenants can also buy top-up packs via Stripe
    # Checkout that roll over.
    # ``monthly_files_included`` is the monthly file/job allotment; the
    # daily ``rate_limit_daily`` still serves as an abuse shield on top
    # of this monthly cap.
    monthly_ai_credits: int = 0
    monthly_files_included: int = 0
    # Per-feature AI grant list. Drives every AI call site via the
    # AND-gate ``ai_enabled AND feature in ai_features``. Replaces
    # the old ``ai_audit_enabled`` bool (migration 037). Flags:
    # see :data:`AI_FEATURE_FLAGS`.
    ai_features: frozenset[str] = field(default_factory=frozenset)

    def can_use(self, feature: str) -> bool:
        """Return True when the tenant may use this AI feature.

        AND-gate: both the master ``ai_enabled`` switch and an
        explicit ``feature in ai_features`` grant must be present.
        Unknown feature names always return False so a typo at a
        call site never silently allows an AI call.
        """
        if feature not in AI_FEATURE_FLAGS:
            return False
        return bool(self.ai_enabled) and feature in self.ai_features


def _coerce_feature_list(raw: Any) -> frozenset[str]:
    """Normalize whatever shape ``ai_features`` arrives as into a frozenset.

    Accepts list/tuple/set/frozenset of strings; drops unknown flag
    names silently (the admin PATCH schema is the validation surface).
    """
    if raw is None:
        return frozenset()
    if isinstance(raw, str):
        # Defensive: a JSON string that wasn't decoded.
        raw = [raw]
    try:
        items = {str(x) for x in raw}
    except TypeError:
        return frozenset()
    return frozenset(i for i in items if i in AI_FEATURE_FLAGS)


def _plan_tier_overrides(plan: TenantPlan) -> dict[str, Any]:
    """Fetch the operator-edited overrides row for this plan, if any.

    Reads ``plan_limit_overrides`` through a short-lived Session taken
    from the existing engine pool. Short TTL ``lru_cache`` keeps the
    resolver path O(1) — ops edits via the admin UI invalidate the
    cache via :func:`invalidate_plan_tier_cache` below.

    Phase 0.7 PR-B4 — bail out fast when ``DATABASE_URL`` is unset so
    the test harness doesn't block on a settings-default
    ``postgresql://localhost:5432/lintpdf`` connect timeout. Production
    callers always have ``DATABASE_URL`` set; this guard is a no-op
    for them.
    """
    import os

    # Fail-fast guard for harnesses that explicitly disable the DB
    # (conftest._disable_lifespan_services sets these to ""); without
    # this the deferred ``init_db(settings.database_url)`` falls back
    # to the postgres-localhost default and stalls every route that
    # entitlement-checks until the kernel closes the dead socket.
    if not os.environ.get("DATABASE_URL") and not os.environ.get("LINTPDF_DATABASE_URL"):
        return {}

    # W6c: dispatch through the PlanOverridesService factory so the
    # SaaS shell can inject its own implementation that reads from
    # lintpdf_saas.api.models.PlanLimitOverride. The default service
    # reads the model from lintpdf.api.models if importable, else
    # returns {} (sensible fallback to hardcoded plan defaults).
    from lintpdf.services.plan_overrides import get_plan_overrides_service

    return get_plan_overrides_service().resolve_for_plan(plan.value)


def resolve_entitlements(tenant: Any) -> TenantEntitlements:
    """Compute effective entitlements by merging layered defaults.

    Priority (highest to lowest):
    1. ``entitlement_overrides`` JSON column (admin per-tenant overrides)
    2. ``tenant.ai_features`` column (WS-F — dedicated JSONB)
    3. Dedicated per-tenant columns (``rate_limit_daily``, etc.) when
       they differ from plan defaults (backward-compat)
    4. ``plan_limit_overrides`` row for this plan (operator-editable,
       effective for every tenant on the plan)
    5. ``PLAN_LIMITS`` hardcoded defaults for the tenant's plan

    ``ai_features`` merges by set-union across layers, not overwrite,
    so a plan-tier grant is never silently stripped by an
    unrelated per-tenant override.
    """
    plan = TenantPlan(tenant.plan)
    plan_defaults = dict(PLAN_LIMITS[plan])
    overrides = getattr(tenant, "entitlement_overrides", None) or {}

    merged: dict[str, Any] = {**plan_defaults}
    plan_tier = _plan_tier_overrides(plan)
    merged.update(plan_tier)

    tenant_rate = getattr(tenant, "rate_limit_daily", None)
    if tenant_rate is not None and tenant_rate != plan_defaults["rate_limit_daily"]:
        merged["rate_limit_daily"] = tenant_rate

    tenant_max_mb = getattr(tenant, "max_file_size_mb", None)
    if tenant_max_mb is not None and tenant_max_mb != plan_defaults["max_file_size_mb"]:
        merged["max_file_size_mb"] = tenant_max_mb

    merged.update(overrides)

    credits_override = getattr(tenant, "monthly_ai_credits_override", None)
    if credits_override is not None:
        merged["monthly_ai_credits"] = credits_override
    files_override = getattr(tenant, "monthly_files_override", None)
    if files_override is not None:
        merged["monthly_files_included"] = files_override

    # Union-merge ai_features across every layer. Order-insensitive
    # because it's a set — but we *do* want PLAN + plan-tier +
    # per-tenant grants to all accumulate.
    ai_features = frozenset().union(
        _coerce_feature_list(plan_defaults.get("ai_features")),
        _coerce_feature_list(plan_tier.get("ai_features")),
        _coerce_feature_list(overrides.get("ai_features")),
        _coerce_feature_list(getattr(tenant, "ai_features", None)),
    )

    return TenantEntitlements(
        rate_limit_daily=merged["rate_limit_daily"],
        max_file_size_mb=merged["max_file_size_mb"],
        max_custom_profiles=merged["max_custom_profiles"],
        overage_rate_cents=merged["overage_rate_cents"],
        report_storage_mb=merged["report_storage_mb"],
        report_default_expiry_days=merged["report_default_expiry_days"],
        allowed_report_formats=list(merged["allowed_report_formats"]),
        allowed_preflight_sources=list(
            merged.get("allowed_preflight_sources", ALL_PREFLIGHT_SOURCES)
        ),
        capability_fillin_enabled=bool(merged.get("capability_fillin_enabled", True)),
        annotations_enabled=bool(merged.get("annotations_enabled", True)),
        webhooks_enabled=merged["webhooks_enabled"],
        whitelabel_enabled=merged["whitelabel_enabled"],
        priority_processing=merged["priority_processing"],
        custom_integrations=merged["custom_integrations"],
        custom_profiles=merged["custom_profiles"],
        max_webhooks=merged["max_webhooks"],
        ai_enabled=merged.get("ai_enabled", False),
        approval_chains_enabled=merged.get("approval_chains_enabled", False),
        max_approval_templates=merged.get("max_approval_templates", 0),
        desktop_app_enabled=merged.get("desktop_app_enabled", False),
        monthly_ai_credits=int(merged.get("monthly_ai_credits", 0) or 0),
        monthly_files_included=int(merged.get("monthly_files_included", 0) or 0),
        ai_features=ai_features,
    )
