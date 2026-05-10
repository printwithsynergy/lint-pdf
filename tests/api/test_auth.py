"""Tests for authentication utilities."""

from __future__ import annotations

import pytest

from lintpdf.api.auth import (
    _OSS_OPEN_TENANT,
    generate_api_key,
    get_current_tenant,
    get_optional_tenant,
    hash_api_key,
)
from lintpdf.api.config import get_settings


class TestApiKeyGeneration:
    @staticmethod
    def test_generate_api_key_format() -> None:
        key = generate_api_key()
        assert key.startswith("lpdf_")
        assert len(key) > 10

    @staticmethod
    def test_generate_unique_keys() -> None:
        keys = {generate_api_key() for _ in range(10)}
        assert len(keys) == 10  # All unique

    @staticmethod
    def test_hash_api_key_deterministic() -> None:
        key = "lpdf_test_key_123"
        assert hash_api_key(key) == hash_api_key(key)

    @staticmethod
    def test_hash_api_key_different_for_different_keys() -> None:
        assert hash_api_key("key_a") != hash_api_key("key_b")

    @staticmethod
    def test_hash_api_key_is_hex() -> None:
        h = hash_api_key("test")
        assert len(h) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in h)


class TestAuthModeOpen:
    """``LINTPDF_AUTH_MODE=open`` bypasses API key checks and returns
    the OSS sentinel tenant. Used by self-hosters running the engine
    behind their own auth gateway, demo deployments where access is
    gated upstream, or local hacking."""

    @staticmethod
    @pytest.fixture(autouse=True)
    def _reset_settings_cache() -> None:
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_current_tenant_returns_sentinel_in_open_mode(
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("LINTPDF_AUTH_MODE", "open")
        get_settings.cache_clear()
        tenant = await get_current_tenant(authorization=None, db=None)  # type: ignore[arg-type]
        assert tenant is _OSS_OPEN_TENANT
        assert tenant.is_active is True
        assert tenant.plan == "oss"

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_optional_tenant_returns_sentinel_in_open_mode(
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("LINTPDF_AUTH_MODE", "open")
        get_settings.cache_clear()
        tenant = await get_optional_tenant(authorization=None, db=None)  # type: ignore[arg-type]
        assert tenant is _OSS_OPEN_TENANT
