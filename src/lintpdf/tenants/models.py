"""Tenant domain models and plan definitions."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class TenantPlan(enum.StrEnum):
    """Subscription plans with resource limits."""

    FREE = "free"
    VIEWER = "viewer"
    STARTER = "starter"
    GROWTH = "growth"
    SCALE = "scale"
    ENTERPRISE = "enterprise"


ALL_PREFLIGHT_SOURCES: list[str] = ["engine", "external", "minimal"]


# AI-feature baselines per plan. Resolver union-merges with
# ``plan_limit_overrides.ai_features`` + per-tenant grants, so
# these are the floor. ``monthly_ai_credits`` is in **integer
# cents** post-migration 037.
#
# STARTER: no AI — trial / low-ceiling plan.
# GROWTH:  audit only (the main cross-sell feature).
# SCALE:   full packaging stack.
# ENTERPRISE: SCALE + similarity + Sonnet fallback routing.
_AI_FEATURES_GROWTH: list[str] = ["audit"]
_AI_FEATURES_SCALE: list[str] = [
    "audit",
    "ocr",
    "dieline",
    "art_size",
    "legend",
]
_AI_FEATURES_ENTERPRISE: list[str] = [
    *_AI_FEATURES_SCALE,
    "similarity",
    "sonnet_fallback",
]


# Plan limits configuration
PLAN_LIMITS: dict[TenantPlan, dict[str, Any]] = {
    TenantPlan.FREE: {
        "rate_limit_daily": 50,
        "max_file_size_mb": 25,
        "max_custom_profiles": 1,
        "overage_rate_cents": 0,
        "report_storage_mb": 100,
        "report_default_expiry_days": 7,
        "allowed_report_formats": ["json", "html"],
        "allowed_preflight_sources": ALL_PREFLIGHT_SOURCES,
        "capability_fillin_enabled": True,
        "annotations_enabled": True,
        "webhooks_enabled": False,
        "whitelabel_enabled": False,
        "priority_processing": False,
        "custom_integrations": False,
        "custom_profiles": False,
        "max_webhooks": 0,
        "approval_chains_enabled": False,
        "max_approval_templates": 0,
        "desktop_app_enabled": False,
        "monthly_ai_credits": 0,
        "monthly_files_included": 50,
        "ai_features": [],
    },
    TenantPlan.VIEWER: {
        "rate_limit_daily": 150,
        "max_file_size_mb": 250,
        "max_custom_profiles": 0,
        "overage_rate_cents": 5,
        "report_storage_mb": 2048,
        "report_default_expiry_days": 30,
        "allowed_report_formats": [],
        "allowed_preflight_sources": ["minimal", "external"],
        "capability_fillin_enabled": False,
        "annotations_enabled": False,
        "webhooks_enabled": False,
        "whitelabel_enabled": False,
        "priority_processing": False,
        "custom_integrations": False,
        "custom_profiles": False,
        "max_webhooks": 0,
        "approval_chains_enabled": False,
        "max_approval_templates": 0,
        "desktop_app_enabled": False,
        "monthly_ai_credits": 0,
        "monthly_files_included": 50,
        "ai_features": [],
    },
    TenantPlan.STARTER: {
        "rate_limit_daily": 500,
        "max_file_size_mb": 250,
        "max_custom_profiles": 10,
        "overage_rate_cents": 10,
        "report_storage_mb": 5120,
        "report_default_expiry_days": 30,
        "allowed_report_formats": ["json", "html", "pdf", "xml"],
        "allowed_preflight_sources": ALL_PREFLIGHT_SOURCES,
        "capability_fillin_enabled": True,
        "annotations_enabled": True,
        "webhooks_enabled": False,
        "whitelabel_enabled": False,
        "priority_processing": False,
        "custom_integrations": False,
        "custom_profiles": False,
        "max_webhooks": 0,
        "approval_chains_enabled": False,
        "max_approval_templates": 0,
        "desktop_app_enabled": False,
        # Value was 100 whole dollars pre-037 — migration multiplies
        # every existing row by 100. Hardcoded defaults are authored
        # directly in cents; no retroactive math needed.
        "monthly_ai_credits": 0,
        "monthly_files_included": 500,
        "ai_features": [],
    },
    TenantPlan.GROWTH: {
        "rate_limit_daily": 5000,
        "max_file_size_mb": 500,
        "max_custom_profiles": 25,
        "overage_rate_cents": 10,
        "report_storage_mb": 25600,
        "report_default_expiry_days": 90,
        "allowed_report_formats": ["json", "html", "pdf", "xml"],
        "allowed_preflight_sources": ALL_PREFLIGHT_SOURCES,
        "capability_fillin_enabled": True,
        "annotations_enabled": True,
        "webhooks_enabled": True,
        "whitelabel_enabled": False,
        "priority_processing": False,
        "custom_integrations": False,
        "custom_profiles": True,
        "max_webhooks": 5,
        "approval_chains_enabled": True,
        "max_approval_templates": 3,
        "desktop_app_enabled": False,
        # $5.00 cap — enough for audit on ~500 typical jobs/mo at
        # Haiku's $0.01/job amortized cost.
        "monthly_ai_credits": 500,
        "monthly_files_included": 2500,
        "ai_features": _AI_FEATURES_GROWTH,
    },
    TenantPlan.SCALE: {
        "rate_limit_daily": 25000,
        "max_file_size_mb": 1024,
        "max_custom_profiles": 50,
        "overage_rate_cents": 10,
        "report_storage_mb": 51200,
        "report_default_expiry_days": 180,
        "allowed_report_formats": [
            "json",
            "html",
            "pdf",
            "xml",
            "annotated_pdf",
            "annotated_pdf_markup",
        ],
        "allowed_preflight_sources": ALL_PREFLIGHT_SOURCES,
        "capability_fillin_enabled": True,
        "annotations_enabled": True,
        "webhooks_enabled": True,
        "whitelabel_enabled": True,
        "priority_processing": True,
        "custom_integrations": False,
        "custom_profiles": True,
        "max_webhooks": 20,
        "approval_chains_enabled": True,
        "max_approval_templates": None,
        "desktop_app_enabled": False,
        # $25.00 cap.
        "monthly_ai_credits": 2500,
        "monthly_files_included": 10000,
        "ai_features": _AI_FEATURES_SCALE,
    },
    TenantPlan.ENTERPRISE: {
        "rate_limit_daily": 100000,
        "max_file_size_mb": 2048,
        "max_custom_profiles": 100,
        "overage_rate_cents": 10,
        "report_storage_mb": 102400,
        "report_default_expiry_days": 365,
        "allowed_report_formats": [
            "json",
            "html",
            "pdf",
            "xml",
            "annotated_pdf",
            "annotated_pdf_markup",
        ],
        "allowed_preflight_sources": ALL_PREFLIGHT_SOURCES,
        "capability_fillin_enabled": True,
        "annotations_enabled": True,
        "webhooks_enabled": True,
        "whitelabel_enabled": True,
        "priority_processing": True,
        "custom_integrations": True,
        "custom_profiles": True,
        "max_webhooks": 100,
        "approval_chains_enabled": True,
        "max_approval_templates": None,
        "desktop_app_enabled": False,
        # $250.00 cap.
        "monthly_ai_credits": 25000,
        "monthly_files_included": 100000,
        "ai_features": _AI_FEATURES_ENTERPRISE,
    },
}

# Warning thresholds (percentage of limit)
RATE_LIMIT_WARN_THRESHOLD = 80
RATE_LIMIT_OVERAGE_THRESHOLD = 100


@dataclass
class TenantInfo:
    """Domain representation of a tenant (decoupled from DB model)."""

    id: str
    name: str
    plan: TenantPlan
    api_key_hash: str
    rate_limit_daily: int
    max_file_size_mb: int
    is_active: bool = True
    contact_email: str | None = None
    custom_profile_ids: list[str] = field(default_factory=list)
    overage_enabled: bool = False
    overage_cap_cents: int | None = None
    overage_rate_override_cents: int | None = None

    @property
    def overage_rate_cents(self) -> int:
        """Per-job overage charge in cents."""
        if self.overage_rate_override_cents is not None:
            return self.overage_rate_override_cents
        return int(PLAN_LIMITS.get(self.plan, {}).get("overage_rate_cents", 0))

    @property
    def overage_allowed(self) -> bool:
        """Whether this tenant can incur billable overages."""
        return self.overage_enabled and self.overage_rate_cents > 0
