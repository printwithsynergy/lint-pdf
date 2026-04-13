"""Celery tasks for async job processing."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from lintpdf.queue.app import celery_app

logger = logging.getLogger(__name__)


def _auto_generate_reports(
    db: Any,
    job: Any,
    result_dict: dict[str, Any],
    pdf_bytes: bytes,
    storage: Any,
) -> None:
    """Auto-generate HTML + PDF reports after job completion.

    Creates report tokens so reports are available immediately via
    ``GET /api/v1/jobs/{id}`` response without requiring a separate
    ``POST /reports`` call.
    """
    import secrets
    import uuid as uuid_mod
    from datetime import datetime, timedelta, timezone

    from lintpdf.api.config import get_settings
    from lintpdf.api.models import BrandProfile, JobFinding, ReportToken, Tenant
    from lintpdf.reports.service import (
        BrandingContext,
        ReportDetailLevel,
        ReportService,
        resolve_branding,
    )

    settings = get_settings()
    service = ReportService(storage, db)

    # Build a result_json with findings for the report generator
    findings = db.query(JobFinding).filter(JobFinding.job_id == job.id).all()
    enriched = dict(result_dict)
    enriched["job_id"] = str(job.id)
    enriched["profile_id"] = job.profile_id
    enriched["duration_ms"] = job.duration_ms or 0
    enriched["file_name"] = job.file_name
    enriched["findings"] = [
        {
            "inspection_id": f.inspection_id,
            "severity": f.severity,
            "message": f.message,
            "page_num": f.page_num,
            "object_id": f.object_id,
            "object_type": f.object_type,
            "source": f.source or "engine",
            "category": f.category,
            "details": f.details,
            "bbox": [f.bbox_x0, f.bbox_y0, f.bbox_x1, f.bbox_y1] if f.bbox_x0 is not None else None,
        }
        for f in findings
    ]
    if "metadata" not in enriched:
        enriched["metadata"] = {}
    enriched["metadata"]["file_key"] = job.file_key

    # Resolve the effective branding from tenant defaults + per-job
    # overrides. Brokers rely on the anonymous path stripping both tenant
    # and LintPDF identity + sanitising PDF metadata.
    tenant_obj = db.query(Tenant).filter(Tenant.id == job.tenant_id).first()

    def _lookup_profile(profile_id: str) -> Any | None:
        try:
            import uuid as _uuid_mod

            pid = _uuid_mod.UUID(profile_id)
        except ValueError:
            return None
        return (
            db.query(BrandProfile)
            .filter(BrandProfile.id == pid, BrandProfile.tenant_id == job.tenant_id)
            .first()
        )

    branding = resolve_branding(
        tenant=tenant_obj,
        job=job,
        brand_param=None,
        default_lintpdf=BrandingContext(),
        lookup_profile=_lookup_profile,
    )

    # Capture the resolved branding on each ReportToken so share links
    # keep the broker's chosen brand even if tenant defaults change later.
    if branding.anonymous:
        token_brand_mode = "anonymous"
        token_brand_profile_id = None
    elif job.brand_profile_id_override is not None:
        token_brand_mode = "profile"
        token_brand_profile_id = job.brand_profile_id_override
    elif tenant_obj and tenant_obj.default_brand_profile_id is not None:
        token_brand_mode = "profile"
        token_brand_profile_id = tenant_obj.default_brand_profile_id
    else:
        token_brand_mode = "lintpdf"
        token_brand_profile_id = None

    report_base_url = settings.report_base_url
    app_base = settings.app_base_url.rstrip("/")
    tokens: dict[str, str] = {}
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    for fmt in ["html", "pdf"]:
        tok = secrets.token_urlsafe(32)
        tokens[fmt] = tok

    # Set cross-links and viewer URL
    branding.pdf_download_url = f"{report_base_url}/r/{tokens['pdf']}.pdf"
    branding.report_url = f"{report_base_url}/r/{tokens['html']}"
    viewer_base = app_base
    if (
        not branding.anonymous
        and tenant_obj
        and getattr(tenant_obj, "app_custom_domain", None)
        and tenant_obj.app_custom_domain_verified
    ):
        viewer_base = f"https://{tenant_obj.app_custom_domain}"
    branding.viewer_url = f"{viewer_base.rstrip('/')}/view/{tokens['html']}"

    for fmt in ["html", "pdf"]:
        content = service._generate_format(
            enriched,
            fmt,
            branding,
            pdf_bytes=pdf_bytes,
            detail_level=ReportDetailLevel.COMPREHENSIVE,
            summary_page="prepend",
        )
        if content is None:
            continue
        storage.upload_report(str(job.tenant_id), str(job.id), fmt, content)
        db.add(
            ReportToken(
                id=uuid_mod.uuid4(),
                job_id=job.id,
                tenant_id=job.tenant_id,
                token=tokens[fmt],
                format=fmt,
                expires_at=expires_at,
                brand_mode=token_brand_mode,
                brand_profile_id=token_brand_profile_id,
            )
        )

    db.commit()
    logger.info(
        "Auto-generated HTML + PDF reports for job %s: %s/r/%s",
        job.id,
        report_base_url,
        tokens.get("html", "?"),
    )


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="lintpdf.preflight.run",
    max_retries=2,
    default_retry_delay=10,
    time_limit=300,
    soft_time_limit=270,
)
def run_preflight(
    self: Any,
    job_id: str,
    profile_id: str,
    file_key: str,
    jdf_overrides: dict[str, Any] | None = None,
    ai_enabled: bool | None = None,
    ai_categories: list[str] | None = None,
    ai_features: list[str] | None = None,
) -> dict[str, Any]:  # skipcq: PY-R1000
    """Execute preflight job.

    Pipeline:
    1. Download PDF from storage
    2. Load preflight profile from registry
    3. Apply JDF overrides (if provided)
    4. Run PreflightOrchestrator
    5. Store results + update job row
    6. Dispatch webhooks

    Args:
        self: Celery task instance (bound).
        job_id: UUID of the job.
        profile_id: Profile to use for preflight.
        file_key: Storage key for the PDF file.
        jdf_overrides: Optional JDF-derived threshold overrides.

    Returns:
        Dict with job results including findings and summary.
    """
    start = time.monotonic()
    logger.info("Starting preflight job %s with profile %s", job_id, profile_id)

    try:
        # Get DB session
        import uuid as uuid_mod

        from lintpdf.api.database import get_db_session
        from lintpdf.api.models import Job, JobFinding, JobStatus

        job_uuid = uuid_mod.UUID(job_id)
        db = get_db_session()
        job: Job | None = None

        try:
            job = db.query(Job).filter(Job.id == job_uuid).first()
            if job is None:
                logger.error("Job %s not found in database", job_id)
                return {"job_id": job_id, "status": "failed", "error": "Job not found"}

            # Mark as processing
            job.status = JobStatus.PROCESSING
            db.commit()

            # ------------------------------------------------------------------
            # Branch on preflight_source: external imports and minimal (viewer
            # only) jobs skip the full analyzer pipeline and finish in a
            # single pass. The engine path continues below.
            # ------------------------------------------------------------------
            from lintpdf.api.models import PreflightSource

            if job.preflight_source == PreflightSource.EXTERNAL:
                return _run_external_preflight(
                    self=self, db=db, job=job, job_id=job_id, start=start
                )
            if job.preflight_source == PreflightSource.MINIMAL:
                return _run_minimal_preflight(self=self, db=db, job=job, job_id=job_id, start=start)

            # Download PDF from storage (try R2, fall back to Redis cache)
            from lintpdf.api.storage import get_storage

            storage = get_storage()
            try:
                pdf_bytes = storage.download_pdf(file_key)
            except Exception as r2_err:
                logger.warning(
                    "R2 download failed for %s: %s (type=%s) — trying Redis cache",
                    job_id,
                    r2_err,
                    type(r2_err).__name__,
                )
                pdf_bytes = None

            if pdf_bytes is None:
                # Fall back to Redis-cached PDF (handles transient R2 outages)
                try:
                    from lintpdf.api.middleware import get_redis_client

                    redis = get_redis_client()
                    if redis is not None:
                        cache_key = f"pdf_cache:{file_key}"
                        pdf_bytes = redis.get(cache_key)
                        if pdf_bytes is not None:
                            logger.info("Retrieved PDF from Redis cache for job %s", job_id)
                except Exception:
                    logger.debug("Redis cache fallback failed for job %s", job_id, exc_info=True)

                if pdf_bytes is None:
                    raise RuntimeError(
                        f"Cannot retrieve PDF: R2 unreachable and no Redis cache for {file_key}"
                    )

            # Load profile
            from lintpdf.profiles.registry import ProfileRegistry

            registry = ProfileRegistry()
            profile = registry.get(profile_id)

            # Apply JDF overrides to profile thresholds if provided
            if jdf_overrides:
                threshold_data = profile.thresholds.model_dump()
                for key, value in jdf_overrides.items():
                    if key in threshold_data:
                        threshold_data[key] = value
                from lintpdf.profiles.schema import ThresholdConfig

                profile = profile.model_copy(
                    update={"thresholds": ThresholdConfig(**threshold_data)}
                )
                if "conformance" in jdf_overrides:
                    profile = profile.model_copy(
                        update={"conformance": jdf_overrides["conformance"]}
                    )

            # Apply per-job AI overrides if provided. ``ai_enabled`` flips the
            # profile's AI on or off; ``ai_categories``/``ai_features`` further
            # narrow which analyzers run. None means "leave profile alone".
            if ai_enabled is not None or ai_categories or ai_features:
                from lintpdf.profiles.schema import AIFeatureConfig

                base_ai = profile.ai or AIFeatureConfig()
                ai_data = base_ai.model_dump()
                if ai_enabled is not None:
                    ai_data["enabled"] = ai_enabled
                if ai_categories:
                    ai_data["categories"] = ai_categories
                if ai_features:
                    ai_data["features"] = ai_features
                profile = profile.model_copy(update={"ai": AIFeatureConfig(**ai_data)})

            # Load AI config if AI is enabled in the profile
            ai_config = None
            if profile.ai and profile.ai.enabled:
                try:
                    from lintpdf.ai.access import get_ai_config

                    ai_config = get_ai_config(job.tenant_id, db)
                except Exception:
                    logger.debug("Could not load AI config for tenant %s", job.tenant_id)

            # Load tenant Pantone overrides (Redis cache → DB fallback)
            custom_pantone: dict | None = None
            try:
                from lintpdf.api.middleware import get_redis_client
                from lintpdf.api.models import TenantColorConfig
                from lintpdf.profiles.icc.pantone_cache import get_overrides, set_overrides

                redis = get_redis_client()
                tenant_id_str = str(job.tenant_id)
                custom_pantone = get_overrides(redis, tenant_id_str)
                if custom_pantone is None:
                    color_config = (
                        db.query(TenantColorConfig)
                        .filter(TenantColorConfig.tenant_id == job.tenant_id)
                        .first()
                    )
                    custom_pantone = color_config.custom_pantone_overrides if color_config else None
                    if custom_pantone:
                        set_overrides(redis, tenant_id_str, custom_pantone)
            except Exception:
                logger.debug(
                    "Could not load Pantone overrides for tenant %s",
                    job.tenant_id,
                    exc_info=True,
                )

            # Run preflight orchestrator
            from lintpdf.profiles.orchestrator import PreflightOrchestrator

            orchestrator = PreflightOrchestrator(
                profile,
                profile_id=profile_id,
                ai_config=ai_config,
                pdf_bytes=pdf_bytes,
                custom_pantone_overrides=custom_pantone,
            )
            result = orchestrator.run(pdf_bytes)

            duration_ms = int((time.monotonic() - start) * 1000)

            # Serialize result for storage
            result_dict = {
                "summary": {
                    "total_findings": result.summary.total_findings,
                    "error_count": result.summary.error_count,
                    "warning_count": result.summary.warning_count,
                    "advisory_count": result.summary.advisory_count,
                    "passed": result.summary.passed,
                    "page_count": result.summary.page_count,
                    "file_size_bytes": result.summary.file_size_bytes,
                },
                "metadata": result.metadata,
            }

            # Upload results JSON to storage (best-effort — results are in DB too)
            try:
                storage.upload_results(
                    tenant_id=str(job.tenant_id),
                    job_id=job_id,
                    results_json=json.dumps(result_dict).encode(),
                )
            except Exception:
                logger.warning(
                    "Failed to upload results to R2 for job %s — results stored in DB", job_id
                )

            # Update job row
            import datetime

            job.status = JobStatus.COMPLETE
            job.result_json = result_dict
            job.page_count = result.summary.page_count
            job.duration_ms = duration_ms
            job.completed_at = datetime.datetime.now(datetime.UTC)

            # Store individual findings
            ai_features_used: set[tuple[str, str]] = set()
            for finding in result.findings:
                bbox = finding.bbox
                db.add(
                    JobFinding(
                        job_id=job.id,
                        inspection_id=finding.inspection_id,
                        severity=finding.severity.value,
                        message=finding.message,
                        page_num=finding.page_num,
                        details=finding.details if finding.details else None,
                        source=finding.source,
                        category=finding.category if finding.category else None,
                        bbox_x0=bbox[0] if bbox else None,
                        bbox_y0=bbox[1] if bbox else None,
                        bbox_x1=bbox[2] if bbox else None,
                        bbox_y1=bbox[3] if bbox else None,
                        object_id=finding.object_id,
                        object_type=finding.object_type,
                    )
                )
                if finding.source == "ai" and finding.category:
                    ai_features_used.add(
                        (
                            finding.category,
                            finding.inspection_id.split(".")[1]
                            if "." in finding.inspection_id
                            else finding.category,
                        )
                    )

            # Deduct AI credits for features used
            if ai_features_used and ai_config:
                try:
                    from lintpdf.ai.credits import deduct_credits

                    for category, feature in ai_features_used:
                        deduct_credits(
                            tenant_id=job.tenant_id,
                            job_id=job.id,
                            category=category,
                            feature=feature,
                            credit_amount=1,
                            processing_time_ms=duration_ms,
                            result_summary={
                                "findings_count": len(
                                    [
                                        f
                                        for f in result.findings
                                        if f.source == "ai" and f.category == category
                                    ]
                                )
                            },
                            db=db,
                        )
                except Exception:
                    logger.exception("Failed to deduct AI credits for job %s", job_id)

            db.commit()

            logger.info("Completed preflight job %s in %dms", job_id, duration_ms)

            # Dispatch webhooks for this tenant
            _dispatch_tenant_webhooks(
                db,
                job.tenant_id,
                "job.completed",
                {
                    "job_id": job_id,
                    "status": "complete",
                    "profile_id": profile_id,
                    "duration_ms": duration_ms,
                    "summary": result_dict["summary"],
                },
            )

            # Auto-generate HTML + PDF reports so they're ready immediately.
            # Callers get report URLs from GET /api/v1/jobs/{id} without a
            # separate POST /reports step.
            try:
                _auto_generate_reports(db, job, result_dict, pdf_bytes, storage)
            except Exception:
                logger.exception("Auto report generation failed for job %s (non-fatal)", job_id)

            # Kick off async tile pre-rendering for the viewer (non-blocking)
            try:
                prerender_viewer_tiles.delay(job_id, str(job.tenant_id), file_key)
            except Exception:
                logger.warning("Failed to queue tile pre-render for job %s", job_id)

            return {
                "job_id": job_id,
                "profile_id": profile_id,
                "status": "complete",
                "duration_ms": duration_ms,
            }

        except Exception as exc:
            # Update job as failed
            try:
                if job is not None:
                    import datetime

                    job.status = JobStatus.FAILED
                    job.error_message = str(exc)
                    job.completed_at = datetime.datetime.now(datetime.UTC)
                    job.duration_ms = int((time.monotonic() - start) * 1000)
                    db.commit()

                    _dispatch_tenant_webhooks(
                        db,
                        job.tenant_id,
                        "job.failed",
                        {
                            "job_id": job_id,
                            "status": "failed",
                            "error": str(exc),
                        },
                    )
            except Exception:
                logger.exception("Failed to update job %s status to failed", job_id)

            raise

        finally:
            db.close()

    except Exception as exc:
        logger.exception("Preflight job %s failed: %s", job_id, exc)

        # Retry on transient failures
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc

        return {
            "job_id": job_id,
            "profile_id": profile_id,
            "status": "failed",
            "error": str(exc),
        }


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lintpdf.queue.tasks.cleanup_expired_reports",
)
def cleanup_expired_reports() -> dict[str, Any]:
    """Delete expired report tokens and their storage files.

    Runs daily via Celery Beat.
    """
    from lintpdf.api.database import get_db_session
    from lintpdf.api.storage import get_storage
    from lintpdf.reports.service import ReportService

    db = get_db_session()
    try:
        storage = get_storage()
        service = ReportService(storage, db)
        count = service.cleanup_expired()
        logger.info("Cleaned up %d expired report tokens", count)
        return {"cleaned": count}
    finally:
        db.close()


# --- White-label custom domain DNS verification probe --------------------


def _resolve_cname(hostname: str) -> str | None:
    """Return the CNAME target for ``hostname`` (FQDN, lowercase, no trailing dot).

    Returns None if the lookup fails or no CNAME is set. Wrapped so the task
    can be unit-tested with a simple monkeypatch, and so the slightly odd
    dnspython import surface is isolated.
    """
    try:
        import dns.resolver  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("dnspython not installed — DNS probe disabled")
        return None

    try:
        answers = dns.resolver.resolve(hostname, "CNAME", lifetime=5.0)
    except Exception as exc:
        logger.debug("CNAME lookup failed for %s: %s", hostname, exc)
        return None

    for answer in answers:
        target = str(answer.target).rstrip(".").lower()
        if target:
            return target
    return None


# CNAME targets we consider "correctly pointed at LintPDF". Customers can
# point at either the engine's primary host or Railway's edge (which is
# technically what a Railway custom domain resolves to once registered).
_ACCEPTABLE_CNAME_TARGETS: tuple[str, ...] = (
    "reports.lintpdf.com",
    "api.lintpdf.com",
    "app.lintpdf.com",
    "lintpdf-production.up.railway.app",
    "backboard.railway.app",
)


def _cname_is_acceptable(target: str | None) -> bool:
    if not target:
        return False
    target = target.rstrip(".").lower()
    return any(
        target == t or target.endswith(f".{t}") or target.endswith(t)
        for t in _ACCEPTABLE_CNAME_TARGETS
    )


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lintpdf.queue.tasks.probe_pending_custom_domains",
)
def probe_pending_custom_domains() -> dict[str, Any]:
    """Check every pending custom report domain's CNAME; auto-activate when live.

    For each unverified domain (tenant-level OR brand-profile-level):

      1. Do a CNAME lookup.
      2. If CNAME points at an acceptable LintPDF host:
         a. Try to register the domain on Railway via GraphQL.
         b. If created / already_exists, flip verified=True in the DB.
      3. If CNAME doesn't match or Railway is disabled, leave pending.

    Runs on a 5-minute Celery beat schedule. Safe to run concurrently
    (commits per-row) and idempotent (verified rows are ignored).
    """
    from lintpdf.api.database import get_db_session
    from lintpdf.api.models import BrandProfile, Tenant
    from lintpdf.integrations.railway import RailwayClient

    result: dict[str, Any] = {
        "checked": 0,
        "activated": 0,
        "railway_registered": 0,
        "cname_mismatch": 0,
        "railway_disabled": 0,
        "errors": 0,
    }

    client = RailwayClient()
    db = get_db_session()
    try:
        pending_tenants: list[Tenant] = (
            db.query(Tenant)
            .filter(
                Tenant.brand_custom_domain.isnot(None),
                Tenant.brand_custom_domain_verified.is_(False),
            )
            .all()
        )
        pending_profiles: list[BrandProfile] = (
            db.query(BrandProfile)
            .filter(
                BrandProfile.custom_domain.isnot(None),
                BrandProfile.custom_domain_verified.is_(False),
            )
            .all()
        )

        for tenant in pending_tenants:
            result["checked"] += 1
            domain = tenant.brand_custom_domain
            if not domain:
                continue
            cname = _resolve_cname(domain)
            if not _cname_is_acceptable(cname):
                result["cname_mismatch"] += 1
                logger.info(
                    "Custom domain %s not yet pointed at LintPDF (CNAME=%s)",
                    domain,
                    cname,
                )
                continue

            outcome = client.add_custom_domain(domain)
            if outcome.status in ("created", "already_exists"):
                result["railway_registered"] += 1
                tenant.brand_custom_domain_verified = True
                db.commit()
                result["activated"] += 1
                logger.info(
                    "Activated tenant custom domain %s (tenant=%s, railway=%s)",
                    domain,
                    tenant.id,
                    outcome.status,
                )
            elif outcome.status == "disabled":
                result["railway_disabled"] += 1
                # Railway auto-registration is off; ops flips verified by hand.
            elif outcome.status == "unauthorized":
                result["railway_disabled"] += 1
                logger.warning(
                    "Railway rejected domain %s — project token lacks permission; "
                    "ops must mark it active manually",
                    domain,
                )
            else:
                result["errors"] += 1
                logger.warning(
                    "Railway add_custom_domain failed for %s: %s",
                    domain,
                    outcome.message,
                )

        for profile in pending_profiles:
            result["checked"] += 1
            domain = profile.custom_domain
            if not domain:
                continue
            cname = _resolve_cname(domain)
            if not _cname_is_acceptable(cname):
                result["cname_mismatch"] += 1
                continue

            outcome = client.add_custom_domain(domain)
            if outcome.status in ("created", "already_exists"):
                result["railway_registered"] += 1
                profile.custom_domain_verified = True
                db.commit()
                result["activated"] += 1
            elif outcome.status in ("disabled", "unauthorized"):
                result["railway_disabled"] += 1
            else:
                result["errors"] += 1
                logger.warning(
                    "Railway add_custom_domain failed for profile domain %s: %s",
                    domain,
                    outcome.message,
                )

        # ── App/viewer custom domains ──
        pending_app_tenants: list[Tenant] = (
            db.query(Tenant)
            .filter(
                Tenant.app_custom_domain.isnot(None),
                Tenant.app_custom_domain_verified.is_(False),
            )
            .all()
        )
        for tenant in pending_app_tenants:
            result["checked"] += 1
            domain = tenant.app_custom_domain
            if not domain:
                continue
            cname = _resolve_cname(domain)
            if not _cname_is_acceptable(cname):
                result["cname_mismatch"] += 1
                continue
            outcome = client.add_custom_domain(domain, service_id=client.app_service_id)
            if outcome.status in ("created", "already_exists"):
                result["railway_registered"] += 1
                tenant.app_custom_domain_verified = True
                db.commit()
                result["activated"] += 1
                logger.info("Activated tenant app domain %s (tenant=%s)", domain, tenant.id)
            elif outcome.status in ("disabled", "unauthorized"):
                result["railway_disabled"] += 1
            else:
                result["errors"] += 1

        pending_app_profiles: list[BrandProfile] = (
            db.query(BrandProfile)
            .filter(
                BrandProfile.app_custom_domain.isnot(None),
                BrandProfile.app_custom_domain_verified.is_(False),
            )
            .all()
        )
        for profile in pending_app_profiles:
            result["checked"] += 1
            domain = profile.app_custom_domain
            if not domain:
                continue
            cname = _resolve_cname(domain)
            if not _cname_is_acceptable(cname):
                result["cname_mismatch"] += 1
                continue
            outcome = client.add_custom_domain(domain, service_id=client.app_service_id)
            if outcome.status in ("created", "already_exists"):
                result["railway_registered"] += 1
                profile.app_custom_domain_verified = True
                db.commit()
                result["activated"] += 1
            elif outcome.status in ("disabled", "unauthorized"):
                result["railway_disabled"] += 1
            else:
                result["errors"] += 1

        return result
    finally:
        db.close()


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lintpdf.viewer.prerender_tiles",
    time_limit=120,
    soft_time_limit=110,
    ignore_result=True,
)
def prerender_viewer_tiles(
    job_id: str,
    tenant_id: str,
    file_key: str,
) -> dict[str, Any]:
    """Pre-render page tiles at default DPI for the interactive viewer.

    Runs asynchronously after a preflight job completes. Renders composite
    page images at 150 DPI (default viewer zoom) and 72 DPI (thumbnail strip),
    then stores them in S3 for instant loading when the viewer opens.
    """
    from lintpdf.ai.rendering import get_page_count, render_page_to_image
    from lintpdf.api.storage import get_storage

    storage = get_storage()
    try:
        pdf_bytes = storage.download_pdf(file_key)
    except Exception:
        logger.warning("Pre-render: could not download PDF for job %s", job_id)
        return {"job_id": job_id, "status": "skipped", "reason": "pdf_not_found"}

    page_count = get_page_count(pdf_bytes)
    rendered = 0

    for page_num in range(1, min(page_count + 1, 201)):  # Cap at 200 pages
        for dpi in (150, 72):
            cache_key = f"{tenant_id}/{job_id}/tiles/p{page_num}_d{dpi}.png"
            try:
                tile_bytes = render_page_to_image(pdf_bytes, page_num, dpi=dpi)
                storage.upload_raw(cache_key, tile_bytes, content_type="image/png")
                rendered += 1
            except Exception:
                logger.debug("Pre-render failed for page %d at %d DPI", page_num, dpi)

    logger.info("Pre-rendered %d tiles for job %s (%d pages)", rendered, job_id, page_count)
    return {"job_id": job_id, "status": "complete", "tiles_rendered": rendered}


def _dispatch_tenant_webhooks(
    db: Any,
    tenant_id: Any,
    event: str,
    payload: dict[str, Any],
) -> None:
    """Dispatch webhooks for a tenant asynchronously."""
    from lintpdf.api.models import WebhookEndpoint

    endpoints = (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.tenant_id == tenant_id, WebhookEndpoint.is_active.is_(True))
        .all()
    )

    for endpoint in endpoints:
        # Only dispatch if endpoint subscribes to this event (empty = all)
        if endpoint.events and event not in endpoint.events:
            continue
        dispatch_webhook.delay(
            webhook_url=endpoint.url,
            webhook_secret=endpoint.secret,
            event=event,
            payload=payload,
        )


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lintpdf.webhook.dispatch",
    max_retries=3,
    default_retry_delay=5,
)
def dispatch_webhook(
    webhook_url: str,
    webhook_secret: str,
    event: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch a webhook notification.

    Args:
        webhook_url: URL to deliver the webhook to.
        webhook_secret: HMAC secret for signing.
        event: Event type (e.g. "job.completed").
        payload: Event payload dict.

    Returns:
        Delivery status dict.
    """
    import hashlib
    import hmac

    import httpx

    # Sign the payload
    body = json.dumps(payload, sort_keys=True, default=str)
    signature = hmac.new(
        webhook_secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    try:
        response = httpx.post(
            webhook_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-LintPDF-Event": event,
                "X-LintPDF-Signature": f"sha256={signature}",
            },
            timeout=10.0,
        )
        response.raise_for_status()

        return {
            "status": "delivered",
            "url": webhook_url,
            "event": event,
            "status_code": response.status_code,
        }

    except Exception as exc:
        logger.warning("Webhook delivery to %s failed: %s", webhook_url, exc)
        return {
            "status": "failed",
            "url": webhook_url,
            "event": event,
            "error": str(exc),
        }


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lintpdf.queue.tasks.process_approval_timeouts",
)
def process_approval_timeouts() -> dict[str, Any]:
    """Celery Beat: handle approval steps whose expires_at has passed.

    Each step's on_timeout setting determines behavior:
    - "reject": mark chain rejected
    - "advance": treat as approved
    - "notify": re-notify approvers, reset expiry
    """
    from lintpdf.api.database import get_db_session
    from lintpdf.approvals.service import process_timeouts

    db = get_db_session()
    try:
        return process_timeouts(db)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# External import + minimal preflight branches
