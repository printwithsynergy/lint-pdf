"""Tests for API configuration."""

from __future__ import annotations

import pytest

from lintpdf.api.config import Settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove environment variables that would override Settings defaults.

    Settings uses the ``LINTPDF_`` prefix (via pydantic-settings), so both
    ``LINTPDF_*`` and any unprefixed variants must be cleared.
    """
    for suffix in [
        "DATABASE_URL",
        "REDIS_URL",
        "VERAPDF_URL",
        "API_HOST",
        "API_PORT",
        "SECRET_KEY",
        "MAX_UPLOAD_SIZE_MB",
        "S3_ENDPOINT_URL",
        "S3_BUCKET_NAME",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "S3_REGION",
        "REPORT_BASE_URL",
        "ADMIN_API_KEY",
        "BETA_MODE",
        "DEV_AUTH_ENABLED",
        "RESEND_API_KEY",
        "EMAIL_FROM_ADDRESS",
    ]:
        monkeypatch.delenv(f"LINTPDF_{suffix}", raising=False)
        monkeypatch.delenv(suffix, raising=False)


class TestSettings:
    @staticmethod
    def test_defaults() -> None:
        settings = Settings()
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.max_upload_size_mb == 1024
        assert settings.s3_bucket_name == "lintpdf-uploads"
        assert settings.redis_url == "redis://localhost:6379/0"

    @staticmethod
    def test_max_upload_size_bytes() -> None:
        settings = Settings(max_upload_size_mb=50)
        assert settings.max_upload_size_bytes == 50 * 1024 * 1024

    @staticmethod
    def test_s3_defaults() -> None:
        settings = Settings()
        assert settings.s3_endpoint_url is None
        assert settings.s3_access_key_id is None
        assert settings.s3_region == "auto"
