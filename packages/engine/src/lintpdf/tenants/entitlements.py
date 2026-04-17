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


def resolve_entitlements(tenant: Any) -> TenantEntitlements:
    """Compute effective entitlements by merging plan defaults + tenant overrides.

    Priority (highest to lowest):
    1. ``entitlement_overrides`` JSON column (admin per-tenant overrides)
    2. Legacy direct columns (``rate_limit_daily``, ``max_file_size_mb``) when
       they differ from plan defaults (backward-compatible with existing admin API)
    3. ``PLAN_LIMITS`` defaults for the tenant's plan

    Args:
        tenant: SQLAlchemy Tenant model instance (or any object with ``plan``,
                ``entitlement_overrides``, ``rate_limit_daily``, and
                ``max_file_size_mb`` attributes).

    Returns:
        Frozen ``TenantEntitlements`` dataclass.
    """
    plan = TenantPlan(tenant.plan)
    plan_defaults = dict(PLAN_LIMITS[plan])
    overrides = getattr(tenant, "entitlement_overrides", None) or {}

    # Start with plan defaults
    merged: dict[str, Any] = {**plan_defaults}

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
    )