# ---------------------------------------------------------------------------


def _extract_essentials_dict(pdf_bytes: bytes) -> dict[str, Any]:
    """Run :func:`extract_viewer_essentials` and return a JSON-safe dict.

    Used by both the external-import and minimal preflight branches to
    populate ``Job.result_json.metadata`` without invoking the full
    analyzer pipeline.
    """
    from lintpdf.profiles.orchestrator import extract_viewer_essentials

    essentials = extract_viewer_essentials(pdf_bytes)
    return {
        "pdf_version": essentials.pdf_version,
        "page_count": essentials.page_count,
        "is_encrypted": essentials.is_encrypted,
        "pages": essentials.pages,
        "info_dict": essentials.info_dict,
    }


def _download_pdf_with_fallback(storage: Any, file_key: str, job_id: str) -> bytes:
    """PDF download helper shared by the import / minimal paths.

    Mirrors the engine path's R2→Redis fallback logic so a transient R2
    outage doesn't block import / minimal jobs either.
    """
    try:
        pdf_bytes = storage.download_pdf(file_key)
    except Exception as r2_err:
        logger.warning(
            "R2 download failed for %s: %s — trying Redis cache",
            job_id,
            r2_err,
        )
        pdf_bytes = None
    if pdf_bytes is None:
        try:
            from lintpdf.api.middleware import get_redis_client

            redis = get_redis_client()
            if redis is not None:
                pdf_bytes = redis.get(f"pdf_cache:{file_key}")
        except Exception:
            logger.debug("Redis cache fallback failed for job %s", job_id, exc_info=True)
    if pdf_bytes is None:
        raise RuntimeError(f"Cannot retrieve PDF: R2 unreachable and no Redis cache for {file_key}")
    return pdf_bytes


