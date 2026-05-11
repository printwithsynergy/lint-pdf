"""Service protocols — the SaaS-facing edge of the plugin contract.

Every concrete coupling between an analyzer and a SaaS module
(`lintpdf.audit.metering`, `lintpdf.ai.cost_cap`, `lintpdf.ai.gpu_client`,
etc.) goes through one of these Protocols. Plugins read services via
``ctx.services.<name>`` rather than importing SaaS modules directly.

OSS-mode hosts (post-Phase-3 LintPDF) construct a ``Services`` instance
with no-op stubs for SaaS-only services (metering, cost_cap, tenants).
The hosted LintPDF SaaS uses ``host.default_services_for_saas()`` which
wraps the existing concrete modules.

Each Protocol is intentionally narrow: it captures only the methods analyzers
actually call. Phase 2 will widen them as needed when the legacy ``analyze()``
path is deleted; Phase 1 keeps both paths working.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from lintpdf.semantic.model import DetectedTextRegion


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
    """Abstract handle for the GPU inference sidecar.

    Phase 1 only declared ``detect_outlines``. Phase 2 widened the
    surface to include every method the migrated AI analyzers
    actually call (logos, NSFW, image quality, embeddings, generic
    object detection, document classification, regulatory symbols,
    translation). OSS hosts that ship without GPU access wire this
    slot to ``None`` and the analyzers self-skip per the
    service-skip pattern in ``engine/CLAUDE.md``.
    """

    def detect_outlines(
        self,
        *,
        pdf_bytes: bytes,
        page_num: int,
        dpi: int,
    ) -> list[dict[str, Any]]: ...

    def detect_logos(
        self,
        png_bytes: bytes,
        reference_embeddings: list[dict[str, Any]] | None = ...,
    ) -> dict[str, Any]: ...

    def detect_nsfw(self, png_bytes: bytes) -> dict[str, Any]: ...

    def assess_image_quality(self, png_bytes: bytes) -> dict[str, Any]: ...

    def embed_image(self, png_bytes: bytes) -> dict[str, Any]: ...

    def detect_objects(
        self,
        png_bytes: bytes,
        prompt: str,
    ) -> dict[str, Any]: ...

    def classify_document(self, png_bytes: bytes) -> dict[str, Any]: ...

    def detect_symbols(self, png_bytes: bytes) -> dict[str, Any]: ...

    def translate_text(
        self,
        *,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> dict[str, Any]: ...


class LLMClient(Protocol):
    """LLM completion service for analyzers that need vision /
    tool-use access (currently dieline_claude + legend_claude).

    Phase 2 ``complete(system, user, ...)`` was too narrow — those
    helpers need images, tool definitions, and ephemeral cache
    control. ``messages_create`` mirrors Anthropic's
    ``client.messages.create`` shape so the existing call sites
    migrate cleanly. OSS hosts can implement a translator (OpenAI
    Vision, local LLM) or wire the no-op stub and the analyzers
    will self-skip.
    """

    def messages_create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: list[dict[str, Any]] | str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
    ) -> Any: ...


class Renderer(Protocol):
    """Rasterises PDF pages to images for AI analyzers.

    Phase 2 widened beyond ``render_page`` to also expose the two
    raster helpers AI analyzers actually call:
    ``render_page_to_image(pdf_bytes, page_num, dpi)`` and
    ``render_all_pages(pdf_bytes, dpi)``.
    """

    def render_page(
        self,
        *,
        pdf_bytes: bytes,
        page_num: int,
        dpi: int,
    ) -> bytes: ...

    def render_page_to_image(
        self,
        pdf_bytes: bytes,
        page_num: int = ...,
        dpi: int = ...,
    ) -> bytes: ...

    def render_all_pages(
        self,
        pdf_bytes: bytes,
        dpi: int = ...,
    ) -> list[bytes]: ...


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


class StorageService(Protocol):
    """Object-storage handle for plugins that fetch tenant-uploaded
    bytes (e.g. reference PDFs for version-diff).

    OSS-mode stub returns ``None`` from every download — analyzers
    that need storage self-skip.
    """

    def download(self, file_id: str) -> bytes | None: ...


class TenantsService(Protocol):
    """Tenant config / entitlements lookup."""

    def get_ai_config(self, tenant_id: str) -> dict[str, Any] | None: ...

    def get_entitlements(self, tenant_id: str) -> dict[str, Any]: ...

    def get_historical_quality_data(
        self, tenant_id: str, *, limit: int = 100
    ) -> list[dict[str, Any]] | None:
        """Return historical preflight quality time-series for the tenant.

        Each entry is a dict with at least:
        ``job_id``, ``created_at`` (ISO 8601 string or None),
        ``status`` (e.g. "complete", "failed", "passed", "approved"),
        ``finding_count``, ``error_count``, ``warning_count``.

        Returns ``None`` when the SaaS host can't fulfil the query
        (DB unavailable, no historical data, OSS host without job
        history). Analyzers that consume this MUST handle ``None``
        gracefully.
        """
        ...


@dataclass(frozen=True)
class ClauseFailure:
    """One failed conformance clause as reported by codex (or veraPDF
    wrapped behind it). Mirrors the handoff Phase 0 contract."""

    clause: str
    test_number: str
    description: str
    failed_check_count: int


@dataclass(frozen=True)
class ConformanceVerdict:
    """Per-profile conformance result returned by codex's
    ``POST /documents/{id}/conformance/{profile}``.

    ``passed=True`` with empty ``clauses`` means the document is
    conformant. ``passed=False`` carries the capped list of failed
    clauses for the report.
    """

    passed: bool
    clauses: list[ClauseFailure] = field(default_factory=list)


class CodexClient(Protocol):
    """Handle for the unified codex extraction surface.

    Codex owns text-region detection, veraPDF conformance parsing,
    render dedup, and per-stage telemetry post-Phase 1 of the
    unified-extraction refactor. Every lint-pdf host (hosted or
    self-hosted) reads these signals via this Protocol instead of
    running them locally.

    Implementations:
    * ``_NoOpCodexClient`` — default when codex's SDK is not
      importable or the endpoint contract is not yet available;
      ``is_enabled()`` returns ``False`` so the orchestrator falls
      back to the local pass.
    * ``_CodexHttpClient`` (in ``lintpdf.codex_client``) — wraps
      ``codex_pdf.client.HttpClient`` and reads the unified
      endpoints once codex publishes them.
    """

    def is_enabled(self) -> bool:
        """Return ``True`` when this client is configured to route the
        codex-owned endpoints. ``False`` makes the orchestrator skip
        the codex path entirely (no exception, no log spam)."""
        ...

    def get_text_regions(
        self,
        *,
        pdf_hash: str,
        page_index: int,
        dpi: int,
    ) -> list[DetectedTextRegion]:
        """Return cached OCR text regions for one page, scaled to PDF
        points. Cache key matches codex's
        ``(pdf_hash, page_index, dpi)``."""
        ...

    def get_conformance_verdict(
        self,
        *,
        document_id: str,
        profile: str,
    ) -> ConformanceVerdict:
        """Trigger / fetch the codex conformance check for one profile
        (``pdfx4``, ``pdfa1b``, ``pdfua1`` etc.). Cache key matches
        codex's ``(pdf_hash, profile)``."""
        ...

    def last_stage_durations_ms(self) -> dict[str, int]:
        """Return the per-stage durations codex reported on the most
        recent call (parsed from ``X-Codex-Stage-Durations-Ms`` or the
        response envelope). Empty dict when nothing was reported.
        Cleared at the start of each new request so callers can
        accumulate independently."""
        ...


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
    storage: StorageService
    codex_client: CodexClient


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

    def get_historical_quality_data(
        self, _tenant_id: str, *, limit: int = 100
    ) -> list[dict[str, Any]] | None:
        return None


