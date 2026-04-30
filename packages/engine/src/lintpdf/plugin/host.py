"""Plugin host bridge — SaaS service wiring + legacy adapters.

Two responsibilities:

1. **`default_services_for_saas()`** — constructs a concrete ``Services``
   bundle wrapping the hosted LintPDF SaaS modules
   (``lintpdf.audit.metering``, ``lintpdf.ai.cost_cap``,
   ``lintpdf.ai.gpu_client``, ``lintpdf.conformance.verapdf_client``,
   etc.). This is the bridge that keeps every existing AI analyzer
   working unchanged through Phase 1: the orchestrator fetches the
   default services and stuffs them into the AnalyzerContext.

2. **`LegacyAIAdapter`** — wraps a decorator-registered ``BaseAIAnalyzer``
   subclass so it satisfies the new ``Analyzer`` Protocol. The adapter
   synthesises a ``PluginManifest`` from the analyzer's class attributes
   (`category`, `feature_slug`, `tier`, `credits_per_run`) and routes
   ``analyze_v2(ctx)`` calls back to the legacy ``analyze()`` signature.

OSS hosts skip ``default_services_for_saas`` entirely and construct a
``Services`` from the no-op stubs in ``plugin.services``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from lintpdf.plugin.manifest import PluginManifest, Tier
from lintpdf.plugin.services import (
    Services,
    noop_cost_cap,
    noop_metering,
    noop_storage,
    noop_tenants,
    noop_verapdf,
)

if TYPE_CHECKING:
    from lintpdf.ai.base import BaseAIAnalyzer
    from lintpdf.analyzers.finding import Finding
    from lintpdf.plugin.protocol import AnalyzerContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SaaS service bundle
# ---------------------------------------------------------------------------


@dataclass
class _SaasServices:
    """Concrete Services impl that wraps hosted-LintPDF modules.

    Each attribute is set in ``default_services_for_saas`` after
    importing the corresponding SaaS module lazily — the import is
    inside the factory so that an OSS install (where these modules
    may be absent or stripped) never sees them.
    """

    metering: Any
    cost_cap: Any
    gpu_client: Any
    llm_client: Any
    renderer: Any
    verapdf_client: Any
    database: Any
    tenants: Any
    storage: Any


def default_services_for_saas() -> Services:
    """Build a Services bundle for the hosted LintPDF SaaS.

    Each wrapper translates the new Protocol shape into the existing
    module's free-function or class API. Wrappers are kept inline (and
    intentionally small) so callers can read this single file to know
    every SaaS module the engine touches.

    Phase 2 inlines these wrappers into the Services impls and deletes
    the corresponding direct-import paths in analyzers.
    """

    # Lazy imports so OSS hosts that don't ship these modules don't
    # crash at engine import time.
    metering = _wrap_metering()
    cost_cap = _wrap_cost_cap()
    gpu_client = _wrap_gpu_client()
    llm_client = _wrap_llm_client()
    renderer = _wrap_renderer()
    verapdf_client = _wrap_verapdf()
    database = _wrap_database()
    tenants = _wrap_tenants()
    storage = _wrap_storage()

    return _SaasServices(  # type: ignore[return-value]
        metering=metering,
        cost_cap=cost_cap,
        gpu_client=gpu_client,
        llm_client=llm_client,
        renderer=renderer,
        verapdf_client=verapdf_client,
        database=database,
        tenants=tenants,
        storage=storage,
    )


def _wrap_metering() -> Any:
    try:
        from lintpdf.audit import metering as _m
    except ImportError:
        logger.info("lintpdf.audit.metering unavailable; using no-op")
        return noop_metering()

    class _MeteringWrap:
        def record_usage(
            self,
            *,
            tenant_id: str,
            feature_slug: str,
            units: int,
            metadata: dict[str, Any] | None = None,
        ) -> None:
            _m.record_usage(
                tenant_id=tenant_id,
                feature_slug=feature_slug,
                units=units,
                metadata=metadata or {},
            )

    return _MeteringWrap()


def _wrap_cost_cap() -> Any:
    try:
        from lintpdf.ai import cost_cap as _cc
    except ImportError:
        logger.info("lintpdf.ai.cost_cap unavailable; using no-op")
        return noop_cost_cap()

    class _CostCapWrap:
        def check_or_raise(
            self,
            *,
            tenant_id: str,
            feature_slug: str,
            estimated_units: int,
        ) -> None:
            _cc.check_cap_or_raise(
                tenant_id=tenant_id,
                feature_slug=feature_slug,
                estimated_units=estimated_units,
            )

    return _CostCapWrap()


def _wrap_gpu_client() -> Any:
    try:
        from lintpdf.ai.gpu_client import get_gpu_client
    except ImportError:
        logger.info("lintpdf.ai.gpu_client unavailable")
        return None
    return get_gpu_client()


def _wrap_llm_client() -> Any:
    """Phase 3d: SaaS host instantiates an Anthropic client and exposes
    it via the LLMClient.messages_create Protocol. Returns None when
    ANTHROPIC_API_KEY isn't set or the SDK isn't installed — analyzers
    self-skip in that case (same OSS-friendly skip pattern as every
    other service)."""
    import os

    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("LLMClient unavailable: ANTHROPIC_API_KEY not set")
        return None

    try:
        import anthropic
    except ImportError:
        logger.info("LLMClient unavailable: anthropic SDK not installed")
        return None

    # Module-level singleton would race during pytest; instantiate per
    # Services bundle (called once per orchestrator run).
    client = anthropic.Anthropic()

    class _LLMWrap:
        def messages_create(
            self,
            *,
            model: str,
            max_tokens: int,
            system: Any,
            messages: list[dict[str, Any]],
            tools: list[dict[str, Any]] | None = None,
            tool_choice: dict[str, Any] | None = None,
        ) -> Any:
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": messages,
            }
            if tools is not None:
                kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice
            return client.messages.create(**kwargs)

    return _LLMWrap()


def _wrap_renderer() -> Any:
    try:
        from lintpdf.rendering import render_all_pages, render_page_to_image
    except ImportError:
        logger.info("lintpdf.rendering unavailable")
        return None

    class _RendererWrap:
        def render_page(self, *, pdf_bytes: bytes, page_num: int, dpi: int) -> bytes:
            return render_page_to_image(pdf_bytes, page_num, dpi)

        def render_page_to_image(
            self, pdf_bytes: bytes, page_num: int = 1, dpi: int = 150
        ) -> bytes:
            return render_page_to_image(pdf_bytes, page_num, dpi)

        def render_all_pages(self, pdf_bytes: bytes, dpi: int = 150) -> list[bytes]:
            return render_all_pages(pdf_bytes, dpi=dpi)

    return _RendererWrap()


def _wrap_verapdf() -> Any:
    try:
        from lintpdf.conformance import verapdf_client as _v
    except ImportError:
        logger.info("lintpdf.conformance.verapdf_client unavailable")
        return noop_verapdf()

    class _VeraPDFWrap:
        def is_configured(self) -> bool:
            try:
                return bool(_v.is_verapdf_configured())
            except AttributeError:
                # Older client without an explicit accessor — assume
                # configured if the URL setting is non-empty.
                from lintpdf.config import get_settings

                return bool(get_settings().verapdf_url)

        def validate(self, *, pdf_bytes: bytes, profile: str) -> dict[str, Any]:
            return _v.validate_with_verapdf(pdf_bytes, profile)

    return _VeraPDFWrap()


def _wrap_database() -> Any:
    try:
        from lintpdf.api import database as _db
    except ImportError:
        logger.info("lintpdf.api.database unavailable")
        return None

    class _DatabaseWrap:
        def session(self) -> Any:
            return _db.SessionLocal()

    return _DatabaseWrap()


def _wrap_storage() -> Any:
    try:
        from lintpdf.api.storage import get_storage_backend
    except ImportError:
        logger.info("lintpdf.api.storage unavailable; using no-op")
        return noop_storage()

    class _StorageWrap:
        def download(self, file_id: str) -> bytes | None:
            try:
                backend = get_storage_backend()
                data = backend.download(str(file_id))
                if data and isinstance(data, bytes):
                    return data
            except Exception as exc:
                logger.debug("storage.download(%s) failed: %s", file_id, exc)
            return None

    return _StorageWrap()


def _wrap_tenants() -> Any:
    try:
        from lintpdf.tenants import config_resolver, entitlements
    except ImportError:
        logger.info("lintpdf.tenants.* unavailable; using no-op")
        return noop_tenants()

    class _TenantsWrap:
        def get_ai_config(self, tenant_id: str) -> dict[str, Any] | None:
            try:
                cfg = config_resolver.get_ai_config(tenant_id)
            except Exception as exc:
                logger.debug("get_ai_config(%s) failed: %s", tenant_id, exc)
                return None
            if cfg is None:
                return None
            # Normalise to plain dict so plugins don't depend on
            # the SaaS-side TenantAIConfig type.
            if hasattr(cfg, "model_dump"):
                return cfg.model_dump()
            return cfg.dict() if hasattr(cfg, "dict") else dict(cfg)

        def get_entitlements(self, tenant_id: str) -> dict[str, Any]:
            try:
                ent = entitlements.get_entitlements(tenant_id)
            except Exception as exc:
                logger.debug("get_entitlements(%s) failed: %s", tenant_id, exc)
                return {}
            if hasattr(ent, "model_dump"):
                return ent.model_dump()
            return ent.dict() if hasattr(ent, "dict") else dict(ent)

        def get_historical_quality_data(
            self, tenant_id: str, *, limit: int = 100
        ) -> list[dict[str, Any]] | None:
            """SaaS-host implementation of TenantsService.get_historical_quality_data.

            Returns None on any failure (DB unavailable, model import
            failure, query exception). Phase 3a moved this query out of
            the analyzer body so trend_analysis/submission_quality_spc.py
            no longer imports lintpdf.api.models directly — closing the
            last eta6 violation.
            """
            try:
                from sqlalchemy import func

                from lintpdf.api import database as _db
                from lintpdf.api.models import Job, JobFinding, JobStatus
            except ImportError as exc:
                logger.debug(
                    "get_historical_quality_data(%s): SaaS DB modules unavailable (%s)",
                    tenant_id,
                    exc,
                )
                return None

            try:
                db = _db.SessionLocal()
            except (RuntimeError, AttributeError) as exc:
                logger.debug("get_historical_quality_data(%s): no DB session (%s)", tenant_id, exc)
                return None

            try:
                jobs = (
                    db.query(Job)
                    .filter(
                        Job.tenant_id == str(tenant_id),
                        Job.status.in_([JobStatus.COMPLETE, JobStatus.FAILED]),
                    )
                    .order_by(Job.created_at.desc())
                    .limit(limit)
                    .all()
                )
                if not jobs:
                    return None

                results: list[dict[str, Any]] = []
                for job in jobs:
                    counts = (
                        db.query(
                            func.count(JobFinding.id).label("total"),
                            func.count(func.nullif(JobFinding.severity != "error", True)).label(
                                "errors"
                            ),
                            func.count(func.nullif(JobFinding.severity != "warning", True)).label(
                                "warnings"
                            ),
                        )
                        .filter(JobFinding.job_id == job.id)
                        .one()
                    )
                    results.append(
                        {
                            "job_id": str(job.id),
                            "created_at": job.created_at.isoformat() if job.created_at else None,
                            "status": job.status.value
                            if hasattr(job.status, "value")
                            else str(job.status),
                            "finding_count": counts.total or 0,
                            "error_count": counts.errors or 0,
                            "warning_count": counts.warnings or 0,
                        }
                    )
                return results if results else None
            except Exception:
                logger.debug(
                    "get_historical_quality_data(%s) query failed",
                    tenant_id,
                    exc_info=True,
                )
                return None
            finally:
                db.close()

    return _TenantsWrap()


# ---------------------------------------------------------------------------
# Legacy adapter — wraps decorator-registered BaseAIAnalyzer subclasses
# ---------------------------------------------------------------------------


def _tier_from_legacy(tier: str) -> Tier:
    if tier == "gpu":
        return Tier.GPU
    if tier == "external_ai":
        return Tier.EXTERNAL_AI
    return Tier.CPU


@dataclass
class LegacyAIAdapter:
    """Wraps a legacy ``BaseAIAnalyzer`` instance as a Plugin.

    The adapter:
      - synthesises a ``PluginManifest`` from class attributes;
      - routes ``analyze_v2(ctx)`` calls back to ``analyze(document,
        events, pdf_bytes, ai_config)`` so legacy analyzers run unchanged.

    AI config is pulled from ``ctx.config["ai_config"]`` and reconstituted
    into a ``TenantAIConfig`` object (when available) so legacy code that
    accesses ``ai_config.attribute`` keeps working through Phase 1. The
    reconstitution is best-effort — analyzers that read attributes the
    new dict lacks degrade to ``None`` rather than crashing.
    """

    legacy: BaseAIAnalyzer

    @property
    def manifest(self) -> PluginManifest:
        cls = type(self.legacy)
        return PluginManifest(
            id=f"lintpdf.legacy.{cls.__module__}.{cls.__name__}",
            version="0.0.0-legacy",
            tier=_tier_from_legacy(self.legacy.tier),
            requires_capabilities=(),
            requires_services=("metering", "cost_cap"),
            declared_check_ids=(),  # Legacy analyzers don't pre-declare; left empty.
            config_schema=None,
        )

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        ai_config_dict = ctx.config.get("ai_config") if ctx.config else None
        ai_config_obj = _reconstitute_tenant_ai_config(ai_config_dict)
        return self.legacy.analyze(
            ctx.document,
            ctx.events,
            ctx.pdf_bytes,
            ai_config_obj,
        )


def _reconstitute_tenant_ai_config(d: dict[str, Any] | None) -> Any:
    """Best-effort: turn a plain dict into a TenantAIConfig if available.

    Phase 2 strips legacy analyzers' use of TenantAIConfig entirely and
    has them read straight from the dict. Until then, the legacy code
    path expects an object with attribute access.
    """

    if d is None:
        return None
    try:
        from lintpdf.api.models import TenantAIConfig

        return TenantAIConfig(**d)
    except Exception as exc:
        logger.debug("TenantAIConfig reconstitution failed: %s", exc)

        # Fallback: a thin attribute-access wrapper so legacy analyzers
        # that do `ai_config.foo` don't crash on a plain dict.
        class _AttrDict:
            def __init__(self, data: dict[str, Any]) -> None:
                self._data = data

            def __getattr__(self, item: str) -> Any:
                return self._data.get(item)

        return _AttrDict(d)