def _persist_imported_findings(
    db: Any,
    job: Any,
    findings: list[Any],
) -> None:
    """Write a list of :class:`Finding` to the ``job_findings`` table."""
    from lintpdf.api.models import JobFinding

    for finding in findings:
        bbox = finding.bbox
        db.add(
            JobFinding(
                job_id=job.id,
                inspection_id=finding.inspection_id,
                severity=finding.severity.value,
                message=finding.message,
                page_num=finding.page_num,
                details=finding.details if finding.details else None,
                source=finding.source,
                category=finding.category if finding.category else None,
                bbox_x0=bbox[0] if bbox else None,
                bbox_y0=bbox[1] if bbox else None,
                bbox_x1=bbox[2] if bbox else None,
                bbox_y1=bbox[3] if bbox else None,
                object_id=finding.object_id,
                object_type=finding.object_type,
            )
        )


def _finalize_non_engine_job(
    db: Any,
    job: Any,
    job_id: str,
    start: float,
    result_dict: dict[str, Any],
    pdf_bytes: bytes,
    storage: Any,
) -> dict[str, Any]:
    """Shared finalisation for external-import and minimal runs.

    Commits the job row, dispatches webhooks, auto-generates reports,
    and kicks off tile pre-rendering — matching engine-path semantics so
    downstream viewer / report behaviour is uniform.
    """
    import datetime as _dt

    from lintpdf.api.models import JobStatus

    duration_ms = int((time.monotonic() - start) * 1000)

    job.status = JobStatus.COMPLETE
    job.result_json = result_dict
    job.page_count = result_dict.get("summary", {}).get("page_count", job.page_count or 0)
    job.duration_ms = duration_ms
    job.completed_at = _dt.datetime.now(_dt.UTC)
    db.commit()

    _dispatch_tenant_webhooks(
        db,
        job.tenant_id,
        "job.completed",
        {
            "job_id": job_id,
            "status": "complete",
            "profile_id": job.profile_id,
            "duration_ms": duration_ms,
            "summary": result_dict["summary"],
            "preflight_source": str(job.preflight_source),
        },
    )

    try:
        _auto_generate_reports(db, job, result_dict, pdf_bytes, storage)
    except Exception:
        logger.exception("Auto report generation failed for job %s (non-fatal)", job_id)

    try:
        prerender_viewer_tiles.delay(job_id, str(job.tenant_id), job.file_key)
    except Exception:
        logger.warning("Failed to queue tile pre-render for job %s", job_id)

    return {
        "job_id": job_id,
        "profile_id": job.profile_id,
        "status": "complete",
        "duration_ms": duration_ms,
        "preflight_source": str(job.preflight_source),
    }