class _NoOpStorage:
    def download(self, _file_id: str) -> bytes | None:
        return None


class _NoOpCodexClient:
    """Default CodexClient that always reports unconfigured.

    Active whenever ``codex_pdf.client`` is not importable or the
    unified-extraction endpoint contract isn't available. Returns
    ``is_enabled() == False`` so the orchestrator's dispatch helper
    short-circuits to the local pass without touching the other
    methods. The other methods raise to surface accidental callers
    that forget to gate on ``is_enabled()``.
    """

    def is_enabled(self) -> bool:
        return False

    def get_text_regions(
        self,
        *,
        pdf_hash: str,
        page_index: int,
        dpi: int,
    ) -> list[Any]:
        raise RuntimeError(
            "_NoOpCodexClient.get_text_regions called without is_enabled() guard — fix the caller."
        )

    def get_conformance_verdict(
        self,
        *,
        document_id: str,
        profile: str,
    ) -> ConformanceVerdict:
        raise RuntimeError(
            "_NoOpCodexClient.get_conformance_verdict called without "
            "is_enabled() guard — fix the caller."
        )

    def last_stage_durations_ms(self) -> dict[str, int]:
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


def noop_storage() -> StorageService:
    """Return a storage stub that returns ``None`` from every download.
    Analyzers that need storage self-skip."""

    return _NoOpStorage()


def noop_codex_client() -> CodexClient:
    """Return a CodexClient stub that reports unconfigured.

    Used whenever codex's SDK is unavailable or the
    ``LINTPDF_CODEX_*`` feature flags are off. ``is_enabled()``
    returns ``False`` so the orchestrator routes to the local
    text-region pass and the local veraPDF runner."""

    return _NoOpCodexClient()
