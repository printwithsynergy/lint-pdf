"""Tests for AI API routes (config, credits, presets).

These tests mock the FastAPI dependency injection layer and verify
that route functions call the correct service methods and return
the expected response shapes.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


class TestAIConfigRoutes:
    """Tests for /api/v1/ai/config routes."""

    @pytest.mark.asyncio
    async def test_get_ai_config(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
        mock_ai_config: MagicMock,
    ) -> None:
        from siftpdf.api.routes.ai_config import get_ai_config

        with patch(
            "siftpdf.ai.config.get_or_create_ai_config",
            return_value=mock_ai_config,
        ):
            response = await get_ai_config(db=mock_db_session, tenant=mock_tenant)

        assert response.ai_enabled == mock_ai_config.ai_enabled
        assert response.credit_balance == mock_ai_config.credit_balance

    @pytest.mark.asyncio
    async def test_update_ai_config(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
        mock_ai_config: MagicMock,
    ) -> None:
        from siftpdf.api.ai_schemas import AIConfigUpdateRequest
        from siftpdf.api.routes.ai_config import update_ai_config

        request = AIConfigUpdateRequest(industry_type="pharma")

        with (
            patch("siftpdf.ai.access.check_ai_access", return_value=mock_ai_config),
            patch(
                "siftpdf.ai.config.update_ai_config",
                return_value=mock_ai_config,
            ),
        ):
            response = await update_ai_config(
                request=request, db=mock_db_session, tenant=mock_tenant
            )

        assert response.ai_enabled == mock_ai_config.ai_enabled

    @pytest.mark.asyncio
    async def test_update_ai_config_requires_access(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        from siftpdf.api.ai_schemas import AIConfigUpdateRequest
        from siftpdf.api.routes.ai_config import update_ai_config

        request = AIConfigUpdateRequest(industry_type="food")

        with patch(
            "siftpdf.ai.access.check_ai_access",
            side_effect=HTTPException(status_code=403, detail="AI not enabled"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_ai_config(request=request, db=mock_db_session, tenant=mock_tenant)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_logo_not_found(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
        mock_ai_config: MagicMock,
    ) -> None:
        from siftpdf.api.routes.ai_config import delete_reference_logo

        with (
            patch("siftpdf.ai.access.check_ai_access", return_value=mock_ai_config),
            patch("siftpdf.ai.config.remove_reference_logo", return_value=False),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_reference_logo(
                    logo_id="nonexistent", db=mock_db_session, tenant=mock_tenant
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_logo_success(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
        mock_ai_config: MagicMock,
    ) -> None:
        from siftpdf.api.routes.ai_config import delete_reference_logo

        with (
            patch("siftpdf.ai.access.check_ai_access", return_value=mock_ai_config),
            patch("siftpdf.ai.config.remove_reference_logo", return_value=True),
        ):
            result = await delete_reference_logo(
                logo_id="test-logo-id", db=mock_db_session, tenant=mock_tenant
            )
            assert result is None  # 204 No Content

    @pytest.mark.asyncio
    async def test_set_brand_palette(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
        mock_ai_config: MagicMock,
    ) -> None:
        from siftpdf.api.ai_schemas import PaletteUpdateRequest
        from siftpdf.api.routes.ai_config import set_brand_palette

        request = PaletteUpdateRequest(
            colors=[
                {"name": "Red", "value": "#FF0000"},
                {"name": "Blue", "value": "#0000FF"},
            ]
        )

        with (
            patch("siftpdf.ai.access.check_ai_access", return_value=mock_ai_config),
            patch("siftpdf.ai.config.update_ai_config", return_value=mock_ai_config),
        ):
            result = await set_brand_palette(
                request=request, db=mock_db_session, tenant=mock_tenant
            )
            assert result["colors"] == 2

    @pytest.mark.asyncio
    async def test_set_custom_dictionary(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
        mock_ai_config: MagicMock,
    ) -> None:
        from siftpdf.api.ai_schemas import DictionaryUpdateRequest
        from siftpdf.api.routes.ai_config import set_custom_dictionary

        request = DictionaryUpdateRequest(words=["LintPDF", "CMYK", "preflight"])

        with (
            patch("siftpdf.ai.access.check_ai_access", return_value=mock_ai_config),
            patch("siftpdf.ai.config.update_ai_config", return_value=mock_ai_config),
        ):
            result = await set_custom_dictionary(
                request=request, db=mock_db_session, tenant=mock_tenant
            )
            assert result["words"] == 3


class TestAICreditRoutes:
    """Tests for /api/v1/ai/credits routes."""

    @pytest.mark.asyncio
    async def test_get_credits(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
        mock_ai_config: MagicMock,
    ) -> None:
        from siftpdf.ai.credits import CreditBalance
        from siftpdf.api.routes.ai_credits import get_credits

        balance = CreditBalance(
            credit_balance=Decimal("100.00"),
            billing_mode="pay_per_use",
            packages_active=1,
            package_credits_remaining=50,
            monthly_spent=Decimal("25.00"),
            monthly_spending_limit=Decimal("200.00"),
        )

        with (
            patch("siftpdf.ai.access.check_ai_access", return_value=mock_ai_config),
            patch("siftpdf.ai.credits.get_credit_balance", return_value=balance),
        ):
            response = await get_credits(db=mock_db_session, tenant=mock_tenant)

        assert response.credit_balance == Decimal("100.00")
        assert response.packages_active == 1
        assert response.monthly_spent == Decimal("25.00")

    @pytest.mark.asyncio
    async def test_topup_credits(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
        mock_ai_config: MagicMock,
    ) -> None:
        from siftpdf.api.ai_schemas import CreditTopupRequest
        from siftpdf.api.routes.ai_credits import topup_credits

        # The route now creates a Stripe Checkout session and returns the
        # checkout_url / session_id; the package row is inserted by the
        # checkout.session.completed webhook handler, not by this endpoint.
        request = CreditTopupRequest(pack="500")

        mock_pack_def = MagicMock()
        mock_pack_def.usd_cents = 5000
        mock_session = {
            "url": "https://checkout.stripe.com/c/pay/cs_test_abc123",
            "id": "cs_test_abc123",
        }

        with (
            patch("siftpdf.ai.access.check_ai_access", return_value=mock_ai_config),
            patch("siftpdf.billing.metered_packs.pack_for_size", return_value=mock_pack_def),
            patch("siftpdf.billing.metered_packs.resolve_price_id", return_value="price_test_500"),
            patch(
                "siftpdf.billing.stripe_client.load_config", return_value=MagicMock(sandbox=True)
            ),
            patch(
                "siftpdf.billing.stripe_client.create_checkout_session",
                return_value=mock_session,
            ),
        ):
            response = await topup_credits(request=request, db=mock_db_session, tenant=mock_tenant)

        assert response.checkout_url == mock_session["url"]
        assert response.session_id == mock_session["id"]
        assert response.pack_size == 500
        assert response.usd_cents == 5000

    @pytest.mark.asyncio
    async def test_get_credits_requires_access(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        from siftpdf.api.routes.ai_credits import get_credits

        with patch(
            "siftpdf.ai.access.check_ai_access",
            side_effect=HTTPException(status_code=403, detail="No access"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_credits(db=mock_db_session, tenant=mock_tenant)
            assert exc_info.value.status_code == 403


class TestAIPresetRoutes:
    """Tests for /api/v1/ai/presets routes."""

    @pytest.mark.asyncio
    async def test_list_presets(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        from siftpdf.api.routes.ai_presets import list_presets

        response = await list_presets(db=mock_db_session, tenant=mock_tenant)

        assert len(response.presets) == 7
        slugs = {p.slug for p in response.presets}
        assert "full-ai-scan" in slugs
        assert "packaging-qc" in slugs

    @pytest.mark.asyncio
    async def test_get_preset_found(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        from siftpdf.api.routes.ai_presets import get_preset

        response = await get_preset(slug="fda-food-label", db=mock_db_session, tenant=mock_tenant)
        assert response.slug == "fda-food-label"
        assert response.name == "FDA Food Label"
        assert len(response.features) > 0

    @pytest.mark.asyncio
    async def test_get_preset_not_found(
        self,
        mock_db_session: MagicMock,
        mock_tenant: MagicMock,
    ) -> None:
        from siftpdf.api.routes.ai_presets import get_preset

        with pytest.raises(HTTPException) as exc_info:
            await get_preset(slug="nonexistent-preset", db=mock_db_session, tenant=mock_tenant)
        assert exc_info.value.status_code == 404
