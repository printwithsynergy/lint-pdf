"""Tenant management service backed by SQLAlchemy."""

from __future__ import annotations

import uuid as uuid_mod

from sqlalchemy.orm import Session  # noqa: TC002

from siftpdf.api.auth import generate_api_key, hash_api_key
from siftpdf.api.models import Tenant
from siftpdf.tenants.models import PLAN_LIMITS, TenantInfo, TenantPlan


class TenantService:
    """Service for creating and managing tenants.

    Uses a SQLAlchemy session for persistence.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_tenant(
        self,
        name: str,
        plan: TenantPlan = TenantPlan.FREE,
        contact_email: str | None = None,
        overage_enabled: bool = False,
        overage_cap_cents: int | None = None,
    ) -> tuple[TenantInfo, str]:
        """Create a new tenant and generate an API key.

        Args:
            name: Human-readable tenant name.
            plan: Subscription plan.
            contact_email: Optional contact email for notifications.
            overage_enabled: Whether to allow billable overages.
            overage_cap_cents: Optional daily overage spending cap in cents.

        Returns:
            Tuple of (TenantInfo, raw_api_key).
            The raw API key is only returned once at creation.
        """
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        limits = PLAN_LIMITS[plan]

        tenant = Tenant(
            id=uuid_mod.uuid4(),
            name=name,
            api_key_hash=key_hash,
            plan=plan,
            rate_limit_daily=limits["rate_limit_daily"],
            max_file_size_mb=limits["max_file_size_mb"],
            contact_email=contact_email,
            overage_enabled=overage_enabled,
            overage_cap_cents=overage_cap_cents,
            is_active=True,
        )
        self._db.add(tenant)
        self._db.commit()
        self._db.refresh(tenant)

        return self._to_info(tenant), api_key

    def authenticate(self, api_key: str) -> TenantInfo | None:
        """Authenticate a tenant by API key.

        Args:
            api_key: Raw API key from request header.

        Returns:
            TenantInfo if valid and active, None otherwise.
        """
        key_hash = hash_api_key(api_key)
        tenant: Tenant | None = (
            self._db.query(Tenant).filter(Tenant.api_key_hash == key_hash).first()
        )
        if tenant is None or not tenant.is_active:
            return None
        return self._to_info(tenant)

    def get_tenant(self, tenant_id: str) -> TenantInfo | None:
        """Get tenant by ID."""
        try:
            uid = uuid_mod.UUID(tenant_id)
        except ValueError:
            return None
        tenant: Tenant | None = self._db.query(Tenant).filter(Tenant.id == uid).first()
        if tenant is None:
            return None
        return self._to_info(tenant)

    def deactivate_tenant(self, tenant_id: str) -> bool:
        """Deactivate a tenant account.

        Returns:
            True if tenant was found and deactivated.
        """
        try:
            uid = uuid_mod.UUID(tenant_id)
        except ValueError:
            return False
        tenant: Tenant | None = self._db.query(Tenant).filter(Tenant.id == uid).first()
        if tenant is None:
            return False
        tenant.is_active = False
        self._db.commit()
        return True

    def update_plan(self, tenant_id: str, new_plan: TenantPlan) -> bool:
        """Update a tenant's subscription plan.

        Args:
            tenant_id: Tenant to update.
            new_plan: New subscription plan.

        Returns:
            True if tenant was found and updated.
        """
        try:
            uid = uuid_mod.UUID(tenant_id)
        except ValueError:
            return False
        tenant: Tenant | None = self._db.query(Tenant).filter(Tenant.id == uid).first()
        if tenant is None:
            return False

        limits = PLAN_LIMITS[new_plan]
        tenant.plan = new_plan
        tenant.rate_limit_daily = limits["rate_limit_daily"]
        tenant.max_file_size_mb = limits["max_file_size_mb"]
        self._db.commit()
        return True

    def update_overage_settings(
        self,
        tenant_id: str,
        *,
        overage_enabled: bool | None = None,
        overage_cap_cents: int | None = ...,  # type: ignore[assignment]  # sentinel
        overage_rate_override_cents: int | None = ...,  # type: ignore[assignment]  # sentinel
    ) -> bool:
        """Update overage billing settings for a tenant.

        Use ``...`` (sentinel) to leave a field unchanged; ``None`` to clear it.

        Returns:
            True if tenant was found and updated.
        """
        try:
            uid = uuid_mod.UUID(tenant_id)
        except ValueError:
            return False
        tenant: Tenant | None = self._db.query(Tenant).filter(Tenant.id == uid).first()
        if tenant is None:
            return False

        if overage_enabled is not None:
            tenant.overage_enabled = overage_enabled
        if overage_cap_cents is not ...:  # type: ignore[comparison-overlap]
            tenant.overage_cap_cents = overage_cap_cents
        if overage_rate_override_cents is not ...:  # type: ignore[comparison-overlap]
            tenant.overage_rate_override_cents = overage_rate_override_cents
        self._db.commit()
        return True

    @staticmethod
    def check_rate_limit(tenant: TenantInfo, current_usage: int) -> bool:
        """Check if tenant is within daily rate limit."""
        return current_usage < tenant.rate_limit_daily

    @staticmethod
    def check_file_size(tenant: TenantInfo, file_size_bytes: int) -> bool:
        """Check if file size is within tenant's plan limit."""
        max_bytes = tenant.max_file_size_mb * 1024 * 1024
        return file_size_bytes <= max_bytes

    @staticmethod
    def _to_info(tenant: Tenant) -> TenantInfo:
        """Convert a Tenant DB model to a TenantInfo domain object."""
        return TenantInfo(
            id=str(tenant.id),
            name=tenant.name,
            plan=TenantPlan(tenant.plan),
            api_key_hash=tenant.api_key_hash,
            rate_limit_daily=tenant.rate_limit_daily,
            max_file_size_mb=tenant.max_file_size_mb,
            contact_email=tenant.contact_email,
            is_active=tenant.is_active,
            overage_enabled=tenant.overage_enabled,
            overage_cap_cents=tenant.overage_cap_cents,
            overage_rate_override_cents=tenant.overage_rate_override_cents,
        )