def _run_external_preflight(
    *, self: Any, db: Any, job: Any, job_id: str, start: float
) -> dict[str, Any]:
    """Ingest a third-party preflight report and persist its findings.

    Pipeline:

    1. Download the PDF (for viewer essentials + later capability fill-in).
    2. Download the imported report blob stored by the submission route.
    3. Parse it via :func:`parse_external_report` (format auto-detect or
       explicit ``job.external_format``).
    4. Write findings to ``job_findings`` with ``source = external:<parser>``.
    5. Merge parser-reported capabilities onto ``job.data_capabilities``.
    6. Finalise (status, reports, webhooks) like the engine path does.
    """
    from lintpdf.api.models import JobImportedReport, default_capabilities
    from lintpdf.api.storage import get_storage
    from lintpdf.imports import parse_external_report

    storage = get_storage()

    # --- PDF ---------------------------------------------------------------
    pdf_bytes = _download_pdf_with_fallback(storage, job.file_key, job_id)

    # --- Imported report ---------------------------------------------------
    imported_row: JobImportedReport | None = (
        db.query(JobImportedReport)
        .filter(JobImportedReport.job_id == job.id)
        .order_by(JobImportedReport.parsed_at.desc())
        .first()
    )
    if imported_row is None:
        raise RuntimeError("External preflight requested but no imported report found for job")

    report_bytes = storage.download_raw(imported_row.raw_blob_key)
    if report_bytes is None:
        raise RuntimeError(f"Imported preflight report blob missing: {imported_row.raw_blob_key}")

    # ``custom`` means a tenant-defined mapping parsed the payload. The
    # mapping id is stashed on ``imported_row.source_metadata`` at submit
    # time so we can round-trip the config without duplicating it here.
    if job.external_format == "custom":
        from lintpdf.api.models import TenantImportMapping
        from lintpdf.imports.custom import CustomMappingParser

        mapping_id = (imported_row.source_metadata or {}).get("mapping_id")
        if not mapping_id:
            raise RuntimeError("external_format='custom' requires mapping_id in source_metadata")
        mapping_row = (
            db.query(TenantImportMapping).filter(TenantImportMapping.id == mapping_id).first()
        )
        if mapping_row is None:
            raise RuntimeError(f"TenantImportMapping {mapping_id} not found — cannot parse")
        parser = CustomMappingParser(mapping_row.config, mapping_id=str(mapping_row.id))
        imported = parser.parse(report_bytes)
        resolved_format = "custom"
    else:
        imported, resolved_format = parse_external_report(report_bytes, fmt=job.external_format)

    # --- Persist findings --------------------------------------------------
    _persist_imported_findings(db, job, imported.findings)

    # --- Essentials + capabilities ----------------------------------------
    essentials = _extract_essentials_dict(pdf_bytes)

    caps = default_capabilities(False)
    caps["metadata"] = True
    caps["thumbnails"] = True
    for key, value in (imported.capabilities or {}).items():
        caps[key] = bool(value)
    job.data_capabilities = caps
    job.external_format = resolved_format
    imported_row.format = resolved_format
    imported_row.source_metadata = imported.source_metadata or imported_row.source_metadata
    imported_row.parser_version = imported.parser_version

    # --- Summary -----------------------------------------------------------
    errors = sum(1 for f in imported.findings if f.severity.value == "error")
    warnings = sum(1 for f in imported.findings if f.severity.value == "warning")
    advisory = sum(1 for f in imported.findings if f.severity.value == "advisory")
    summary = {
        "total_findings": len(imported.findings),
        "error_count": errors,
        "warning_count": warnings,
        "advisory_count": advisory,
        "passed": errors == 0,
        "page_count": essentials["page_count"],
        "file_size_bytes": len(pdf_bytes),
    }
    result_dict = {
        "summary": summary,
        "metadata": {
            **essentials,
            "preflight_source": "external",
            "external_format": resolved_format,
            "external_tool": (imported.source_metadata or {}).get("tool"),
        },
    }

    return _finalize_non_engine_job(db, job, job_id, start, result_dict, pdf_bytes, storage)


