"""Tests for Settings loading from environment variables."""

from __future__ import annotations

# skipcq: PYL-R0201
import warnings
from unittest.mock import patch

from grounded.api.config import Settings, get_settings


class TestSettingsDefaults:
    """Tests for default Settings values."""

    def test_default_database_url(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.database_url == "postgresql://localhost:5432/grounded"

    def test_default_redis_url(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.redis_url == "redis://localhost:6379/0"

    def test_default_verapdf_url(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.verapdf_url == "http://localhost:8080"

    def test_default_api_host_and_port(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.api_host == "0.0.0.0"
            assert s.api_port == 8000

    def test_default_secret_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.secret_key == "change-me-in-production"

    def test_default_max_upload_size(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.max_upload_size_mb == 1024

    def test_default_email_settings(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.resend_api_key is None
            assert s.email_from_address == "Grounded <noreply@thinkneverland.com>"

    def test_default_s3_settings(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.s3_endpoint_url is None
            assert s.s3_bucket_name == "grounded-uploads"
            assert s.s3_access_key_id is None
            assert s.s3_secret_access_key is None
            assert s.s3_region == "auto"

    def test_default_report_base_url(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.report_base_url == "https://reports.grounded.dev"

    def test_default_admin_api_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.admin_api_key == ""

    def test_default_dev_auth_disabled(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.dev_auth_enabled is False


class TestSettingsFromEnvironment:
    """Tests for Settings loaded from env vars with GROUNDED_ prefix."""

    def test_database_url_from_env(self) -> None:
        with patch.dict("os.environ", {"GROUNDED_DATABASE_URL": "postgresql://prod:5432/live"}):
            s = Settings()
            assert s.database_url == "postgresql://prod:5432/live"

    def test_redis_url_from_env(self) -> None:
        with patch.dict("os.environ", {"GROUNDED_REDIS_URL": "redis://redis:6380/2"}):
            s = Settings()
            assert s.redis_url == "redis://redis:6380/2"

    def test_api_port_from_env(self) -> None:
        with patch.dict("os.environ", {"GROUNDED_API_PORT": "9000"}):
            s = Settings()
            assert s.api_port == 9000

    def test_secret_key_from_env(self) -> None:
        with patch.dict("os.environ", {"GROUNDED_SECRET_KEY": "super-secret-prod-key"}):
            s = Settings()
            assert s.secret_key == "super-secret-prod-key"

    def test_max_upload_size_from_env(self) -> None:
        with patch.dict("os.environ", {"GROUNDED_MAX_UPLOAD_SIZE_MB": "512"}):
            s = Settings()
            assert s.max_upload_size_mb == 512

    def test_resend_api_key_from_env(self) -> None:
        with patch.dict("os.environ", {"GROUNDED_RESEND_API_KEY": "re_test_abc"}):
            s = Settings()
            assert s.resend_api_key == "re_test_abc"

    def test_s3_settings_from_env(self) -> None:
        env = {
            "GROUNDED_S3_ENDPOINT_URL": "https://r2.example.com",
            "GROUNDED_S3_BUCKET_NAME": "my-bucket",
            "GROUNDED_S3_ACCESS_KEY_ID": "AKID123",
            "GROUNDED_S3_SECRET_ACCESS_KEY": "secret456",
            "GROUNDED_S3_REGION": "us-east-1",
        }
        with patch.dict("os.environ", env):
            s = Settings()
            assert s.s3_endpoint_url == "https://r2.example.com"
            assert s.s3_bucket_name == "my-bucket"
            assert s.s3_access_key_id == "AKID123"
            assert s.s3_secret_access_key == "secret456"
            assert s.s3_region == "us-east-1"

    def test_dev_auth_from_env(self) -> None:
        with patch.dict("os.environ", {"GROUNDED_DEV_AUTH_ENABLED": "true"}):
            s = Settings()
            assert s.dev_auth_enabled is True

    def test_report_base_url_from_env(self) -> None:
        with patch.dict("os.environ", {"GROUNDED_REPORT_BASE_URL": "https://custom.reports.com"}):
            s = Settings()
            assert s.report_base_url == "https://custom.reports.com"


class TestMaxUploadSizeBytes:
    """Tests for the max_upload_size_bytes computed property."""

    def test_converts_mb_to_bytes(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.max_upload_size_bytes == 1024 * 1024 * 1024  # 1024 MB

    def test_custom_size(self) -> None:
        with patch.dict("os.environ", {"GROUNDED_MAX_UPLOAD_SIZE_MB": "100"}):
            s = Settings()
            assert s.max_upload_size_bytes == 100 * 1024 * 1024

    def test_small_size(self) -> None:
        with patch.dict("os.environ", {"GROUNDED_MAX_UPLOAD_SIZE_MB": "1"}):
            s = Settings()
            assert s.max_upload_size_bytes == 1048576


class TestGetSettings:
    """Tests for the get_settings factory function."""

    def test_returns_settings_instance(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            s = get_settings()
            assert isinstance(s, Settings)

    def test_warns_on_default_secret(self) -> None:
        with patch.dict("os.environ", {}, clear=True), warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            get_settings()
            secret_warnings = [x for x in w if "GROUNDED_SECRET_KEY" in str(x.message)]
            assert len(secret_warnings) >= 1

    def test_no_warning_with_custom_secret(self) -> None:
        with (
            patch.dict("os.environ", {"GROUNDED_SECRET_KEY": "my-strong-secret"}),
            warnings.catch_warnings(record=True) as w,
        ):
            warnings.simplefilter("always")
            get_settings()
            secret_warnings = [x for x in w if "GROUNDED_SECRET_KEY" in str(x.message)]
            assert len(secret_warnings) == 0


class TestSettingsModelConfig:
    """Tests for pydantic model configuration."""

    def test_env_prefix(self) -> None:
        assert Settings.model_config.get("env_prefix") == "GROUNDED_"

    def test_env_file(self) -> None:
        assert Settings.model_config.get("env_file") == ".env"
