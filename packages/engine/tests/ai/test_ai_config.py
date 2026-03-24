"""Tests for AI configuration service (lintpdf.ai.config)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.ai.config import (
    add_reference_logo,
    admin_update_ai_config,
    get_or_create_ai_config,
    remove_reference_logo,
    update_ai_config,
)

if TYPE_CHECKING:
    from unittest.mock import MagicMock


class TestGetOrCreateAIConfig:
    """Tests for get_or_create_ai_config."""

    def test_returns_existing_config(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        result = get_or_create_ai_config(tenant_id, mock_db_session)
        assert result is mock_ai_config
        mock_db_session.add.assert_not_called()

    def test_creates_default_config_when_missing(
        self, mock_db_session: MagicMock, tenant_id
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        get_or_create_ai_config(tenant_id, mock_db_session)

        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()
        # The added object should have been created with the given tenant_id
        added_obj = mock_db_session.add.call_args[0][0]
        assert added_obj.tenant_id == tenant_id


class TestUpdateAIConfig:
    """Tests for update_ai_config (self-service fields only)."""

    def test_updates_allowed_fields(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        updates = {
            "enabled_categories": ["barcode", "content_quality"],
            "industry_type": "packaging",
            "monthly_spending_limit": 500,
        }

        result = update_ai_config(tenant_id, updates, mock_db_session)

        assert result.enabled_categories == ["barcode", "content_quality"]
        assert result.industry_type == "packaging"
        assert result.monthly_spending_limit == 500

    def test_ignores_admin_only_fields(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_ai_config.ai_enabled = True
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        updates = {
            "ai_enabled": False,  # admin-only, should be ignored
            "billing_mode": "credit_package",  # admin-only
            "industry_type": "pharma",  # allowed
        }

        result = update_ai_config(tenant_id, updates, mock_db_session)

        # ai_enabled should not change
        assert result.ai_enabled is True
        assert result.industry_type == "pharma"

    def test_ignores_unknown_fields(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        result = update_ai_config(tenant_id, {"nonexistent_field": "value"}, mock_db_session)
        assert result is mock_ai_config

    def test_updates_brand_palette(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        palette = [
            {"name": "Brand Red", "value": "#FF0000"},
            {"name": "Brand Blue", "value": "#0000FF"},
        ]
        result = update_ai_config(tenant_id, {"brand_palette": palette}, mock_db_session)
        assert result.brand_palette == palette

    def test_updates_custom_dictionary(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        words = ["LintPDF", "preflight", "CMYK"]
        result = update_ai_config(tenant_id, {"custom_dictionary": words}, mock_db_session)
        assert result.custom_dictionary == words


class TestAdminUpdateAIConfig:
    """Tests for admin_update_ai_config."""

    def test_can_toggle_ai_enabled(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_ai_config.ai_enabled = False
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        result = admin_update_ai_config(tenant_id, {"ai_enabled": True}, mock_db_session)
        assert result.ai_enabled is True

    def test_can_change_billing_mode(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        result = admin_update_ai_config(
            tenant_id, {"billing_mode": "credit_package"}, mock_db_session
        )
        assert result.billing_mode == "credit_package"

    def test_can_set_trial(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        from datetime import UTC, datetime, timedelta

        expiry = datetime.now(UTC) + timedelta(days=14)
        result = admin_update_ai_config(
            tenant_id,
            {"trial_enabled": True, "trial_expires_at": expiry},
            mock_db_session,
        )
        assert result.trial_enabled is True
        assert result.trial_expires_at == expiry

    def test_ignores_non_admin_fields(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        result = admin_update_ai_config(
            tenant_id,
            {"industry_type": "food", "custom_dictionary": ["test"]},
            mock_db_session,
        )
        # These are self-service fields, not admin fields — should be ignored
        assert result.industry_type != "food"


class TestReferenceLogo:
    """Tests for add_reference_logo and remove_reference_logo."""

    def test_add_logo(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_ai_config.reference_logos = None
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        result = add_reference_logo(tenant_id, "Brand Logo", "logos/abc/xyz", mock_db_session)

        assert result["name"] == "Brand Logo"
        assert result["storage_key"] == "logos/abc/xyz"
        assert "id" in result
        assert len(mock_ai_config.reference_logos) == 1

    def test_add_second_logo(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_ai_config.reference_logos = [
            {"id": "existing-id", "name": "Old Logo", "storage_key": "logos/old"}
        ]
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        result = add_reference_logo(tenant_id, "New Logo", "logos/new", mock_db_session)

        assert len(mock_ai_config.reference_logos) == 2
        assert result["name"] == "New Logo"

    def test_remove_logo_success(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        logo_id = "test-logo-id"
        mock_ai_config.reference_logos = [
            {"id": logo_id, "name": "Test Logo", "storage_key": "logos/test"},
            {"id": "other-id", "name": "Other Logo", "storage_key": "logos/other"},
        ]
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config

        result = remove_reference_logo(tenant_id, logo_id, mock_db_session)
        assert result is True
        assert len(mock_ai_config.reference_logos) == 1
        assert mock_ai_config.reference_logos[0]["id"] == "other-id"

    def test_remove_logo_not_found(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_ai_config.reference_logos = [
            {"id": "some-id", "name": "Logo", "storage_key": "logos/x"},
        ]
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        result = remove_reference_logo(tenant_id, "nonexistent-id", mock_db_session)
        assert result is False

    def test_remove_logo_empty_list(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_ai_config.reference_logos = None
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        result = remove_reference_logo(tenant_id, "any-id", mock_db_session)
        assert result is False