def _run_minimal_preflight(
    *, self: Any, db: Any, job: Any, job_id: str, start: float
) -> dict[str, Any]:
    """Extract viewer essentials only — no analyzers, no findings.

    Every finding-driven viewer tool is marked unavailable and can be
    filled in on demand via :func:`fill_capability`.
    """
    from lintpdf.api.models import default_capabilities
    from lintpdf.api.storage import get_storage

    storage = get_storage()
    pdf_bytes = _download_pdf_with_fallback(storage, job.file_key, job_id)
    essentials = _extract_essentials_dict(pdf_bytes)

    caps = default_capabilities(False)
    caps["metadata"] = True
    caps["thumbnails"] = True
    job.data_capabilities = caps

    summary = {
        "total_findings": 0,
        "error_count": 0,
        "warning_count": 0,
        "advisory_count": 0,
        "passed": True,
        "page_count": essentials["page_count"],
        "file_size_bytes": len(pdf_bytes),
    }
    result_dict = {
        "summary": summary,
        "metadata": {
            **essentials,
            "preflight_source": "minimal",
        },
    }

    return _finalize_non_engine_job(db, job, job_id, start, result_dict, pdf_bytes, storage)


# ---------------------------------------------------------------------------
# Capability fill-in (on-demand single-analyzer runs)
# ---------------------------------------------------------------------------

