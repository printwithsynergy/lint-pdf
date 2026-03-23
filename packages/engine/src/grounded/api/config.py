"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """LintPDF API configuration.

    All values can be overridden via environment variables.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="GROUNDED_")

    # Database (required — set GROUNDED_DATABASE_URL)
    database_url: str

    # Redis (required — set GROUNDED_REDIS_URL)
    redis_url: str

    # veraPDF sidecar (required — set GROUNDED_VERAPDF_URL)
    verapdf_url: str

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Auth (required — set GROUNDED_SECRET_KEY to a strong random value)
    secret_key: str

    # Upload limits
    max_upload_size_mb: int = 1024

    # Email (Resend)
    resend_api_key: str | None = None
    email_from_address: str = "LintPDF <noreply@thinkneverland.com>"

    # S3-compatible storage (Cloudflare R2)
    s3_endpoint_url: str | None = None
    s3_bucket_name: str = "grounded-uploads"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str = "auto"

    # Report hosting
    report_base_url: str = "https://reports.lintpdf.com"

    # Admin
    admin_api_key: str = ""

    # Dev auth (impersonation endpoint)
    dev_auth_enabled: bool = False

    # GPU inference service URL (required for AI features — set GROUNDED_GPU_INFERENCE_URL)
    gpu_inference_url: str = ""

    # ClamAV malware scanning (optional — set to enable virus scanning on uploads)
    clamav_url: str | None = None

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


def get_settings() -> Settings:
    """Get cached settings instance.

    Raises ``ValidationError`` if required environment variables are missing.
    """
    return Settings()
