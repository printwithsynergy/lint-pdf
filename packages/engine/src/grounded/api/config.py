"""Application settings loaded from environment variables."""

from __future__ import annotations

import logging
import warnings

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Grounded API configuration.

    All values can be overridden via environment variables.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="GROUNDED_")

    # Database
    database_url: str = "postgresql://localhost:5432/grounded"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # veraPDF sidecar
    verapdf_url: str = "http://localhost:8080"

    # API server
    api_host: str = "0.0.0.0"  # skipcq: BAN-B104 — bind all interfaces for container deployments
    api_port: int = 8000

    # Auth
    secret_key: str = "change-me-in-production"

    # Upload limits
    max_upload_size_mb: int = 1024

    # Email (Resend)
    resend_api_key: str | None = None
    email_from_address: str = "Grounded <noreply@thinkneverland.com>"

    # S3-compatible storage (Cloudflare R2)
    s3_endpoint_url: str | None = None
    s3_bucket_name: str = "grounded-uploads"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str = "auto"

    # Report hosting
    report_base_url: str = "https://reports.grounded.dev"

    # Admin
    admin_api_key: str = ""

    # Dev auth (impersonation endpoint)
    dev_auth_enabled: bool = False

    # GPU inference service URL (for Tier 2 AI features)
    gpu_inference_url: str = "http://localhost:8001"

    # ClamAV malware scanning (optional — set to enable virus scanning on uploads)
    clamav_url: str | None = None

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


_INSECURE_DEFAULT_SECRET = "change-me-in-production"


def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()

    if settings.secret_key == _INSECURE_DEFAULT_SECRET:
        warnings.warn(
            "GROUNDED_SECRET_KEY is set to the insecure default. "
            "Set a strong secret via the GROUNDED_SECRET_KEY environment variable.",
            stacklevel=2,
        )
        logger.warning("INSECURE: Using default secret_key — set GROUNDED_SECRET_KEY")

    return settings