#: Capability name → (analyzer factory callable, capability key). Keeping this
#: dict small and explicit means the viewer can only trigger analyzers we've
#: deliberately wired for on-demand use. New entries should be vetted for
#: runtime cost — fill-in runs inline on the Celery worker.
_CAPABILITY_ANALYZERS: dict[str, str] = {
    "separations": "SpotColorAnalyzer",
    "tac": "InkCoverageAnalyzer",
    "fonts": "FontAnalyzer",
    "images": "ImageAnalyzer",
}


def capability_supports_fillin(name: str) -> bool:
    """Whether the viewer may call fill-in for this capability."""
    return name in _CAPABILITY_ANALYZERS


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lintpdf.viewer.fill_capability",
    max_retries=1,
    default_retry_delay=5,
    time_limit=120,
    soft_time_limit=90,
)
def fill_capability(job_id: str, capability: str) -> dict[str, Any]:
    """Run the single analyzer responsible for ``capability`` on a job's PDF.

    Called from the viewer when a user clicks "Load" on a tool whose
    backing data wasn't provided (typical for imported PitStop / callas
    reports that lack TAC / separations data, and for minimal jobs).

    On success:

    * Appends new :class:`Finding` rows if the analyzer produced any.
    * Flips ``job.data_capabilities[capability] = True``.
    """
    import uuid as uuid_mod

    from lintpdf.api.database import get_db_session
    from lintpdf.api.models import Job
    from lintpdf.api.storage import get_storage

    if not capability_supports_fillin(capability):
        return {"status": "unsupported", "capability": capability}

    db = get_db_session()
    try:
        job = db.query(Job).filter(Job.id == uuid_mod.UUID(job_id)).first()
        if job is None:
            return {"status": "not_found", "job_id": job_id}

        storage = get_storage()
        pdf_bytes = _download_pdf_with_fallback(storage, job.file_key, job_id)

        analyzer = _build_fillin_analyzer(capability)
        if analyzer is None:
            return {"status": "unsupported", "capability": capability}

        from lintpdf.profiles.orchestrator import PreflightOrchestrator

        document, events = PreflightOrchestrator._parse_and_interpret(pdf_bytes)
        findings = list(analyzer.analyze(document, events))
        _persist_imported_findings(db, job, findings)

        caps = dict(job.data_capabilities or {})
        caps[capability] = True
        job.data_capabilities = caps
        db.commit()

        return {
            "status": "complete",
            "job_id": job_id,
            "capability": capability,
            "new_findings": len(findings),
        }
    except Exception:
        logger.exception("fill_capability failed for job %s / %s", job_id, capability)
        raise
    finally:
        db.close()


def _build_fillin_analyzer(capability: str) -> Any | None:
    """Instantiate the analyzer registered for a capability, or None."""
    from lintpdf.analyzers import (
        FontAnalyzer,
        ImageAnalyzer,
        InkCoverageAnalyzer,
        SpotColorAnalyzer,
    )

    # Layers / OCG — analyzer exists as part of DocumentAnalyzer today; when
    # a dedicated OCGAnalyzer lands we can wire it here. Until then we flag
    # the capability unsupported so the viewer hides the control.
    if capability == "separations":
        return SpotColorAnalyzer()
    if capability == "tac":
        return InkCoverageAnalyzer()
    if capability == "fonts":
        return FontAnalyzer()
    if capability == "images":
        return ImageAnalyzer()
    return None
