"""Unit tests for ``resolve_report_base_url`` — the white-label URL resolver.

Priority order (highest wins):
  1. Active brand profile's verified ``custom_domain`` (if whitelabel_enabled)
  2. Tenant's verified ``brand_custom_domain``       (if whitelabel_enabled)
  3. ``settings.report_base_url`` (global default)

Unverified domains are silently ignored so a customer mid-onboarding never
gets reports published under a URL that doesn't yet resolve.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from lintpdf.reports.service import resolve_report_base_url
from lintpdf.services.whitelabel import set_whitelabel_service


class _SaaSStyleWhitelabelService:
    """Test-side service mirroring the SaaS impl.

    Same priority chain the previous in-tree ``resolve_report_base_url``
    used — gated on ``entitlements.whitelabel_enabled``.
    """

    def resolve_report_base_url(self, tenant, brand_profile, entitlements, settings):  # type: ignore[no-untyped-def]
        if entitlements.whitelabel_enabled:
            if (
                brand_profile is not None
                and brand_profile.custom_domain
                and brand_profile.custom_domain_verified
            ):
                return f"https://{brand_profile.custom_domain}"
            if tenant.brand_custom_domain and tenant.brand_custom_domain_verified:
                return f"https://{tenant.brand_custom_domain}"
        return settings.report_base_url

    def resolve_viewer_base_url(self, tenant, brand_profile, entitlements, settings):  # type: ignore[no-untyped-def]
        if entitlements.whitelabel_enabled:
            if (
                brand_profile is not None
                and getattr(brand_profile, "app_custom_domain", None)
                and brand_profile.app_custom_domain_verified
            ):
                return f"https://{brand_profile.app_custom_domain}"
            if getattr(tenant, "app_custom_domain", None) and tenant.app_custom_domain_verified:
                return f"https://{tenant.app_custom_domain}"
        return settings.app_base_url


@pytest.fixture(autouse=True)
def _install_whitelabel_service():  # type: ignore[no-untyped-def]
    set_whitelabel_service(_SaaSStyleWhitelabelService())
    yield
    set_whitelabel_service(None)


@dataclass
class _FakeTenant:
    brand_custom_domain: str | None = None
    brand_custom_domain_verified: bool = False


@dataclass
class _FakeProfile:
    custom_domain: str | None = None
    custom_domain_verified: bool = False


@dataclass
class _FakeEntitlements:
    whitelabel_enabled: bool = True


@dataclass
class _FakeSettings:
    report_base_url: str = "https://reports.lintpdf.com"


def test_returns_default_when_tenant_has_nothing() -> None:
    url = resolve_report_base_url(
        _FakeTenant(),
        None,
        _FakeEntitlements(),
        _FakeSettings(),
    )
    assert url == "https://reports.lintpdf.com"


def test_returns_default_when_domain_set_but_unverified() -> None:
    tenant = _FakeTenant(
        brand_custom_domain="reports.acme.example",
        brand_custom_domain_verified=False,
    )
    url = resolve_report_base_url(tenant, None, _FakeEntitlements(), _FakeSettings())
    assert url == "https://reports.lintpdf.com"


def test_returns_tenant_custom_domain_when_verified() -> None:
    tenant = _FakeTenant(
        brand_custom_domain="reports.acme.example",
        brand_custom_domain_verified=True,
    )
    url = resolve_report_base_url(tenant, None, _FakeEntitlements(), _FakeSettings())
    assert url == "https://reports.acme.example"


def test_returns_default_when_plan_drops_whitelabel() -> None:
    tenant = _FakeTenant(
        brand_custom_domain="reports.acme.example",
        brand_custom_domain_verified=True,
    )
    # Tenant's row still has the domain, but the plan no longer allows
    # whitelabel. Resolver must fall back to the default to avoid
    # handing paid features to a downgraded account.
    url = resolve_report_base_url(
        tenant,
        None,
        _FakeEntitlements(whitelabel_enabled=False),
        _FakeSettings(),
    )
    assert url == "https://reports.lintpdf.com"


def test_brand_profile_custom_domain_wins_over_tenant() -> None:
    tenant = _FakeTenant(
        brand_custom_domain="reports.acme.example",
        brand_custom_domain_verified=True,
    )
    profile = _FakeProfile(
        custom_domain="reports.client.example",
        custom_domain_verified=True,
    )
    url = resolve_report_base_url(tenant, profile, _FakeEntitlements(), _FakeSettings())
    assert url == "https://reports.client.example"


def test_brand_profile_unverified_falls_back_to_tenant() -> None:
    tenant = _FakeTenant(
        brand_custom_domain="reports.acme.example",
        brand_custom_domain_verified=True,
    )
    profile = _FakeProfile(
        custom_domain="reports.client.example",
        custom_domain_verified=False,
    )
    url = resolve_report_base_url(tenant, profile, _FakeEntitlements(), _FakeSettings())
    assert url == "https://reports.acme.example"


def test_brand_profile_without_domain_falls_back_to_tenant() -> None:
    tenant = _FakeTenant(
        brand_custom_domain="reports.acme.example",
        brand_custom_domain_verified=True,
    )
    profile = _FakeProfile(custom_domain=None)
    url = resolve_report_base_url(tenant, profile, _FakeEntitlements(), _FakeSettings())
    assert url == "https://reports.acme.example"


def test_settings_override_respects_custom_global_default() -> None:
    tenant = _FakeTenant()
    settings = _FakeSettings(report_base_url="https://custom.example.com")
    url = resolve_report_base_url(tenant, None, _FakeEntitlements(), settings)
    assert url == "https://custom.example.com"
