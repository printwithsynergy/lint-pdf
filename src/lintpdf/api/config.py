"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

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

    # CORS — origins allowed to hit the HTTP API from a browser.
    # The marketing Swagger UI on https://lintpdf.com/swagger fetches
    # /openapi.tenant.json from here, and the dashboard at
    # https://app.lintpdf.com is a first-party SPA client; both need
    # Access-Control-Allow-Origin to be set. The engine uses bearer-
    # token auth (no cookies), so ``allow_credentials=False`` is safe
    # and the allowlist is the real access gate.
    #
    # Override via LINTPDF_CORS_ALLOW_ORIGINS="https://a.com,https://b.com".
    # Use "*" for a fully open API (not recommended for production).
    cors_allow_origins: str = "https://lintpdf.com,https://app.lintpdf.com"

    # Auth
    secret_key: str = "change-me-in-production"

    # Upload limits
    max_upload_size_mb: int = 1024

    # Upload stream chunk size (MB) — smaller values detect oversized uploads
    # sooner at the cost of more read() syscalls. 1 MB gives sub-second 413s
    # on multi-GB probes while keeping well-formed small uploads fast.
    max_upload_stream_chunk_mb: int = 1

    # Burst rate limit — per-tenant requests-per-minute ceiling. Enforced in
    # addition to the daily ``rate_limit_daily`` quota so a misbehaving
    # client can't exhaust a tenant's budget in 10 seconds. Set to 0 to
    # disable the burst check.
    burst_rate_per_minute: int = 100

    # Sync submit mode — maximum time a ``?wait=<seconds>`` / endpoint
    # ``response_mode=sync`` request is allowed to block on job completion
    # before the handler falls back to the 202 + job_id async response.
    # Client callers can request a shorter wait via ?wait=N but the
    # server-side ceiling still applies. Keep this well under the
    # frontend / edge proxy read timeout (Railway defaults ~300s) so a
    # slow job never produces a 502 mid-response. 120s comfortably covers
    # the p90 of an engine-mode preflight on a <50 MB PDF.
    sync_max_wait_s: float = 120.0

    # Email (Resend)
    resend_api_key: str | None = None
    email_from_address: str = "LintPDF <noreply@thinkneverland.com>"

    # S3-compatible storage (Cloudflare R2)
    s3_endpoint_url: str | None = None
    s3_bucket_name: str = "lintpdf-uploads"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str = "auto"

    # CDN tile delivery — when set, the viewer fetches pre-warmed tiles
    # directly from the R2 CDN instead of proxying through the engine.
    # Set to the base URL of the R2 custom domain (e.g. "https://cdn.lintpdf.com").
    tile_cdn_base_url: str | None = None

    # Report hosting
    #
    # The engine serves /r/{token} routes at this base URL. Default points at
    # reports.lintpdf.com, a dedicated Railway custom domain on the API service
    # (DNS: CNAME reports -> e3fo0e01.up.railway.app + TXT _railway-verify.reports,
    # both managed in the Hostinger zone for lintpdf.com). An earlier build used
    # https://api.lintpdf.com here as a temporary fallback while reports.lintpdf.com
    # was unconfigured; now that the subdomain has a CNAME + Railway cert we've
    # switched the primary hostname to reports.* so public report links no longer
    # collide with the API surface.
    #
    # Tenants with the whitelabel entitlement can override per-tenant (via
    # tenants.brand_custom_domain, gated on brand_custom_domain_verified) or
    # per-brand-profile (via brand_profiles.custom_domain); the override is
    # resolved by lintpdf.reports.service.resolve_report_base_url().
    report_base_url: str = "https://reports.lintpdf.com"

    # App base URL (Next.js dashboard).
    app_base_url: str = "https://app.lintpdf.com"

    # Hosted viewer handoff URL for interactive links emitted by engine
    # APIs/reports. Supports either:
    #   1) A direct token template, e.g. "https://app.example.com/view/{token}"
    #   2) A host page URL, e.g. "https://loupepdf.com/demo"
    #      (engine appends source=lintpdf&lintpdf_token=<token>).
    viewer_handoff_base_url: str = "https://loupepdf.com/demo"

    # Admin
    admin_api_key: str = ""

    # Auth mode for the tenant-scoped API surface.
    #
    # ``required`` (default) — every tenant-scoped route requires a valid
    # API key, dispatched through ``TenantContextService``.
    # ``open`` — bypass API key checks and inject a built-in OSS sentinel
    # tenant. Intended for self-hosters running the engine behind their
    # own auth gateway, demo deployments where access is gated upstream
    # (rate limiting + marketing-side AV), or local hacking.
    #
    # The hosted SaaS at lintpdf.com runs ``required``. The marketing
    # demo at lintpdf.com/demo runs ``open`` against the public engine
    # endpoint because the marketing app's /api/demo/upload route already
    # rate-limits, magic-byte-validates, and ClamAV-scans every upload
    # before it touches the engine.
    auth_mode: str = "required"

    # Dev auth (impersonation endpoint)
    dev_auth_enabled: bool = False

    # GPU inference service URL (required for AI features — set LINTPDF_GPU_INFERENCE_URL)
    gpu_inference_url: str = ""

    # ClamAV malware scanning.
    # Format: "host:port" (e.g. "clamd:3310"). Set via LINTPDF_CLAMAV_URL.
    # Default fail-open behavior (see scan_for_malware) is a deliberate
    # production choice — the upstream railway-clamav image ships with
    # a build-time config bug that breaks TCP listening. Once the
    # in-repo replacement at packages/engine/clamav/ is deployed and
    # verified, set ``LINTPDF_CLAMAV_REQUIRED=1`` to flip the upload
    # path to fail-closed (bulk-files step 16 — enterprise compliance).
    clamav_url: str | None = None
    clamav_required: bool = False

    # Trial upload secret (shared with marketing site)
    trial_secret: str = ""

    # Trial: auto-queue preflight on submission instead of waiting for admin action.
    # When false (default), submissions sit in PENDING until an admin clicks "Run Preflight".
    # When true, preflight is queued immediately on submit; admin still sends the report.
    trial_auto_submit: bool = False
    trial_auto_submit_profile_id: str = "lintpdf-default"

    # POST /reports feature gates.
    #   reports_inline_enabled — set to False to disable inline (JSON/XML
    #     in the response body) and force every request back to the
    #     URL-only flow. Used as a kill-switch if the new path regresses
    #     in production without needing a redeploy.
    #   reports_idempotency_enabled — when False the engine ignores the
    #     ``Idempotency-Key`` header and mints random tokens like it
    #     always did. Independent gate because the two features can
    #     regress independently.
    reports_inline_enabled: bool = True
    reports_idempotency_enabled: bool = True

    # Corpus testing — signing key for run certificates.
    # Set LINTPDF_CORPUS_SIGNING_KEY to a random value (≥32 bytes).
    # Rotated annually; old certificates remain verifiable only
    # against the key that signed them.  NULL disables certificate
    # issuance (runs still execute and diff, no signed artifact produced).
    corpus_signing_key: str | None = None

    # Codex unified-extraction feature flags.
    #
    # When the matching flag is on AND the CodexClient reports
    # is_enabled() == True, the orchestrator routes the work through
    # codex (text-region detection, veraPDF conformance, per-stage
    # telemetry capture) instead of the local pass / runner. Default
    # off so customer-facing output stays byte-identical until codex's
    # endpoint contract is verified in staging. Each flag is
    # independent — text-regions, conformance, and stage telemetry can
    # roll out one at a time.
    codex_text_regions_enabled: bool = False
    codex_conformance_enabled: bool = False
    codex_stage_telemetry_enabled: bool = False

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_upload_stream_chunk_bytes(self) -> int:
        return self.max_upload_stream_chunk_mb * 1024 * 1024


