"""Tenant entitlement resolution — merges plan defaults with per-tenant overrides."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lintpdf.tenants.models import ALL_PREFLIGHT_SOURCES, PLAN_LIMITS, TenantPlan


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
    # ``monthly_ai_credits`` is the monthly AI-credit grant; tenants can
    # also buy top-up packs via Stripe Checkout that roll over.
    # ``monthly_files_included`` is the monthly file/job allotment; the
    # daily ``rate_limit_daily`` still serves as an abuse shield on top
    # of this monthly cap.
    monthly_ai_credits: int = 0
    monthly_files_included: int = 0
    # AI accuracy audit — when True the customer-facing Modal auditor
    # runs after every preflight and writes per-finding verdicts to
    # JobFinding.audit_*. Gated to Scale + Enterprise by default; ops
    # can flip it on any tenant via ``entitlement_overrides`` for
    # pilots. Internal Opus harness runs regardless of this flag —
    # it's operator-side, not customer-visible.
    ai_audit_enabled: bool = False


def _plan_tier_overrides(plan: TenantPlan) -> dict[str, Any]:
    """Fetch the operator-edited overrides row for this plan, if any.

    Reads ``plan_limit_overrides`` through a short-lived Session taken
    from the existing engine pool. Short TTL ``lru_cache`` keeps the
    resolver path O(1) — ops edits via the admin UI invalidate the
    cache via :func:`invalidate_plan_tier_cache` below.
    """
    # Deferred import so this module doesn't pull the whole API stack
    # when only the dataclass is needed (tests, Celery boot).
    from lintpdf.api.database import get_db_session
    from lintpdf.api.models import PlanLimitOverride

    try:
        session = get_db_session()
    except Exception:
        return {}
    import contextlib

    try:
        row = (
            session.query(PlanLimitOverride)
            .filter(PlanLimitOverride.plan == plan.value)
            .first()
        )
        if row is None or not row.overrides:
            return {}
        return dict(row.overrides)
    except Exception:
        # A missing table (pre-035) or transient DB flap just means
        # "no plan-tier overrides yet" — fall back to hardcoded
        # PLAN_LIMITS without failing the request.
        return {}
    finally:
        with contextlib.suppress(Exception):
            session.close()


def resolve_entitlements(tenant: Any) -> TenantEntitlements:
    """Compute effective entitlements by merging layered defaults.

    Priority (highest to lowest):
    1. ``entitlement_overrides`` JSON column (admin per-tenant overrides)
    2. Dedicated per-tenant columns (``rate_limit_daily``, etc.) when
       they differ from plan defaults (backward-compat)
    3. ``plan_limit_overrides`` row for this plan (operator-editable,
       effective for every tenant on the plan)
    4. ``PLAN_LIMITS`` hardcoded defaults for the tenant's plan

    Args:
        tenant: SQLAlchemy Tenant model instance (or any object with
                ``plan``, ``entitlement_overrides``, ``rate_limit_daily``,
                ``max_file_size_mb`` attributes).

    Returns:
        Frozen ``TenantEntitlements`` dataclass.
    """
    plan = TenantPlan(tenant.plan)
    plan_defaults = dict(PLAN_LIMITS[plan])
    overrides = getattr(tenant, "entitlement_overrides", None) or {}

    # Start with hardcoded plan defaults, then layer ops-edited
    # plan-tier overrides before the per-tenant merge.
    merged: dict[str, Any] = {**plan_defaults}
    merged.update(_plan_tier_overrides(plan))

    # Layer in legacy column overrides (only if they differ from plan default)
    tenant_rate = getattr(tenant, "rate_limit_daily", None)
    if tenant_rate is not None and tenant_rate != plan_defaults["rate_limit_daily"]:
        merged["rate_limit_daily"] = tenant_rate

    tenant_max_mb = getattr(tenant, "max_file_size_mb", None)
    if tenant_max_mb is not None and tenant_max_mb != plan_defaults["max_file_size_mb"]:
        merged["max_file_size_mb"] = tenant_max_mb

    # Layer in JSON overrides (highest priority for generic entitlements)
    merged.update(overrides)

    # Dedicated per-tenant columns for metered-resource monthly caps
    # beat both the plan defaults and the generic JSON overrides, so
    # ops can set ``monthly_ai_credits_override=2000`` on a Growth
    # tenant without reshaping their entitlement_overrides blob.
    credits_override = getattr(tenant, "monthly_ai_credits_override", None)
    if credits_override is not None:
        merged["monthly_ai_credits"] = credits_override
    files_override = getattr(tenant, "monthly_files_override", None)
    if files_override is not None:
        merged["monthly_files_included"] = files_override

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
        ai_audit_enabled=bool(merged.get("ai_audit_enabled", False)),
    )
