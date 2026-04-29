"""Service protocols — the SaaS-facing edge of the plugin contract.

Every concrete coupling between an analyzer and a SaaS module
(`lintpdf.audit.metering`, `lintpdf.ai.cost_cap`, `lintpdf.ai.gpu_client`,
etc.) goes through one of these Protocols. Plugins read services via
``ctx.services.<name>`` rather than importing SaaS modules directly.

OSS-mode hosts (post-Phase-3 SiftPDF) construct a ``Services`` instance
with no-op stubs for SaaS-only services (metering, cost_cap, tenants).
The hosted LintPDF SaaS uses ``host.default_services_for_saas()`` which
wraps the existing concrete modules.

Each Protocol is intentionally narrow: it captures only the methods analyzers
actually call. Phase 2 will widen them as needed when the legacy ``analyze()``
path is deleted; Phase 1 keeps both paths working.
"""

from __future__ import annotations

from typing import Any, Protocol


class MeteringService(Protocol):
    """Records AI usage events for billing / analytics."""

    def record_usage(
        self,
        *,
        tenant_id: str,
        feature_slug: str,
        units: int,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...


class CostCapService(Protocol):
    """Enforces per-tenant cost caps on AI features."""

    def check_or_raise(
        self,
        *,
        tenant_id: str,
        feature_slug: str,
        estimated_units: int,
    ) -> None: ...


class GPUClient(Protocol):
    """Abstract handle for the GPU inference sidecar."""

    def detect_outlines(
        self,
        *,
        pdf_bytes: bytes,
        page_num: int,
        dpi: int,
    ) -> list[dict[str, Any]]: ...


class LLMClient(Protocol):
    """Anthropic / OpenAI-style chat completion for AI analyzers."""

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str: ...


class Renderer(Protocol):
    """Rasterises PDF pages to images for AI analyzers."""

    def render_page(
        self,
        *,
        pdf_bytes: bytes,
        page_num: int,
        dpi: int,
    ) -> bytes: ...


class VeraPDFClient(Protocol):
    """veraPDF sidecar handle. OSS stub emits a single advisory."""

    def is_configured(self) -> bool: ...

    def validate(
        self,
        *,
        pdf_bytes: bytes,
        profile: str,
    ) -> dict[str, Any]: ...


class DatabaseService(Protocol):
    """Opaque session factory for plugins that read SaaS-side state."""

    def session(self) -> Any: ...


class TenantsService(Protocol):
    """Tenant config / entitlements lookup."""

    def get_ai_config(self, tenant_id: str) -> dict[str, Any] | None: ...

    def get_entitlements(self, tenant_id: str) -> dict[str, Any]: ...


class Services(Protocol):
    """Aggregate service surface exposed to plugins via ``ctx.services``.

    Plugins read attributes lazily — accessing ``ctx.services.metering`` on
    a Services-with-noop-metering returns a stub whose ``record_usage`` is
    a no-op. This lets the same plugin run hosted (with metering on) and
    OSS (with metering skipped) without conditional imports.
    """

    metering: MeteringService
    cost_cap: CostCapService
    gpu_client: GPUClient
    llm_client: LLMClient
    renderer: Renderer
    verapdf_client: VeraPDFClient
    database: DatabaseService
    tenants: TenantsService


# ---------------------------------------------------------------------------
# OSS / no-op stubs
# ---------------------------------------------------------------------------


class _NoOpMetering:
    def record_usage(self, **_: Any) -> None:
        return None


class _NoOpCostCap:
    def check_or_raise(self, **_: Any) -> None:
        return None


class _NoOpVeraPDF:
    def is_configured(self) -> bool:
        return False

    def validate(self, **_: Any) -> dict[str, Any]:
        return {
            "status": "skipped",
            "advisory": "PDF/A validation skipped — veraPDF service not configured.",
        }


class _NoOpTenants:
    def get_ai_config(self, _tenant_id: str) -> dict[str, Any] | None:
        return None

    def get_entitlements(self, _tenant_id: str) -> dict[str, Any]:
        return {}


def noop_metering() -> MeteringService:
    """Return a metering stub that records nothing. Safe for OSS hosts."""

    return _NoOpMetering()


def noop_cost_cap() -> CostCapService:
    """Return a cost-cap stub that always allows. Safe for OSS hosts."""

    return _NoOpCostCap()


def noop_verapdf() -> VeraPDFClient:
    """Return a veraPDF stub that emits a single skipped advisory."""

    return _NoOpVeraPDF()


def noop_tenants() -> TenantsService:
    """Return a tenants stub that reports no AI config and no entitlements."""

    return _NoOpTenants()
