"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """LintPDF API configuration.

    All values can be overridden via environment variables.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="LINTPDF_")

    # Database
    database_url: str = "postgresql://localhost:5432/lintpdf"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # veraPDF sidecar
    verapdf_url: str = "http://localhost:8080"

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Auth
    secret_key: str = "change-me-in-production"

    # Upload limits
    max_upload_size_mb: int = 1024

    # Email (Resend)
    resend_api_key: str | None = None
    email_from_address: str = "LintPDF <noreply@thinkneverland.com>"

    # S3-compatible storage (Cloudflare R2)
    s3_endpoint_url: str | None = None
    s3_bucket_name: str = "lintpdf-uploads"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str = "auto"

    # Report hosting
    report_base_url: str = "https://reports.lintpdf.com"

    # Admin
    admin_api_key: str = ""

    # Dev auth (impersonation endpoint)
    dev_auth_enabled: bool = False

    # GPU inference service URL (required for AI features — set LINTPDF_GPU_INFERENCE_URL)
    gpu_inference_url: str = ""

    # ClamAV malware scanning — REQUIRED: uploads fail-closed if unset or unreachable.
    # Format: "host:port" (e.g. "clamd:3310"). Set via LINTPDF_CLAMAV_URL.
    clamav_url: str | None = None

    # Trial upload secret (shared with marketing site)
    trial_secret: str = ""

    # Trial: auto-queue preflight on submission instead of waiting for admin action.
    # When false (default), submissions sit in PENDING until an admin clicks "Run Preflight".
    # When true, preflight is queued immediately on submit; admin still sends the report.
    trial_auto_submit: bool = False
    trial_auto_submit_profile_id: str = "lintpdf-default"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


def get_settings() -> Settings:
    """Get cached settings instance."""
    import warnings

    settings = Settings()
    if settings.secret_key == "change-me-in-production":
        warnings.warn(
            "Using default LINTPDF_SECRET_KEY — set a strong random value in production",
            stacklevel=2,
        )
    return settings
