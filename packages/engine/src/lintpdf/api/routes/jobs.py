"""Job submission and retrieval endpoints."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import uuid as uuid_mod
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.config import get_settings
from lintpdf.api.database import get_db
from lintpdf.api.middleware import check_burst_rate_limit, check_rate_limit
from lintpdf.api.models import (
    BrandProfile,
    BrandSpec,
    Job,
    JobFinding,
    JobImportedReport,
    JobStatus,
    PreflightSource,
    Tenant,
)
from lintpdf.api.schemas import (
    FindingResponse,
    JobCreateResponse,
    JobListResponse,
    JobResponse,
    JobStateAnnotationComment,
    JobStateAnnotationItem,
    JobStateAnnotations,
    JobStateApprovalChain,
    JobStateApprovalStep,
    JobStateReportInfo,
    JobStateResponse,
    JobStateVerdict,
    JobSummaryResponse,
)
from lintpdf.api.storage import get_storage
from lintpdf.api.upload_security import PDF_TYPES, validate_upload_streaming
from lintpdf.tenants.models import RATE_LIMIT_WARN_THRESHOLD

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

_file_param = File(..., description="PDF file to preflight")
_profile_param = Form(
    default=None,
    description=(
        "Profile to use. When omitted, falls back to the tenant's "
        "default_profile_id (set by site-admins) or `lintpdf-default`."
    ),
)
_ai_enabled_param = Form(
    default=None,
    description=(
        "Per-job AI override. If true, AI analyzers run regardless of the "
        "profile's ai.enabled setting (subject to tenant entitlements). "
        "If false, AI is force-disabled. If unset, profile setting wins."
    ),
)
_ai_categories_param = Form(
    default=None,
    description=(
        "Comma-separated AI categories to enable for this job (overrides "
        "profile.ai.categories). Only applies when ``ai_enabled`` is true."
    ),
)
_ai_features_param = Form(
    default=None,
    description=(
        "Comma-separated AI feature slugs to enable for this job (overrides "
        "profile.ai.features). Only applies when ``ai_enabled`` is true."
    ),
)
_ai_preset_param = Form(
    default=None,
    description=(
        "AI preset slug (e.g. ``brand-compliance``, ``packaging-qc``, "
        "``full-ai-scan``). When provided the engine expands the preset to "
        "its feature list and implicitly enables AI for this job. Mutually "
        "compatible with ``ai_features``/``ai_categories`` — explicit lists "
        "override the preset's defaults."
    ),
)
_preflight_source_param = Form(
    default="engine",
    description=(
        "Preflight source mode. ``engine`` (default) runs LintPDF's full "
        "analyzer pipeline; ``external`` ingests a third-party preflight "
        "report supplied in the ``external_report`` field; ``minimal`` "
        "extracts only viewer essentials without running analyzers."
    ),
)
_external_format_param = Form(
    default=None,
    description=(
        "Format of the imported preflight report (one of "
        "``pitstop_xml``, ``callas_json``, ``callas_xml``, ``acrobat_xml``, "
        "``lintpdf_json``). Omit to auto-detect from the file content."
    ),
)
_external_report_param = File(
    default=None,
    description=(
        "Optional third-party preflight report file (required when ``preflight_source=external``)."
    ),
)
_mapping_id_param = Form(
    default=None,
    description=(
        "UUID of a tenant-defined import mapping to parse the "
        "``external_report`` with. When provided the mapping must be "
        "owned by the authenticated tenant, and ``external_format`` is "
        "implicitly set to ``custom`` — built-in parsers are bypassed."
    ),
)
_brand_param = Form(
    default=None,
    description=(
        "Branding override for this job's outputs. Values: ``anonymous`` "
        "(strip all branding and sanitise PDF metadata — for brokers "
        "forwarding reports to distributors), ``lintpdf`` (LintPDF default), "
        "or a BrandProfile UUID owned by the tenant. Absent → tenant default."
    ),
)
_unbranded_param = Form(
    default=None,
    description=(
        "Convenience alias: when true, submits the job with anonymous "
        "branding (equivalent to ``brand=anonymous``)."
    ),
)
_brand_spec_param = Form(
    default=None,
    description=(
        "Per-submission BrandSpec override. Accepts a UUID owned by the "
        "authenticated tenant; the resolver uses it in preference to any "
        "custom endpoint's default BrandSpec and the tenant-default "
        "BrandSpec. Absent → fall back to the endpoint / tenant default. "
        "Strict colour advisories stay suppressed when no spec resolves "
        "anywhere in the chain."
    ),
)
_overrides_param = Form(
    default=None,
    description=(
        "Universal per-call override envelope as a JSON string. Accepts "
        "``checks``, ``thresholds``, ``conformance``, ``workflow``, "
        "``color``, ``ai``, ``viewer``, ``report``, ``branding``, "
        "``share`` — see ``lintpdf.overrides.OverridesEnvelope``. All "
        "fields optional; only provided values override the resolved "
        "profile / tenant default. Flat parameters (brand, unbranded, "
        "ai_enabled, etc.) continue to work for back-compat."
    ),
)


def _send_rate_warning_if_needed(tenant: Tenant, usage: object) -> None:  # skipcq: PY-R1000
    """Fire a rate-limit warning or overage notice email.

    Uses a Redis key to deduplicate — only one email per threshold per day.
    """
    from lintpdf.api.middleware import UsageInfo, get_redis_client
    from lintpdf.tenants.models import RATE_LIMIT_OVERAGE_THRESHOLD

    if not isinstance(usage, UsageInfo):
        return

    contact = getattr(tenant, "contact_email", None)
    if not contact:
        return

    threshold = None
    if usage.percentage >= RATE_LIMIT_OVERAGE_THRESHOLD:
        threshold = RATE_LIMIT_OVERAGE_THRESHOLD
    elif usage.percentage >= RATE_LIMIT_WARN_THRESHOLD:
        threshold = RATE_LIMIT_WARN_THRESHOLD
    else:
        return

    # Deduplicate via Redis — one warning per threshold per day
    redis = get_redis_client()
    if redis is not None:
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        warn_key = f"rate_warn:{tenant.id}:{today}:{threshold}"
        try:
            already_sent = redis.set(warn_key, "1", nx=True, ex=86400)
            if not already_sent:
                return
        except Exception:
            logger.debug("Redis dedup check failed — sending warning anyway")

    try:
        if threshold == RATE_LIMIT_OVERAGE_THRESHOLD and usage.overage_enabled:
            from lintpdf.email.service import send_overage_started

            send_overage_started(
                to=contact,
                tenant_name=tenant.name,
                used=usage.used,
                limit=usage.limit,
                rate_cents=usage.overage_rate_cents,
                cost_cents=usage.overage_cost_cents,
            )
        else:
            from lintpdf.email.service import send_rate_limit_warning

            send_rate_limit_warning(
                to=contact,
                tenant_name=tenant.name,
                used=usage.used,
                limit=usage.limit,
            )
    except Exception:
        logger.exception("Failed to send rate limit warning email")


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_job(  # skipcq: PY-R1000
    file: UploadFile = _file_param,
    profile_id: str | None = _profile_param,
    jdf_file: UploadFile | None = File(default=None, description="Optional JDF/XJDF sidecar"),
    ai_enabled: bool | None = _ai_enabled_param,
    ai_categories: str | None = _ai_categories_param,
    ai_features: str | None = _ai_features_param,
    ai_preset: str | None = _ai_preset_param,
    preflight_source: str = _preflight_source_param,
    external_format: str | None = _external_format_param,
    external_report: UploadFile | None = _external_report_param,
    mapping_id: str | None = _mapping_id_param,
    brand: str | None = _brand_param,
    unbranded: bool | None = _unbranded_param,
    brand_spec_id: str | None = _brand_spec_param,
    overrides: str | None = _overrides_param,
    wait: float | None = Query(
        default=None,
        ge=0,
        description=(
            "If set, block the response until the job reaches a terminal "
            "state (``complete`` / ``failed``) or this many seconds have "
            "elapsed, whichever comes first. Omit (default) for the "
            "standard async 202 + job_id response. Server-side ceiling "
            "is ``LINTPDF_SYNC_MAX_WAIT_S`` (default 120s) — values above "
            "that are clamped. On timeout the handler falls back to the "
            "202 response so the caller can keep polling via "
            "``GET /api/v1/jobs/{job_id}``."
        ),
    ),
    ocr: str | None = Query(
        default=None,
        description=(
            "WS-C opt-in for Claude OCR on outlined PDFs. "
            "``?ocr=force`` runs the OCR pass on every page regardless "
            "of the extractable-char heuristic. Omit (default) for "
            "the standard auto-trigger: OCR only when a page has "
            "< 5 extractable characters."
        ),
    ),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> JSONResponse:
    """Submit a PDF for preflight checking.

    The job is processed asynchronously by default (202 + job_id). Pass
    ``?wait=<seconds>`` to block for inline results; see the ``wait``
    parameter for semantics.
    """
    # Parse the overrides envelope (JSON string in a multipart form —
    # Pydantic can't natively nest JSON through FastAPI's Form). Empty
    # string / None = no overrides; invalid JSON or unknown fields =
    # 422 with the path that broke so the caller can fix their payload.
    overrides_envelope = None
    overrides_as_dict: dict[str, object] | None = None
    if overrides:
        import json as _json

        from pydantic import ValidationError as _ValidationError

        from lintpdf.overrides import OverridesEnvelope as _OverridesEnvelope

        try:
            overrides_payload = _json.loads(overrides)
        except _json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"overrides must be valid JSON: {exc}",
            ) from exc
        try:
            overrides_envelope = _OverridesEnvelope.model_validate(overrides_payload)
        except _ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"overrides failed validation: {exc.errors()}",
            ) from exc
        overrides_as_dict = overrides_envelope.model_dump(exclude_unset=True, exclude_none=True)

        # Map envelope → flat form params where both exist, so the rest
        # of this handler (branding resolution, AI resolution) sees one
        # consistent set of values. The nested envelope wins because
        # it's more explicit — callers using it are opting in to the
        # new shape.
        if overrides_envelope.branding is not None:
            b = overrides_envelope.branding
            if b.mode is not None and brand is None:
                brand = b.profile_id if b.mode == "profile" and b.profile_id else b.mode
        if overrides_envelope.ai is not None:
            a = overrides_envelope.ai
            if a.enabled is not None and ai_enabled is None:
                ai_enabled = a.enabled
            if a.categories is not None and ai_categories is None:
                ai_categories = ",".join(a.categories)
            if a.features is not None and ai_features is None:
                ai_features = ",".join(a.features)
            if a.preset is not None and ai_preset is None:
                ai_preset = a.preset
    # Check rate limit (raises 429 if hard limit exceeded).
    # Daily rate limit stays as the abuse shield; the monthly file
    # quota check below consumes a file from the tenant's metered pool
    # and returns 402 Payment Required once the pool is empty (unless
    # overage billing is on). The two checks compose — rate_limit_daily
    # rejects traffic bursts, file_quota rejects over-consumption.
    check_burst_rate_limit(tenant)
    usage = check_rate_limit(tenant)

    from lintpdf.billing.file_quota import check_and_consume_file_quota

    check_and_consume_file_quota(tenant, files_requested=1, db=db)

    # Validate ``profile_id`` exists at submit time so clients get a clean
    # 404 instead of a queued job that silently fails in the worker. This
    # also matches the test contract: nonexistent profile → 404.
    #
    # Resolver checks: tenant's custom_profiles (wins on collision) →
    # visible system_profiles → tenant default → `lintpdf-default`.
    # Also side-fixes the pre-existing bug where a tenant with a valid
    # custom_profiles row 404'd because the old check only hit the
    # bundled registry.
    from lintpdf.profiles.resolver import (
        profile_exists_for_tenant,
        resolve_effective_profile_id,
    )

    profile_id = resolve_effective_profile_id(db, tenant, profile_id)
    if not profile_exists_for_tenant(db, tenant, profile_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found",
        )

    # ------------------------------------------------------------------
    # Resolve the preflight source + external import parameters.
    # ------------------------------------------------------------------
    try:
        source_enum = PreflightSource(preflight_source.lower().strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid preflight_source {preflight_source!r}. "
                "Expected one of: engine, external, minimal."
            ),
        ) from exc

    # Tier gate: some plans (e.g. Viewer) forbid engine-mode submissions.
    from lintpdf.api.gates import plan_upgrade_required
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)
    if source_enum.value not in entitlements.allowed_preflight_sources:
        raise plan_upgrade_required(
            gate="preflight_source",
            current_plan=str(tenant.plan),
            required_plan="starter",
            message=(
                f"Your plan ({tenant.plan}) does not allow "
                f"preflight_source={source_enum.value!r}. "
                f"Allowed: {entitlements.allowed_preflight_sources}."
            ),
        )

    if source_enum is PreflightSource.EXTERNAL and external_report is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "preflight_source='external' requires an external_report file "
                "containing the third-party preflight output."
            ),
        )
    if source_enum is not PreflightSource.EXTERNAL and external_report is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=("external_report is only valid when preflight_source='external'."),
        )

    resolved_external_format: str | None = None
    external_report_bytes: bytes | None = None
    resolved_mapping_id: uuid_mod.UUID | None = None
    if source_enum is PreflightSource.EXTERNAL and external_report is not None:
        from lintpdf.api.models import TenantImportMapping
        from lintpdf.imports.base import ParserError
        from lintpdf.imports.custom import CustomMappingParser
        from lintpdf.imports.detect import (
            detect_format,
            parser_for_format,
        )

        # Hard cap imported reports at 50 MB — PitStop/callas XML for huge
        # jobs rarely exceed a few MB; anything larger is almost certainly
        # a mistake or abuse.
        max_report_bytes = 50 * 1024 * 1024
        external_report_bytes = await external_report.read()
        if not external_report_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="external_report is empty.",
            )
        if len(external_report_bytes) > max_report_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"external_report exceeds maximum size of "
                    f"{max_report_bytes // (1024 * 1024)} MB."
                ),
            )

        # ``mapping_id`` bypasses built-in parser selection: the tenant's
        # own mapping drives parsing. We still materialise the parser here
        # (without calling .parse()) to fail fast on mapping misconfig.
        if mapping_id:
            try:
                candidate_mapping_uuid = uuid_mod.UUID(mapping_id)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="mapping_id must be a valid UUID.",
                ) from exc
            mapping_row = (
                db.query(TenantImportMapping)
                .filter(
                    TenantImportMapping.id == candidate_mapping_uuid,
                    TenantImportMapping.tenant_id == tenant.id,
                )
                .first()
            )
            if mapping_row is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=("Import mapping not found or not owned by the authenticated tenant."),
                )
            if not mapping_row.is_active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Import mapping is inactive.",
                )
            try:
                CustomMappingParser(mapping_row.config, mapping_id=str(mapping_row.id))
            except ParserError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Import mapping config invalid: {exc}",
                ) from exc
            resolved_mapping_id = candidate_mapping_uuid
            resolved_external_format = "custom"
        # Fail-fast format validation — either the caller specified a
        # format we support, or the payload sniffs to one we support.
        elif external_format:
            try:
                parser_for_format(external_format)
            except ParserError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(exc),
                ) from exc
            resolved_external_format = external_format
        else:
            try:
                resolved_external_format = detect_format(external_report_bytes)
            except ParserError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Could not auto-detect external_format. Pass an "
                        "explicit external_format field (pitstop_xml, "
                        f"callas_json, callas_xml, acrobat_xml, lintpdf_json), "
                        f"or a mapping_id. Detector said: {exc}"
                    ),
                ) from exc

    # ------------------------------------------------------------------
    # Resolve brand override. ``unbranded=true`` is an ergonomic alias
    # for ``brand=anonymous``; explicit ``brand`` wins if both supplied.
    # ------------------------------------------------------------------
    from lintpdf.reports.service import BrandMode, parse_brand_param

    brand_mode_resolved: BrandMode | None = None
    brand_profile_override_id: uuid_mod.UUID | None = None
    unbranded_override_flag = False

    effective_brand = brand
    if effective_brand is None and unbranded:
        effective_brand = "anonymous"

    if effective_brand is not None:
        brand_mode_resolved, raw_profile_id = parse_brand_param(effective_brand)
        if brand_mode_resolved is BrandMode.ANONYMOUS:
            unbranded_override_flag = True
        elif brand_mode_resolved is BrandMode.PROFILE:
            if raw_profile_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="brand parameter missing a profile id.",
                )
            try:
                candidate_uuid = uuid_mod.UUID(raw_profile_id)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Invalid brand value {effective_brand!r}. Expected "
                        "'anonymous', 'lintpdf', or a BrandProfile UUID."
                    ),
                ) from exc
            profile_row = (
                db.query(BrandProfile)
                .filter(
                    BrandProfile.id == candidate_uuid,
                    BrandProfile.tenant_id == tenant.id,
                )
                .first()
            )
            if profile_row is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=("BrandProfile not found or not owned by the authenticated tenant."),
                )
            brand_profile_override_id = candidate_uuid
        # BrandMode.LINTPDF is represented by leaving both overrides unset —
        # the resolver falls through to the LintPDF default when neither
        # ``unbranded_override`` nor ``brand_profile_id_override`` is set
        # and the tenant's own default isn't anonymous. To force LintPDF
        # over a tenant "anonymous default", we still need a signal: wipe
        # tenant anonymous intent by setting ``unbranded_override=False``
        # and leaving the profile override empty — because nothing below
        # Job overrides looks further down, the resolver will correctly
        # return LintPDF default only when ``tenant.unbranded_by_default``
        # is False. For the "tenant default is anonymous but job wants
        # LintPDF" edge case we surface the explicit param as a query
        # string on the report URL, so persisting it is unnecessary.

    # Resolve the per-submission BrandSpec override. We validate
    # ownership here (before the upload has started) so a malformed
    # or foreign ID fails fast with a 422/404 rather than after the
    # caller has paid the PDF upload cost. A missing BrandSpec is a
    # 404 rather than a silent fallback — the caller explicitly
    # asked for a spec and we shouldn't pretend we found one.
    brand_spec_id_resolved: uuid_mod.UUID | None = None
    if brand_spec_id is not None:
        try:
            brand_spec_id_resolved = uuid_mod.UUID(brand_spec_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="brand_spec_id must be a UUID.",
            ) from exc
        spec_row = (
            db.query(BrandSpec)
            .filter(
                BrandSpec.id == brand_spec_id_resolved,
                BrandSpec.tenant_id == tenant.id,
                BrandSpec.is_archived.is_(False),
            )
            .first()
        )
        if spec_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand spec '{brand_spec_id}' not found or archived.",
            )

    # Stream upload body into a spooled temp file so worker RSS stays
    # bounded regardless of PDF size — the first stress test (2026-04-21)
    # wedged the engine when 15 concurrent 30-47 MB uploads materialized
    # their bodies as ``bytes`` in the event loop. See
    # ``validate_upload_streaming`` docstring for details.
    spool, file_size = await validate_upload_streaming(
        file,
        allowed_types=PDF_TYPES,
        max_size_bytes=tenant.max_file_size_mb * 1024 * 1024,
        settings=get_settings(),
    )

    job_id = uuid_mod.uuid4()

    storage = get_storage()
    loop = asyncio.get_running_loop()
    try:
        file_key = await loop.run_in_executor(
            None,
            storage.upload_pdf_stream,
            str(tenant.id),
            str(job_id),
            spool,
        )
    finally:
        with contextlib.suppress(Exception):
            spool.close()

    # Parse JDF sidecar if provided
    jdf_overrides = None
    if jdf_file is not None:
        try:
            jdf_content = await jdf_file.read()
            from lintpdf.integrations.jdf_parser import params_to_overrides, parse_jdf

            jdf_params = parse_jdf(jdf_content)
            jdf_overrides = params_to_overrides(jdf_params)
        except Exception:
            logger.warning("Failed to parse JDF sidecar for job %s — ignoring", job_id)

    job = Job(
        id=job_id,
        tenant_id=tenant.id,
        status=JobStatus.PENDING,
        profile_id=profile_id,
        file_key=file_key,
        file_name=file.filename,
        file_size=file_size,
        jdf_overrides=jdf_overrides,
        preflight_source=source_enum,
        external_format=resolved_external_format,
        brand_profile_id_override=brand_profile_override_id,
        unbranded_override=unbranded_override_flag,
        brand_spec_id=brand_spec_id_resolved,
        # Persisted so the worker (via ``run_preflight``), the viewer
        # config endpoint, and any subsequent mint call all see the
        # exact envelope the caller sent — no re-parsing, no drift.
        overrides=overrides_as_dict,
        # WS-C: ``?ocr=force`` forces Claude OCR on every page
        # regardless of the extractable-char heuristic.
        ocr_force=(ocr == "force"),
    )
    db.add(job)

    # Persist the imported preflight artifact so the worker can re-read
    # it without the caller needing to re-upload, and so we can re-parse
    # on parser upgrades / audit.
    if source_enum is PreflightSource.EXTERNAL and external_report_bytes is not None:
        report_key = f"{tenant.id}/{job_id}/external-report.dat"
        report_content_type = (
            external_report.content_type if external_report is not None else None
        ) or "application/octet-stream"
        await loop.run_in_executor(
            None,
            lambda: storage.upload_raw(report_key, external_report_bytes, report_content_type),
        )
        imported_source_metadata: dict[str, Any] | None = None
        if resolved_mapping_id is not None:
            imported_source_metadata = {"mapping_id": str(resolved_mapping_id)}
        db.add(
            JobImportedReport(
                id=uuid_mod.uuid4(),
                job_id=job_id,
                format=resolved_external_format or "unknown",
                raw_blob_key=report_key,
                raw_size_bytes=len(external_report_bytes),
                parser_version="1",
                source_metadata=imported_source_metadata,
            )
        )

    db.commit()

    # Queue the job for async processing
    from lintpdf.queue.tasks import run_preflight
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)

    # Redis PDF hot-cache (``pdf_cache:{file_key}``) was previously
    # populated here as a latency optimisation for the worker. At
    # bulk-file scale it just moves the RAM pressure from the engine to
    # the Redis server (100 × 50 MB bodies = 5 GB Redis RSS) for a
    # marginal round-trip saving. The worker already falls back to R2
    # on cache miss; we skip the cache entirely now so streaming
    # uploads actually pay off.

    # Expand an ``ai_preset`` into its feature list. A preset implicitly
    # enables AI (``ai_enabled=true``) unless the caller already supplied
    # an explicit ``ai_enabled=false`` to force-disable. Explicit
    # ``ai_features``/``ai_categories`` values still win over the
    # preset's defaults so callers can customize a preset.
    preset_features: list[str] | None = None
    preset_categories: list[str] | None = None
    if ai_preset:
        from lintpdf.api.routes.ai_presets import _AI_PRESETS

        if ai_preset not in _AI_PRESETS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"AI preset '{ai_preset}' not found",
            )
        raw_features = _AI_PRESETS[ai_preset].get("features", [])
        # ``full-ai-scan`` uses the sentinel ``["all"]`` which the
        # registry reads as categories=["all"] → run everything.
        if raw_features == ["all"]:
            preset_categories = ["all"]
        else:
            preset_features = [str(f) for f in raw_features]
        if ai_enabled is None:
            ai_enabled = True

    # Queue routing (bulk-files step 3 — queue isolation):
    #   ai_heavy  → any job where AI is enabled. Dedicated worker
    #               service (railway.worker-ai.toml) with concurrency
    #               tuned to Modal's max_containers so AI jobs can't
    #               starve the deterministic pool.
    #   priority  → paid-tier non-AI jobs. Served by railway.worker.toml.
    #   default   → free-tier non-AI jobs. Same worker, lower priority.
    if ai_enabled:
        queue_name = "ai_heavy"
    elif entitlements.priority_processing:
        queue_name = "priority"
    else:
        queue_name = "default"
    task_args = [str(job_id), profile_id, file_key]
    task_kwargs: dict[str, Any] = {}
    if jdf_overrides:
        task_kwargs["jdf_overrides"] = jdf_overrides
    if ai_enabled is not None:
        task_kwargs["ai_enabled"] = ai_enabled
    if ai_categories:
        task_kwargs["ai_categories"] = [c.strip() for c in ai_categories.split(",") if c.strip()]
    elif preset_categories:
        task_kwargs["ai_categories"] = preset_categories
    if ai_features:
        task_kwargs["ai_features"] = [f.strip() for f in ai_features.split(",") if f.strip()]
    elif preset_features:
        task_kwargs["ai_features"] = preset_features
    run_preflight.apply_async(
        args=task_args,
        kwargs=task_kwargs,
        queue=queue_name,
    )

    # Send rate warning email if approaching or exceeding limit
    if usage is not None and (usage.warning or usage.in_overage):
        _send_rate_warning_if_needed(tenant, usage)

    # Build rate-limit headers once — they apply to both the async 202
    # and the sync 200 variants below.
    headers: dict[str, str] = {}
    if usage is not None:
        headers["X-RateLimit-Limit"] = str(usage.limit)
        headers["X-RateLimit-Remaining"] = str(usage.remaining_included)
        headers["X-RateLimit-Used"] = str(usage.used)
        if usage.in_overage:
            headers["X-RateLimit-Overage"] = "true"
            headers["X-RateLimit-Overage-Count"] = str(usage.overage_count)
            headers["X-RateLimit-Overage-Cost-Cents"] = str(usage.overage_cost_cents)
            headers["X-RateLimit-Overage-Rate-Cents"] = str(usage.overage_rate_cents)

    # Sync mode: block for terminal state up to ``wait`` seconds, bounded
    # by the server-side ceiling. On timeout fall through to the standard
    # 202 response so the caller can keep polling.
    if wait is not None and wait > 0:
        effective_wait = min(wait, get_settings().sync_max_wait_s)
        job_response = await poll_job_until_terminal(
            job_id=job_id,
            tenant_id=tenant.id,
            db=db,
            max_wait_s=effective_wait,
        )
        if job_response is not None:
            return JSONResponse(
                content=job_response.model_dump(mode="json"),
                status_code=status.HTTP_200_OK,
                headers=headers,
            )

    response_data = JobCreateResponse(job_id=job_id).model_dump(mode="json")
    return JSONResponse(content=response_data, status_code=202, headers=headers)


def _hydrate_job_response(db: Session, job: Job) -> JobResponse:
    """Build a full ``JobResponse`` for a loaded ``Job`` row.

    Shared between ``GET /api/v1/jobs/{id}`` and the sync ``?wait``
    path on ``POST /api/v1/jobs`` / ``POST /api/v1/endpoints/{id}/submit``
    — both need the same summary + findings + reports hydration once the
    job reaches a terminal state.
    """
    response = JobResponse(
        job_id=job.id,
        status=job.status.value if hasattr(job.status, "value") else str(job.status),
        profile_id=job.profile_id,
        file_name=job.file_name,
        file_size=job.file_size,
        page_count=job.page_count,
        created_at=job.created_at,
        completed_at=job.completed_at,
        duration_ms=job.duration_ms,
        error_message=job.error_message,
        # WS-C/WS-D — dieline, art size, legend swatches and OCR text
        # layer were declared on the DB model but never on the Pydantic
        # response, so GET /jobs/{id} was silently dropping them. The
        # viewer's share-link config endpoint worked because that path
        # reads these columns directly; the public API did not.
        dieline=job.dieline,
        art_size_mm=job.art_size_mm,
        legend_swatches=job.legend_swatches,
        ocr_text_layer=job.ocr_text_layer,
    )

    if job.status == JobStatus.COMPLETE and job.result_json:
        result = job.result_json
        summary = result.get("summary", {})
        response.summary = JobSummaryResponse(
            total_findings=summary.get("total_findings", 0),
            error_count=summary.get("error_count", 0),
            warning_count=summary.get("warning_count", 0),
            advisory_count=summary.get("advisory_count", 0),
            passed=summary.get("passed", True),
            page_count=summary.get("page_count", 0),
            file_size_bytes=summary.get("file_size_bytes", 0),
        )

        from lintpdf.api.schemas import AuditVerdict

        def _audit_for(f: JobFinding) -> AuditVerdict | None:
            # Surface the AI accuracy-audit verdict when the auditor
            # has written one. Keeping the whole field ``None`` (rather
            # than a status-less stub) lets the viewer cheaply decide
            # "no audit ran → render no chip" with a single null check.
            if not f.audit_status:
                return None
            return AuditVerdict(
                status=f.audit_status,
                rationale=f.audit_rationale,
                model=f.audit_model,
                at=f.audit_at,
            )

        findings: list[JobFinding] = job.findings
        response.findings = [
            FindingResponse(
                inspection_id=f.inspection_id,
                severity=f.severity,
                message=f.message,
                page_num=f.page_num,
                details=f.details,
                source=f.source,
                category=f.category,
                bbox=[f.bbox_x0, f.bbox_y0, f.bbox_x1, f.bbox_y1]
                if f.bbox_x0 is not None
                else None,
                object_id=f.object_id,
                object_type=f.object_type,
                audit=_audit_for(f),
            )
            for f in findings
        ]

        # Include auto-generated report URLs if available. Resolve the
        # base URL through the whitelabel-aware resolver so tenants with a
        # verified ``brand_custom_domain`` (or a verified per-profile
        # ``custom_domain``) see their own domain in the URLs returned by
        # both ``GET /api/v1/jobs/{id}`` and the sync ``?wait=`` path —
        # otherwise whitelabel customers would get back
        # ``https://reports.lintpdf.com/r/<token>`` even though their
        # minted reports are served from their custom domain.
        from lintpdf.api.config import get_settings as _get_settings
        from lintpdf.api.models import BrandProfile, ReportToken, Tenant
        from lintpdf.reports.service import resolve_report_base_url
        from lintpdf.tenants.entitlements import resolve_entitlements

        report_tokens = (
            db.query(ReportToken)
            .filter(ReportToken.job_id == job.id, ReportToken.tenant_id == job.tenant_id)
            .all()
        )
        if report_tokens:
            settings = _get_settings()
            tenant = (
                db.query(Tenant).filter(Tenant.id == job.tenant_id).first()
            )
            base_url = settings.report_base_url
            if tenant is not None:
                entitlements = resolve_entitlements(tenant)
                active_profile: BrandProfile | None = None
                if entitlements.whitelabel_enabled and tenant.default_brand_profile_id:
                    active_profile = (
                        db.query(BrandProfile)
                        .filter(
                            BrandProfile.id == tenant.default_brand_profile_id,
                            BrandProfile.tenant_id == tenant.id,
                        )
                        .first()
                    )
                base_url = resolve_report_base_url(
                    tenant, active_profile, entitlements, settings
                )
            response.reports = {
                t.format: f"{base_url}/r/{t.token}{'.pdf' if t.format == 'pdf' else ''}"
                for t in report_tokens
            }

    return response


async def poll_job_until_terminal(
    job_id: uuid_mod.UUID,
    tenant_id: uuid_mod.UUID,
    db: Session,
    max_wait_s: float,
    poll_interval_s: float = 0.5,
) -> JobResponse | None:
    """Poll the ``jobs`` row every ``poll_interval_s`` until terminal.

    Returns a fully-hydrated :class:`JobResponse` the moment the job
    reaches ``complete`` or ``failed``. If ``max_wait_s`` elapses first
    the coroutine returns ``None`` so the caller can fall back to the
    regular 202 + job_id response (caller can then poll client-side
    via ``GET /api/v1/jobs/{id}``).

    The function issues a fresh ``SELECT`` each loop so it sees writes
    committed by the worker process on the other side of the
    transaction boundary.
    """
    deadline = asyncio.get_event_loop().time() + max(0.0, max_wait_s)
    while True:
        # Re-query on every tick. ``db.expire_all()`` drops cached
        # identity-map state so the follow-up query re-fetches the
        # row freshly from Postgres instead of handing back the
        # stale ``pending`` version from when the row was inserted.
        db.expire_all()
        job: Job | None = (
            db.query(Job)
            .options(selectinload(Job.findings))
            .filter(Job.id == job_id, Job.tenant_id == tenant_id)
            .first()
        )
        if job is None:
            # Row was deleted mid-wait (tenant purge, admin cancel).
            return None
        if job.status in (JobStatus.COMPLETE, JobStatus.FAILED):
            return _hydrate_job_response(db, job)
        if asyncio.get_event_loop().time() >= deadline:
            return None
        await asyncio.sleep(poll_interval_s)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> JobResponse:
    """Get job status and results."""
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid job id: '{job_id}' is not a valid UUID.",
        ) from exc

    # Eager-load findings in a single round trip instead of issuing a
    # separate ``SELECT ... FROM job_findings WHERE job_id = ?`` below.
    # ``selectinload`` issues one extra query for the collection (not
    # per-row), so a job with 10k findings still emits exactly two
    # queries instead of 10k + 1.
    job: Job | None = (
        db.query(Job)
        .options(selectinload(Job.findings))
        .filter(Job.id == uid, Job.tenant_id == tenant.id)
        .first()
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    return _hydrate_job_response(db, job)


# ---------------------------------------------------------------------------
# Universal job-state digest
# ---------------------------------------------------------------------------

_STATE_SECTIONS = {"reports", "approval_chain", "verdict", "annotations"}


def _parse_include(raw: str | None) -> set[str]:
    """Normalise the `?include=` query param.

    * Unset (``None`` or empty) → every section included (default).
    * Comma-separated list → exactly those sections; unknown keys 422.
    * The ``job`` key is always returned (there's no job-less digest).
    """
    if raw is None or not raw.strip():
        return set(_STATE_SECTIONS)
    wanted: set[str] = set()
    for part in raw.split(","):
        key = part.strip()
        if not key:
            continue
        if key not in _STATE_SECTIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Unknown include key {key!r}. Expected any of: "
                    f"{', '.join(sorted(_STATE_SECTIONS))}."
                ),
            )
        wanted.add(key)
    return wanted


@router.get("/{job_id}/state", response_model=JobStateResponse)
async def get_job_state(
    job_id: str,
    include: str | None = None,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> JobStateResponse:
    """Return the universal state of a preflight job in one call.

    Stitches together the five retrieval surfaces callers currently have
    to fan out across:

    1. Core job (`GET /jobs/{id}`) — status, preflight summary + findings,
       auto-attached report URLs.
    2. Reports (`GET /jobs/{id}/reports`) — every minted token with
       share-link metadata (`allow_annotations`, `require_visitor_email`).
    3. Approval chain (`GET /jobs/{id}/approval-chain`) — status +
       step history including each approver's free-text `notes`.
    4. Verdict (`GET /viewer/jobs/{id}/verdict`) — manual pass/fail
       marker + aggregated notes + the auto-passed flag mirrored from
       the preflight summary.
    5. Annotations (`GET /viewer/jobs/{id}/annotations`) with threaded
       comments embedded inline (no N+1; comments are joined in a single
       query via ``annotation_id IN (...)``).

    Use ``?include=approval_chain,verdict`` to trim the payload to just
    the sections you need. Unknown include keys return 422.
    """
    from lintpdf.api.config import get_settings as _get_settings
    from lintpdf.api.models import (
        ApprovalChain,
        ApprovalStep,
        ReportToken,
        ViewerAnnotation,
        ViewerAnnotationComment,
    )

    wanted = _parse_include(include)

    # 1. Core job (reuse the existing /jobs/{id} surface wholesale).
    job_response = await get_job(job_id=job_id, db=db, tenant=tenant)
    # At this point we know the job exists + belongs to the tenant, since
    # get_job() has already 404'd otherwise. Pull the UUID back so we
    # don't pay the parse twice.
    uid = uuid_mod.UUID(job_id)

    state = JobStateResponse(job=job_response)

    # 2. Reports — every token, including share-link metadata.
    if "reports" in wanted:
        base_url = _get_settings().report_base_url.rstrip("/")
        tokens = (
            db.query(ReportToken)
            .filter(ReportToken.job_id == uid, ReportToken.tenant_id == tenant.id)
            .order_by(ReportToken.created_at.asc())
            .all()
        )
        state.reports = [
            JobStateReportInfo(
                format=t.format,
                # Match the suffix logic used by /r/{token}.{ext} public routes.
                url=(
                    f"{base_url}/r/{t.token}.pdf"
                    if t.format in ("pdf", "annotated_pdf", "annotated_pdf_markup")
                    else f"{base_url}/r/{t.token}.json"
                    if t.format == "json"
                    else f"{base_url}/r/{t.token}.xml"
                    if t.format == "xml"
                    else f"{base_url}/r/{t.token}"
                ),
                token=t.token,
                expires_at=t.expires_at.isoformat() if t.expires_at else None,
                allow_annotations=bool(t.allow_annotations),
                require_visitor_email=t.require_visitor_email,
            )
            for t in tokens
        ]

    # 3. Approval chain — reuse the existing serialiser so the shape
    # matches the standalone /approval-chain endpoint exactly.
    if "approval_chain" in wanted:
        chain = (
            db.query(ApprovalChain)
            .filter(ApprovalChain.job_id == uid, ApprovalChain.tenant_id == tenant.id)
            .first()
        )
        if chain is not None:
            steps = (
                db.query(ApprovalStep)
                .filter(ApprovalStep.chain_id == chain.id)
                .order_by(ApprovalStep.step_index, ApprovalStep.created_at)
                .all()
            )
            state.approval_chain = JobStateApprovalChain(
                id=str(chain.id),
                template_id=str(chain.template_id) if chain.template_id else None,
                status=chain.status,
                current_step=chain.current_step,
                step_history=[
                    JobStateApprovalStep(
                        step_index=s.step_index,
                        step_name=s.step_name,
                        approver_email=s.approver_email,
                        decision=s.decision,
                        notes=s.notes,
                        decided_at=s.decided_at,
                    )
                    for s in steps
                ],
                created_at=chain.created_at,
                completed_at=chain.completed_at,
            )

    # 4. Verdict — same read as /viewer/jobs/{id}/verdict.
    if "verdict" in wanted:
        job_row = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
        auto_passed: bool | None = None
        if job_row is not None and job_row.result_json:
            auto_passed = (job_row.result_json.get("summary") or {}).get("passed")
        state.verdict = JobStateVerdict(
            verdict=job_row.verdict if job_row else None,
            auto_passed=auto_passed,
            verdict_by=job_row.verdict_by if job_row else None,
            verdict_at=job_row.verdict_at.isoformat() if job_row and job_row.verdict_at else None,
            notes=job_row.verdict_notes if job_row else None,
        )

    # 5. Annotations — single SELECT for the annotation rows, single
    # SELECT for all their comments, then stitch in Python. Net O(1)
    # round trips instead of the old N+1 fan-out.
    if "annotations" in wanted:
        ann_rows = (
            db.query(ViewerAnnotation)
            .filter(ViewerAnnotation.job_id == uid)
            .order_by(ViewerAnnotation.created_at.asc())
            .all()
        )
        comments_by_ann: dict[str, list[JobStateAnnotationComment]] = {}
        if ann_rows:
            ann_ids = [r.id for r in ann_rows]
            comment_rows = (
                db.query(ViewerAnnotationComment)
                .filter(ViewerAnnotationComment.annotation_id.in_(ann_ids))
                .order_by(ViewerAnnotationComment.created_at.asc())
                .all()
            )
            for c in comment_rows:
                comments_by_ann.setdefault(str(c.annotation_id), []).append(
                    JobStateAnnotationComment(
                        id=str(c.id),
                        annotation_id=str(c.annotation_id),
                        author_email=c.author_email,
                        body=c.body,
                        created_at=c.created_at.isoformat(),
                        updated_at=c.updated_at.isoformat(),
                    )
                )

        items = [
            JobStateAnnotationItem(
                id=str(r.id),
                job_id=str(r.job_id),
                page_num=r.page_num,
                kind=r.kind,
                geometry=r.geometry_json,
                color=r.color,
                text=r.text,
                author_email=r.author_email,
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat(),
                comments=comments_by_ann.get(str(r.id), []),
            )
            for r in ann_rows
        ]
        by_page: dict[str, int] = {}
        for r in ann_rows:
            key = str(r.page_num)
            by_page[key] = by_page.get(key, 0) + 1

        state.annotations = JobStateAnnotations(
            total=len(ann_rows),
            by_page=by_page,
            items=items,
        )

    return state


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> JobListResponse:
    """List jobs for the current tenant (paginated)."""
    # Clamp pagination parameters to safe ranges
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    base_query = db.query(Job).filter(Job.tenant_id == tenant.id)
    total = base_query.count()
    offset = (page - 1) * page_size
    jobs: list[Job] = (
        base_query.order_by(Job.created_at.desc()).offset(offset).limit(page_size).all()
    )

    return JobListResponse(
        jobs=[
            JobResponse(
                job_id=j.id,
                status=j.status.value if hasattr(j.status, "value") else str(j.status),
                profile_id=j.profile_id,
                file_name=j.file_name,
                file_size=j.file_size,
                page_count=j.page_count,
                created_at=j.created_at,
                completed_at=j.completed_at,
                duration_ms=j.duration_ms,
            )
            for j in jobs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Cancel or delete a job."""
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid job id: '{job_id}' is not a valid UUID.",
        ) from exc

    job: Job | None = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    db.delete(job)
    db.commit()


