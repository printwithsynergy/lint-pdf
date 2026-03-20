"""Tests for AI access control (grounded.ai.access)."""

from __future__ import annotations

from typing import TYPE_CHECKING

# skipcq: PYL-R0201
import pytest
from fastapi import HTTPException

from grounded.ai.access import (
    check_ai_access,
    check_ai_category_access,
    get_ai_config,
    is_ai_available,
)

if TYPE_CHECKING:
    from unittest.mock import MagicMock


class TestGetAIConfig:
    """Tests for get_ai_config helper."""

    def test_returns_config_when_present(
        self, mock_db_session: MagicMock, mock_ai_config: MagicMock, tenant_id
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        result = get_ai_config(tenant_id, mock_db_session)
        assert result is mock_ai_config

    def test_returns_none_when_not_configured(self, mock_db_session: MagicMock, tenant_id) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        result = get_ai_config(tenant_id, mock_db_session)
        assert result is None


class TestCheckAIAccess:
    """Tests for check_ai_access (raises 403 when AI not available)."""

    def test_returns_config_when_enabled(
        self, mock_tenant: MagicMock, mock_db_session: MagicMock, mock_ai_config: MagicMock
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        result = check_ai_access(mock_tenant, mock_db_session)
        assert result is mock_ai_config

    def test_raises_403_when_config_missing(
        self, mock_tenant: MagicMock, mock_db_session: MagicMock
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            check_ai_access(mock_tenant, mock_db_session)
        assert exc_info.value.status_code == 403
        assert "not enabled" in exc_info.value.detail

    def test_raises_403_when_disabled(
        self,
        mock_tenant: MagicMock,
        mock_db_session: MagicMock,
        mock_ai_config_disabled: MagicMock,
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_ai_config_disabled
        )
        with pytest.raises(HTTPException) as exc_info:
            check_ai_access(mock_tenant, mock_db_session)
        assert exc_info.value.status_code == 403

    def test_raises_403_when_trial_expired(
        self,
        mock_tenant: MagicMock,
        mock_db_session: MagicMock,
        mock_ai_config_trial_expired: MagicMock,
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_ai_config_trial_expired
        )
        with pytest.raises(HTTPException) as exc_info:
            check_ai_access(mock_tenant, mock_db_session)
        assert exc_info.value.status_code == 403
        assert "trial has expired" in exc_info.value.detail

    def test_passes_when_trial_active(
        self,
        mock_tenant: MagicMock,
        mock_db_session: MagicMock,
        mock_ai_config_trial_active: MagicMock,
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_ai_config_trial_active
        )
        result = check_ai_access(mock_tenant, mock_db_session)
        assert result is mock_ai_config_trial_active

    def test_passes_when_trial_enabled_but_no_expiry_set(
        self, mock_tenant: MagicMock, mock_db_session: MagicMock, tenant_id
    ) -> None:
        """Trial with no expiration date should still pass."""
        from tests.ai.conftest import _make_ai_config

        config = _make_ai_config(tenant_id, trial_enabled=True, trial_expires_at=None)
        mock_db_session.query.return_value.filter.return_value.first.return_value = config
        result = check_ai_access(mock_tenant, mock_db_session)
        assert result is config


class TestIsAIAvailable:
    """Tests for is_ai_available (non-throwing boolean check)."""

    def test_true_when_enabled(
        self,
        mock_tenant: MagicMock,
        mock_db_session: MagicMock,
        mock_ai_config: MagicMock,
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_ai_config
        assert is_ai_available(mock_tenant, mock_db_session) is True

    def test_false_when_no_config(self, mock_tenant: MagicMock, mock_db_session: MagicMock) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        assert is_ai_available(mock_tenant, mock_db_session) is False

    def test_false_when_disabled(
        self,
        mock_tenant: MagicMock,
        mock_db_session: MagicMock,
        mock_ai_config_disabled: MagicMock,
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_ai_config_disabled
        )
        assert is_ai_available(mock_tenant, mock_db_session) is False

    def test_false_when_trial_expired(
        self,
        mock_tenant: MagicMock,
        mock_db_session: MagicMock,
        mock_ai_config_trial_expired: MagicMock,
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_ai_config_trial_expired
        )
        assert is_ai_available(mock_tenant, mock_db_session) is False

    def test_true_when_trial_active(
        self,
        mock_tenant: MagicMock,
        mock_db_session: MagicMock,
        mock_ai_config_trial_active: MagicMock,
    ) -> None:
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            mock_ai_config_trial_active
        )
        assert is_ai_available(mock_tenant, mock_db_session) is True


class TestCheckAICategoryAccess:
    """Tests for check_ai_category_access."""

    def test_passes_when_all_categories_enabled(self, mock_ai_config: MagicMock) -> None:
        """Config with enabled_categories=["all"] allows everything."""
        mock_ai_config.enabled_categories = ["all"]
        check_ai_category_access(mock_ai_config, ["barcode", "content_quality"])

    def test_passes_for_enabled_category(self, mock_ai_config_categories: MagicMock) -> None:
        check_ai_category_access(mock_ai_config_categories, ["barcode"])

    def test_raises_403_for_disabled_category(self, mock_ai_config_categories: MagicMock) -> None:
        with pytest.raises(HTTPException) as exc_info:
            check_ai_category_access(mock_ai_config_categories, ["logo_verification"])
        assert exc_info.value.status_code == 403
        assert "logo_verification" in exc_info.value.detail

    def test_raises_403_when_no_categories_enabled(
        self, mock_ai_config_no_categories: MagicMock
    ) -> None:
        with pytest.raises(HTTPException) as exc_info:
            check_ai_category_access(mock_ai_config_no_categories, ["barcode"])
        assert exc_info.value.status_code == 403
        assert "No AI categories" in exc_info.value.detail

    def test_category_all_in_request_is_ignored(self, mock_ai_config_categories: MagicMock) -> None:
        """Requesting category "all" should be silently skipped."""
        check_ai_category_access(mock_ai_config_categories, ["all", "barcode"])

    def test_mixed_valid_and_invalid_raises(self, mock_ai_config_categories: MagicMock) -> None:
        with pytest.raises(HTTPException) as exc_info:
            check_ai_category_access(mock_ai_config_categories, ["barcode", "logo_verification"])
        assert exc_info.value.status_code == 403
