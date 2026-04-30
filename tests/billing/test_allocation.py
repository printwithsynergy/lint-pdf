"""Unit tests for the metered-resource allocator (credits + files)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from siftpdf.api.models import TenantAICreditPackage
from siftpdf.billing.allocation import (
    allocate_monthly,
    fulfill_purchase,
)
from tests.api.conftest import PLACEHOLDER_TENANT_ID


def _period() -> datetime:
    return datetime(2026, 4, 1, tzinfo=timezone.utc)


class TestAllocateMonthly:
    @staticmethod
    def test_grants_credits_on_growth_tier(db_session) -> None:
        from siftpdf.api.models import Tenant

        tenant = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        # Conftest seeds a GROWTH tenant (monthly_ai_credits=500).
        result = allocate_monthly(
            tenant,
            "credits",
            db_session,
            billing_period_start=_period(),
            source_event="invoice.paid",
        )
        db_session.commit()
        assert result is not None
        assert result.amount == 500
        assert result.source == "plan_monthly"
        assert result.created is True

        pkg = db_session.query(TenantAICreditPackage).filter_by(id=result.package_id).one()
        assert pkg.kind == "credits"
        assert pkg.credits_remaining == 500
        # SQLite strips timezone info → compare naive.
        assert pkg.billing_period_start.replace(tzinfo=None) == _period().replace(tzinfo=None)

    @staticmethod
    def test_idempotent_on_same_period(db_session) -> None:
        from siftpdf.api.models import Tenant

        tenant = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        first = allocate_monthly(
            tenant,
            "credits",
            db_session,
            billing_period_start=_period(),
            source_event="invoice.paid",
        )
        db_session.commit()
        second = allocate_monthly(
            tenant,
            "credits",
            db_session,
            billing_period_start=_period(),
            source_event="invoice.paid",
        )
        db_session.commit()
        assert first is not None and second is not None
        assert first.package_id == second.package_id
        assert second.created is False

        # Only one row exists for (tenant, kind, plan_monthly, period).
        count = (
            db_session.query(TenantAICreditPackage)
            .filter_by(
                tenant_id=tenant.id,
                kind="credits",
                source="plan_monthly",
                billing_period_start=_period(),
            )
            .count()
        )
        assert count == 1

    @staticmethod
    def test_files_grants_are_distinct_from_credits(db_session) -> None:
        from siftpdf.api.models import Tenant

        tenant = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        c = allocate_monthly(
            tenant,
            "credits",
            db_session,
            billing_period_start=_period(),
            source_event="invoice.paid",
        )
        f = allocate_monthly(
            tenant,
            "files",
            db_session,
            billing_period_start=_period(),
            source_event="invoice.paid",
        )
        db_session.commit()
        assert c is not None and f is not None
        assert c.package_id != f.package_id
        assert c.kind == "credits"
        assert f.kind == "files"

    @staticmethod
    def test_returns_none_when_plan_allots_zero(db_session) -> None:
        from siftpdf.api.models import Tenant, TenantPlan

        tenant = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        tenant.plan = TenantPlan.FREE  # FREE has monthly_ai_credits=0
        db_session.commit()
        result = allocate_monthly(
            tenant,
            "credits",
            db_session,
            billing_period_start=_period(),
            source_event="invoice.paid",
        )
        assert result is None

    @staticmethod
    def test_override_wins_over_plan_default(db_session) -> None:
        from siftpdf.api.models import Tenant, TenantPlan

        tenant = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        tenant.plan = TenantPlan.FREE  # plan default = 0
        tenant.monthly_ai_credits_override = 750
        db_session.commit()
        result = allocate_monthly(
            tenant,
            "credits",
            db_session,
            billing_period_start=_period(),
            source_event="invoice.paid",
        )
        db_session.commit()
        assert result is not None
        assert result.amount == 750


class TestFulfillPurchase:
    @staticmethod
    def test_inserts_purchase_package(db_session) -> None:
        tenant_id = PLACEHOLDER_TENANT_ID
        result = fulfill_purchase(
            tenant_id=tenant_id,
            kind="credits",
            pack_size=500,
            price_cents=2500,
            stripe_session_id="cs_test_abc123",
            db=db_session,
        )
        db_session.commit()
        pkg = db_session.query(TenantAICreditPackage).filter_by(id=result.package_id).one()
        assert pkg.source == "purchase"
        assert pkg.credits_purchased == 500
        assert pkg.credits_remaining == 500
        assert pkg.stripe_session_id == "cs_test_abc123"
        assert pkg.price_paid == Decimal("25.00")
        assert pkg.expires_at is not None

    @staticmethod
    def test_idempotent_on_session_id(db_session) -> None:
        first = fulfill_purchase(
            tenant_id=PLACEHOLDER_TENANT_ID,
            kind="credits",
            pack_size=500,
            price_cents=2500,
            stripe_session_id="cs_test_dup",
            db=db_session,
        )
        db_session.commit()
        second = fulfill_purchase(
            tenant_id=PLACEHOLDER_TENANT_ID,
            kind="credits",
            pack_size=500,
            price_cents=2500,
            stripe_session_id="cs_test_dup",
            db=db_session,
        )
        assert first.package_id == second.package_id
        assert second.created is False

    @staticmethod
    def test_rejects_unknown_pack_size(db_session) -> None:
        with pytest.raises(ValueError, match="Unknown"):
            fulfill_purchase(
                tenant_id=PLACEHOLDER_TENANT_ID,
                kind="credits",
                pack_size=123,  # not in catalogue
                price_cents=1000,
                stripe_session_id="cs_test_bad",
                db=db_session,
            )
