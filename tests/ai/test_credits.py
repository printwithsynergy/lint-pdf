"""Tests for AI credit metering (lintpdf.ai.credits)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from lintpdf.services.ai_credit_balance import (
    CreditBalance,
    set_ai_credit_balance_service,
)
from lintpdf.services.ai_credit_check import set_ai_credit_check_service
from lintpdf.services.ai_credit_deduction import set_ai_credit_deduction_service

if TYPE_CHECKING:
    from collections.abc import Generator


# Stub model identities for the MagicMock query chain. The tenant_id
# fixture's mock_db_session returns the same chain regardless of the
# class passed to ``db.query(...)``, so these don't need to be real
# ORM classes — they're just opaque tokens. Replacing the SaaS-only
# imports keeps the OSS test surface free of ``TenantAIConfig`` etc.
class _StubTenantAIConfig:
    pass


class _StubTenantAICreditPackage:
    pass


class _StubAIUsageLog:
    """Attribute-bag stub. Tests inspect attrs after ``db.add(...)``."""

    cost = None  # class-level for the MagicMock query chain

    def __init__(self, **kw):  # type: ignore[no-untyped-def]
        for k, v in kw.items():
            setattr(self, k, v)


# Mirror of the SaaS-only ``AIBillingMode`` enum — values match the
# string literals stored in ``TenantAIConfig.billing_mode``.
_BM_PAY_PER_USE = "pay_per_use"
_BM_CREDIT_PACKAGE = "credit_package"


class _SaaSStyleCreditBalanceService:
    """Test-side service mirroring the SaaS read pattern.

    Uses MagicMock-friendly query chain via stub model identities so
    the OSS test file doesn't import the SaaS-only billing models.
    """

    def get_credit_balance(self, tenant_id, db) -> CreditBalance:  # type: ignore[no-untyped-def]
        config = (
            db.query(_StubTenantAIConfig)
            .filter(getattr(_StubTenantAIConfig, "tenant_id", None) == tenant_id)
            .first()
        )
        if config is None:
            return CreditBalance(
                credit_balance=Decimal("0"),
                billing_mode=_BM_PAY_PER_USE,
                packages_active=0,
                package_credits_remaining=0,
                monthly_spent=Decimal("0"),
                monthly_spending_limit=None,
            )

        now = datetime.now(timezone.utc)
        packages = (
            db.query(_StubTenantAICreditPackage)
            .filter(
                getattr(_StubTenantAICreditPackage, "tenant_id", None) == tenant_id,
                getattr(_StubTenantAICreditPackage, "kind", None) == "credits",
                getattr(_StubTenantAICreditPackage, "credits_remaining", 0) > 0,
            )
            .all()
        )
        active_packages = [p for p in packages if p.expires_at is None or p.expires_at > now]
        package_credits = sum(p.credits_remaining for p in active_packages)

        monthly_cost = db.query(_StubAIUsageLog).filter(_StubAIUsageLog.cost is not None).scalar()

        return CreditBalance(
            credit_balance=Decimal(str(config.credit_balance)),
            billing_mode=str(config.billing_mode),
            packages_active=len(active_packages),
            package_credits_remaining=package_credits,
            monthly_spent=Decimal(str(monthly_cost)),
            monthly_spending_limit=(
                Decimal(str(config.monthly_spending_limit))
                if config.monthly_spending_limit is not None
                else None
            ),
        )


class _SaaSStyleCreditCheckService:
    """Test-side credit check service mirroring the SaaS read pattern.

    Walks ``TenantAIConfig`` + delegates to ``get_credit_balance`` for
    the package / spending-limit gate so the mocked DB session sees
    the same query chain the previous in-tree ``check_ai_credits``
    exercised.
    """

    def check_credits(self, tenant_id, credits_needed, db) -> None:  # type: ignore[no-untyped-def]
        from fastapi import HTTPException, status

        from lintpdf.ai.credits import get_credit_balance

        config = (
            db.query(_StubTenantAIConfig)
            .filter(getattr(_StubTenantAIConfig, "tenant_id", None) == tenant_id)
            .first()
        )
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="AI features not configured. No credits available.",
            )

        if config.billing_mode == _BM_CREDIT_PACKAGE:
            balance = get_credit_balance(tenant_id, db)
            if balance.package_credits_remaining < credits_needed:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=(
                        f"Insufficient AI credits. Need {credits_needed}, "
                        f"have {balance.package_credits_remaining}. "
                        "Purchase a credit top-up package to continue."
                    ),
                )
        elif config.monthly_spending_limit is not None:
            balance = get_credit_balance(tenant_id, db)
            estimated_cost = Decimal(str(credits_needed)) * Decimal(str(config.overage_rate))
            if (
                balance.monthly_spending_limit is not None
                and balance.monthly_spent + estimated_cost > balance.monthly_spending_limit
            ):
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=(
                        "Monthly AI spending limit would be exceeded. "
                        f"Limit: {config.monthly_spending_limit}, "
                        f"Current spend: {balance.monthly_spent}."
                    ),
                )


class _SaaSStyleCreditDeductionService:
    """Test-side deduction service mirroring the SaaS write pattern.

    Drains ``TenantAICreditPackage`` rows in oldest-first order,
    computes overage at the configured rate, writes the
    ``AIUsageLog`` row, and fires the threshold webhook. Same query
    chain the previous in-tree ``deduct_credits`` exercised.
    """

    def deduct_credits(
        self,
        tenant_id,  # type: ignore[no-untyped-def]
        job_id,
        category,
        feature,
        credit_amount,
        processing_time_ms,
        result_summary,
        db,
    ) -> None:
        config = (
            db.query(_StubTenantAIConfig)
            .filter(getattr(_StubTenantAIConfig, "tenant_id", None) == tenant_id)
            .first()
        )
        if config is None:
            return

        cost = Decimal("0")

        if config.billing_mode == _BM_CREDIT_PACKAGE:
            now = datetime.now(timezone.utc)
            packages = (
                db.query(_StubTenantAICreditPackage)
                .filter(
                    getattr(_StubTenantAICreditPackage, "tenant_id", None) == tenant_id,
                    getattr(_StubTenantAICreditPackage, "kind", None) == "credits",
                    getattr(_StubTenantAICreditPackage, "credits_remaining", 0) > 0,
                )
                .order_by(getattr(_StubTenantAICreditPackage, "purchased_at", None))
                .all()
            )

            remaining = credit_amount
            for pkg in packages:
                if pkg.expires_at and pkg.expires_at <= now:
                    continue
                if remaining <= 0:
                    break
                deduct = min(remaining, pkg.credits_remaining)
                pkg.credits_remaining -= deduct
                remaining -= deduct

            if remaining > 0:
                cost = Decimal(str(remaining)) * Decimal(str(config.overage_rate))
        else:
            cost = Decimal(str(credit_amount)) * Decimal(str(config.overage_rate))

        db.add(
            _StubAIUsageLog(
                tenant_id=tenant_id,
                job_id=job_id,
                category=category,
                feature=feature,
                credits_consumed=credit_amount,
                cost=cost,
                processing_time_ms=processing_time_ms,
                result_summary=result_summary,
            )
        )
        db.flush()


@pytest.fixture(autouse=True)
def _install_credit_balance_service() -> Generator[None, None, None]:
    set_ai_credit_balance_service(_SaaSStyleCreditBalanceService())
    set_ai_credit_check_service(_SaaSStyleCreditCheckService())
    set_ai_credit_deduction_service(_SaaSStyleCreditDeductionService())
    yield
    set_ai_credit_balance_service(None)
    set_ai_credit_check_service(None)
    set_ai_credit_deduction_service(None)


class TestGetCreditBalance:
    """Tests for get_credit_balance."""

    def test_returns_zero_balance_when_no_config(
        self, mock_db_session: MagicMock, tenant_id
    ) -> None:
        from lintpdf.ai.credits import get_credit_balance

        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        balance = get_credit_balance(tenant_id, mock_db_session)

        assert balance.credit_balance == Decimal("0")
        assert balance.packages_active == 0
        assert balance.package_credits_remaining == 0
        assert balance.monthly_spent == Decimal("0")
        assert balance.monthly_spending_limit is None

    def test_returns_balance_with_config(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        from lintpdf.ai.credits import get_credit_balance

        mock_ai_config.credit_balance = Decimal("50.00")
        mock_ai_config.monthly_spending_limit = Decimal("200.00")
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        mock_db_session.query.return_value.filter.return_value.all.return_value = []
        mock_db_session.query.return_value.filter.return_value.scalar.return_value = 0

        balance = get_credit_balance(tenant_id, mock_db_session)

        assert balance.credit_balance == Decimal("50.00")
        assert balance.monthly_spending_limit == Decimal("200.00")

    def test_counts_active_packages(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        from lintpdf.ai.credits import get_credit_balance

        # Create mock credit packages
        pkg_active = MagicMock()
        pkg_active.credits_remaining = 50
        pkg_active.expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        pkg_expired = MagicMock()
        pkg_expired.credits_remaining = 25
        pkg_expired.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

        pkg_no_expiry = MagicMock()
        pkg_no_expiry.credits_remaining = 100
        pkg_no_expiry.expires_at = None

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        mock_db_session.query.return_value.filter.return_value.all.return_value = [
            pkg_active,
            pkg_expired,
            pkg_no_expiry,
        ]
        mock_db_session.query.return_value.filter.return_value.scalar.return_value = 0

        balance = get_credit_balance(tenant_id, mock_db_session)

        # Expired package should be excluded
        assert balance.packages_active == 2
        assert balance.package_credits_remaining == 150


class TestCheckAICredits:
    """Tests for check_ai_credits (raises 402 when insufficient)."""

    @staticmethod
    def test_raises_402_when_no_config(mock_db_session: MagicMock, tenant_id) -> None:
        from lintpdf.ai.credits import check_ai_credits

        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            check_ai_credits(tenant_id, 5, mock_db_session)
        assert exc_info.value.status_code == 402
        assert "not configured" in exc_info.value.detail

    def test_passes_with_sufficient_package_credits(
        self, mock_db_session: MagicMock, tenant_id
    ) -> None:
        from lintpdf.ai.credits import check_ai_credits

        config = MagicMock()
        config.billing_mode = "credit_package"

        # First call -> config, second call chain -> balance
        mock_db_session.query.return_value.filter.return_value.first.return_value = config
        mock_db_session.query.return_value.filter.return_value.all.return_value = []
        mock_db_session.query.return_value.filter.return_value.scalar.return_value = 0

        # Patch get_credit_balance to return sufficient credits
        with patch("lintpdf.ai.credits.get_credit_balance") as mock_balance:
            mock_balance.return_value = MagicMock(package_credits_remaining=100)
            check_ai_credits(tenant_id, 5, mock_db_session)  # Should not raise

    def test_raises_402_with_insufficient_package_credits(
        self, mock_db_session: MagicMock, tenant_id
    ) -> None:
        from lintpdf.ai.credits import check_ai_credits

        config = MagicMock()
        config.billing_mode = "credit_package"
        mock_db_session.query.return_value.filter.return_value.first.return_value = config

        with patch("lintpdf.ai.credits.get_credit_balance") as mock_balance:
            mock_balance.return_value = MagicMock(package_credits_remaining=2)
            with pytest.raises(HTTPException) as exc_info:
                check_ai_credits(tenant_id, 10, mock_db_session)
            assert exc_info.value.status_code == 402
            assert "Insufficient" in exc_info.value.detail

    @staticmethod
    def test_passes_pay_per_use_under_limit(mock_db_session: MagicMock, tenant_id) -> None:
        from lintpdf.ai.credits import check_ai_credits

        config = MagicMock()
        config.billing_mode = "pay_per_use"
        config.monthly_spending_limit = Decimal("100.00")
        config.overage_rate = Decimal("0.10")
        mock_db_session.query.return_value.filter.return_value.first.return_value = config

        with patch("lintpdf.ai.credits.get_credit_balance") as mock_balance:
            mock_balance.return_value = MagicMock(
                monthly_spent=Decimal("10.00"),
                monthly_spending_limit=Decimal("100.00"),
            )
            check_ai_credits(tenant_id, 5, mock_db_session)  # Should not raise

    @staticmethod
    def test_raises_402_pay_per_use_over_limit(mock_db_session: MagicMock, tenant_id) -> None:
        from lintpdf.ai.credits import check_ai_credits

        config = MagicMock()
        config.billing_mode = "pay_per_use"
        config.monthly_spending_limit = Decimal("10.00")
        config.overage_rate = Decimal("1.00")
        mock_db_session.query.return_value.filter.return_value.first.return_value = config

        with patch("lintpdf.ai.credits.get_credit_balance") as mock_balance:
            mock_balance.return_value = MagicMock(
                monthly_spent=Decimal("8.00"),
                monthly_spending_limit=Decimal("10.00"),
            )
            with pytest.raises(HTTPException) as exc_info:
                check_ai_credits(tenant_id, 5, mock_db_session)
            assert exc_info.value.status_code == 402
            assert "spending limit" in exc_info.value.detail

    @staticmethod
    def test_passes_pay_per_use_no_limit(mock_db_session: MagicMock, tenant_id) -> None:
        """Pay-per-use with no spending limit should always pass."""
        from lintpdf.ai.credits import check_ai_credits

        config = MagicMock()
        config.billing_mode = "pay_per_use"
        config.monthly_spending_limit = None
        mock_db_session.query.return_value.filter.return_value.first.return_value = config

        check_ai_credits(tenant_id, 100, mock_db_session)  # Should not raise


class TestDeductCredits:
    """Tests for deduct_credits."""

    @staticmethod
    def test_deduct_from_oldest_package_first(mock_db_session: MagicMock, tenant_id) -> None:
        from lintpdf.ai.credits import deduct_credits

        config = MagicMock()
        config.billing_mode = "credit_package"
        mock_db_session.query.return_value.filter.return_value.first.return_value = config

        # Two packages: older one should be deducted first
        pkg_old = MagicMock()
        pkg_old.credits_remaining = 3
        pkg_old.purchased_at = datetime.now(timezone.utc) - timedelta(days=30)
        pkg_old.expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        pkg_new = MagicMock()
        pkg_new.credits_remaining = 10
        pkg_new.purchased_at = datetime.now(timezone.utc) - timedelta(days=1)
        pkg_new.expires_at = datetime.now(timezone.utc) + timedelta(days=60)

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            pkg_old,
            pkg_new,
        ]

        job_id = uuid.uuid4()
        deduct_credits(
            tenant_id,
            job_id,
            category="barcode",
            feature="barcode_decode",
            credit_amount=5,
            processing_time_ms=100,
            result_summary=None,
            db=mock_db_session,
        )

        # Old package should be fully depleted, then 2 from new
        assert pkg_old.credits_remaining == 0
        assert pkg_new.credits_remaining == 8
        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @staticmethod
    def test_skips_expired_packages(mock_db_session: MagicMock, tenant_id) -> None:
        from lintpdf.ai.credits import deduct_credits

        config = MagicMock()
        config.billing_mode = "credit_package"
        mock_db_session.query.return_value.filter.return_value.first.return_value = config

        pkg_expired = MagicMock()
        pkg_expired.credits_remaining = 50
        pkg_expired.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

        pkg_valid = MagicMock()
        pkg_valid.credits_remaining = 10
        pkg_valid.expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            pkg_expired,
            pkg_valid,
        ]

        job_id = uuid.uuid4()
        deduct_credits(
            tenant_id,
            job_id,
            category="barcode",
            feature="barcode_decode",
            credit_amount=5,
            processing_time_ms=50,
            result_summary=None,
            db=mock_db_session,
        )

        # Expired package should not be touched
        assert pkg_expired.credits_remaining == 50
        assert pkg_valid.credits_remaining == 5

    @staticmethod
    def test_pay_per_use_logs_cost(mock_db_session: MagicMock, tenant_id) -> None:
        from lintpdf.ai.credits import deduct_credits

        config = MagicMock()
        config.billing_mode = "pay_per_use"
        config.overage_rate = Decimal("0.10")
        mock_db_session.query.return_value.filter.return_value.first.return_value = config

        job_id = uuid.uuid4()
        deduct_credits(
            tenant_id,
            job_id,
            category="barcode",
            feature="barcode_decode",
            credit_amount=5,
            processing_time_ms=100,
            result_summary={"barcodes_found": 2},
            db=mock_db_session,
        )

        mock_db_session.add.assert_called_once()
        usage_log = mock_db_session.add.call_args[0][0]
        assert usage_log.credits_consumed == 5
        assert usage_log.cost == Decimal("0.50")

    def test_no_config_logs_warning_and_returns(
        self, mock_db_session: MagicMock, tenant_id
    ) -> None:
        from lintpdf.ai.credits import deduct_credits

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        job_id = uuid.uuid4()
        # Should not raise
        deduct_credits(
            tenant_id,
            job_id,
            category="barcode",
            feature="barcode_decode",
            credit_amount=5,
            processing_time_ms=100,
            result_summary=None,
            db=mock_db_session,
        )
        mock_db_session.add.assert_not_called()


class TestCheckSpendingLimit:
    """Edge cases for monthly spending limit enforcement."""

    @staticmethod
    def test_exact_limit_boundary(mock_db_session: MagicMock, tenant_id) -> None:
        """Spending exactly at the limit (but not over) should pass."""
        from lintpdf.ai.credits import check_ai_credits

        config = MagicMock()
        config.billing_mode = "pay_per_use"
        config.monthly_spending_limit = Decimal("10.00")
        config.overage_rate = Decimal("1.00")
        mock_db_session.query.return_value.filter.return_value.first.return_value = config

        with patch("lintpdf.ai.credits.get_credit_balance") as mock_balance:
            # Current spend 9.00 + estimated 1.00 = 10.00 exactly at limit
            mock_balance.return_value = MagicMock(
                monthly_spent=Decimal("9.00"),
                monthly_spending_limit=Decimal("10.00"),
            )
            check_ai_credits(tenant_id, 1, mock_db_session)  # Should not raise

    @staticmethod
    def test_one_cent_over_limit(mock_db_session: MagicMock, tenant_id) -> None:
        """Exceeding the limit by any amount should raise 402."""
        from lintpdf.ai.credits import check_ai_credits

        config = MagicMock()
        config.billing_mode = "pay_per_use"
        config.monthly_spending_limit = Decimal("10.00")
        config.overage_rate = Decimal("1.00")
        mock_db_session.query.return_value.filter.return_value.first.return_value = config

        with patch("lintpdf.ai.credits.get_credit_balance") as mock_balance:
            mock_balance.return_value = MagicMock(
                monthly_spent=Decimal("9.01"),
                monthly_spending_limit=Decimal("10.00"),
            )
            with pytest.raises(HTTPException) as exc_info:
                check_ai_credits(tenant_id, 2, mock_db_session)
            assert exc_info.value.status_code == 402