class RerunAuditResponse(BaseModel):
    """Response shape for ``POST /api/v1/jobs/{job_id}/audit:rerun``."""

    job_id: uuid_mod.UUID
    findings_updated: int = Field(
        ...,
        description=(
            "How many ``JobFinding`` rows received a fresh "
            "verdict. Zero is a valid outcome — it means the "
            "Claude auditor returned all-null verdicts (transport "
            "error on every batch) or the job has no findings. "
            "Not an error."
        ),
    )
    model: str = Field(
        ...,
        description="Auditor model used (e.g. ``claude-haiku-4-5``).",
    )


@router.post(
    "/{job_id}/audit:rerun",
    response_model=RerunAuditResponse,
    status_code=status.HTTP_200_OK,
)
async def rerun_audit(
    job_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RerunAuditResponse:
    """Re-run the customer AI audit against an already-complete job.

    The normal audit runs async at ``run_preflight`` completion
    via ``audit_findings_async``; this endpoint is for the cases
    it isn't useful to resubmit the whole PDF:

      * A Claude prompt tune dropped; ops wants to refresh verdicts
        on historical jobs.
      * Anthropic was down when the async audit first ran and the
        24h retry ceiling expired; the verdicts are all NULL and
        the customer wants them refreshed once service recovers.
      * An admin toggled ``"audit"`` into a tenant's ``ai_features``
        mid-flight for a pilot and wants to populate the audit
        columns on their back-catalogue.

    Bypasses the entitlement gate (so pilots work), but still
    requires ``ANTHROPIC_API_KEY`` to be set — otherwise the helper
    logs + returns zero updates. Requires the caller to own the
    job (the normal ``get_current_tenant`` dependency scopes the
    lookup to the tenant).
    """
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid job id: '{job_id}' is not a valid UUID.",
        ) from exc

    job = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    if job.status != JobStatus.COMPLETE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Job '{job_id}' is {job.status}; can only re-audit "
                "complete jobs."
            ),
        )

    from lintpdf.queue.tasks import run_customer_audit

    try:
        changed = run_customer_audit(db, job, str(job.id), force=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Audit re-run failed: {exc!s}",
        ) from exc

    return RerunAuditResponse(
        job_id=job.id,
        findings_updated=changed,
        model=os.environ.get("LINTPDF_AUDIT_MODEL", "claude-haiku-4-5"),
    )