@lru_cache(maxsize=1)
def _cached_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    """Return the process-wide Settings singleton.

    The environment is immutable for the life of a production process,
    so computing the pydantic model once (instead of per call) removes a
    measurable amount of work from every route, Celery task, and CLI
    entry point. Under pytest the environment flips between tests (via
    ``monkeypatch.setenv``) so we bypass the cache when
    ``PYTEST_CURRENT_TEST`` is set, giving tests fresh values without
    requiring them to know about the cache.
    """
    import os
    import sys
    import warnings

    # `PYTEST_CURRENT_TEST` is set per-test by pytest; check that AND
    # whether the `pytest` module was imported, so the gate stays
    # bypassed for tests that legitimately clear the env var (e.g.
    # patch.dict('os.environ', {}, clear=True) or
    # monkeypatch.delenv('PYTEST_CURRENT_TEST')).
    in_test = bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules
    settings = Settings() if os.environ.get("PYTEST_CURRENT_TEST") else _cached_settings()

    if settings.secret_key == "change-me-in-production":
        # Hard-fail in production. The default value is a known string;
        # leaving it in place lets attackers forge any HMAC-signed
        # token (viewer JWTs, share-link tokens, etc.). Tests bypass
        # via PYTEST_CURRENT_TEST; local dev bypasses via
        # ``LINTPDF_ENVIRONMENT=development`` (or ``"staging"``).
        # Production deploys must set ``LINTPDF_SECRET_KEY`` to a
        # random value (≥32 bytes recommended).
        environment = os.environ.get("LINTPDF_ENVIRONMENT", "production").lower()
        if not in_test and environment == "production":
            raise RuntimeError(
                "LINTPDF_SECRET_KEY is unset (default 'change-me-in-production' "
                "would let attackers forge signed tokens). Set "
                "LINTPDF_SECRET_KEY to a random value before booting in "
                "production. To bypass for local dev, set "
                "LINTPDF_ENVIRONMENT=development (or 'staging')."
            )
        warnings.warn(
            "Using default LINTPDF_SECRET_KEY — set a strong random value in production",
            stacklevel=2,
        )
    return settings


# Backwards compat: older tests call ``get_settings.cache_clear()``.
get_settings.cache_clear = _cached_settings.cache_clear  # type: ignore[attr-defined]
