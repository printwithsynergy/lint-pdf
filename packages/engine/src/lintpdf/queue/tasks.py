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

    Auto-gen always produces URL-only tokens; the inline return mode is
    an opt-in surface of ``POST /reports`` only. Webhook payloads and
    ``GET /jobs/{id}.reports`` consumers can keep assuming ``url`` is
    populated on every row minted here.
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
    # Matches the app-wide default (10 min hard / 9 min soft). AI-heavy
    # profiles (full-ai-scan) can legitimately run 6–8 minutes on larger
    # PDFs; the previous 5-minute cap silently killed them, leaving the
    # Job row stuck in "processing".
    time_limit=600,
    soft_time_limit=540,
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

            # Bail out cleanly on retry redelivery. ``task_acks_late=True``
            # means Celery returns the task to the queue if a worker
            # crashes mid-execution, even when a prior attempt already
            # finished successfully. Re-running unconditionally would
            # reset ``status`` back to PROCESSING (line below), masking
            # the COMPLETE/FAILED state and leaving the job looking stuck
            # until the 20-min reaper cleans up. Terminal states are
            # final -- skip and ack.
            if job.status in (JobStatus.COMPLETE, JobStatus.FAILED):
                logger.info(
                    "Job %s already in terminal state %s; skipping redelivery",
                    job_id,
                    job.status,
                )
                return {
                    "job_id": job_id,
                    "status": job.status.value if hasattr(job.status, "value") else str(job.status),
                    "skipped": "redelivery_after_terminal",
                }

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

            # Apply the universal per-call override envelope captured
            # at submit time. This is the single path for every
            # non-JDF override the caller sent: checks enabled/disabled,
            # severity overrides / max_severity, thresholds beyond the
            # JDF subset, color workflow, AI config. Applied AFTER JDF
            # so explicit envelope values beat the JDF-derived ones
            # when both are present.
            job_overrides = job.overrides if job is not None else None
            if job_overrides:
                from lintpdf.overrides import (
                    OverridesEnvelope,
                    apply_profile_overrides,
                )

                try:
                    envelope = OverridesEnvelope.model_validate(job_overrides)
                    profile = apply_profile_overrides(profile, envelope)
                except Exception:
                    # Persisted envelopes should always round-trip, but
                    # if a future schema change drifts, fall back to the
                    # profile rather than failing the whole job. Log so
                    # the drift is visible.
                    logger.exception(
                        "Failed to apply overrides envelope for job %s — "
                        "running with profile defaults",
                        job_id,
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

            # Serialize result for storage. Findings are denormalised
            # into a plain dict list so downstream report generators
            # (annotated_pdf, annotated_pdf_markup, html, json, xml) can
            # draw overlays without round-tripping through the DB.
            # Previously the annotated PDF pipeline always saw an empty
            # findings list here because this dict only carried summary
            # + metadata -- the overlay never rendered a single bbox
            # even when the analyzers computed perfectly good ones.
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
                "findings": [
                    {
                        "inspection_id": f.inspection_id,
                        "severity": (
                            f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                        ),
                        "message": f.message,
                        "page_num": f.page_num,
                        "bbox": list(f.bbox) if f.bbox else None,
                        "details": f.details,
                        "source": f.source or "engine",
                        "category": f.category,
                        "object_id": f.object_id,
                        "object_type": f.object_type,
                    }
                    for f in result.findings
                ],
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
            # Also emit the umbrella state_changed event so subscribers
            # that only want one webhook per logical change don't need
            # to listen to job.completed + approval.* + verdict.* etc.
            try:
                from lintpdf.webhooks.events import fire_job_state_changed

                fire_job_state_changed(
                    db, job, job.tenant_id, reason="job.completed"
                )
            except Exception:
                logger.exception(
                    "job.state_changed emit failed for job %s", job_id
                )

            # Auto-generate HTML + PDF reports so they're ready immediately.
            # Callers get report URLs from GET /api/v1/jobs/{id} without a
            # separate POST /reports step.
            try:
                _auto_generate_reports(db, job, result_dict, pdf_bytes, storage)
            except Exception:
                logger.exception("Auto report generation failed for job %s (non-fatal)", job_id)

            # Kick off async tile pre-warming for the viewer (non-blocking).
            # Uses the Redis-coordinated warm_viewer_tiles task so the
            # frontend can show progress and poll for completion.
            enqueue_tile_warming(job_id)

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
    name="lintpdf.queue.tasks.reap_stale_jobs",
)
def reap_stale_jobs() -> dict[str, Any]:
    """Safety net for jobs stuck in ``processing`` longer than any legit run.

    The primary defense against abandoned in-flight work is:

    1. Railway ``gracefulShutdownTimeoutSec`` on the worker services, so
       redeploys wait for the current task to finish instead of SIGKILL.
    2. Celery ``task_reject_on_worker_lost = True``, which re-delivers
       abandoned tasks to another worker.
    3. Celery ``time_limit = 600`` on the preflight task, so runaway jobs
       self-terminate and flip the row to ``failed``.

    This reaper only fires when all three of those miss — broker eviction,
    database-transaction-rolled-back-but-cancelled-after-commit, worker
    crash during the final DB write. We run it every 5 minutes and mark
    any ``processing`` job whose ``created_at`` is older than the hard
    time limit + a generous safety margin as ``failed``. Never cancels
    work that could still legitimately be running.
    """
    import datetime as _dt
    import uuid as _uuid

    from lintpdf.api.database import get_db_session
    from lintpdf.api.models import Job, JobStatus

    # Hard timeout (10 min) + 2 min grace. Anything still "processing"
    # after 12 minutes is definitively dead -- the worker would have
    # been hard-killed by Celery's time_limit + redelivery would have
    # short-circuited via the terminal-state guard at the top of
    # run_preflight. Tighter than the previous 20 min so customers see
    # a clear "failed" state sooner instead of a stuck dashboard.
    stale_after = _dt.timedelta(minutes=12)
    cutoff = _dt.datetime.now(_dt.UTC) - stale_after

    db = get_db_session()
    try:
        stuck: list[Job] = (
            db.query(Job).filter(Job.status == JobStatus.PROCESSING, Job.created_at < cutoff).all()
        )
        reaped = 0
        for job in stuck:
            job.status = JobStatus.FAILED
            job.error_message = (
                "Job abandoned by worker (reaped after "
                f"{int(stale_after.total_seconds() / 60)}-minute timeout). "
                "Please resubmit."
            )
            job.completed_at = _dt.datetime.now(_dt.UTC)
            reaped += 1
            # Fire the standard failure webhook so downstream callers
            # (dashboard, email, integrations) aren't left hanging.
            try:
                _dispatch_tenant_webhooks(
                    db,
                    job.tenant_id,
                    "job.failed",
                    {
                        "job_id": str(job.id),
                        "status": "failed",
                        "error": job.error_message,
                        "reaped": True,
                    },
                )
            except Exception:
                logger.exception("Reaper: webhook dispatch failed for job %s", job.id)
        if reaped:
            db.commit()
            logger.warning(
                "Reaped %d stale processing job(s): %s",
                reaped,
                ", ".join(str(j.id) for j in stuck),
            )
        # Touch _uuid to keep the import in the module namespace for
        # future extensions (per-tenant filtering by id) without a ruff
        # unused-import warning.
        _ = _uuid
        return {"reaped": reaped, "cutoff": cutoff.isoformat()}
    finally:
        db.close()


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


# The only CNAME target we accept for a BYO custom domain is our Fly.io
# Caddy edge. Caddy terminates TLS via on-demand Let's Encrypt and
# path-routes ``/r/*`` + ``/api/v1/*`` to the reports backend and
# ``/view/*`` + ``/_next/*`` + ``/dashboard/*`` to the app backend.
#
# Legacy paths (direct-to-Railway ``*.up.railway.app``, CF-Worker
# ``*-custom.lintpdf.com``) have been retired -- no active tenant uses
# them and new signups always go through the edge.
_EDGE_CNAME_TARGET = "edge.lintpdf.com"


def _cname_points_at_edge(target: str | None) -> bool:
    """``True`` if ``target`` resolves to our Fly.io Caddy edge."""
    if not target:
        return False
    t = target.rstrip(".").lower()
    return t == _EDGE_CNAME_TARGET or t.endswith(f".{_EDGE_CNAME_TARGET}")


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lintpdf.edge.prewarm_cert",
    time_limit=60,
    soft_time_limit=50,
    ignore_result=True,
    max_retries=1,
    default_retry_delay=15,
)
def prewarm_edge_cert(hostname: str) -> dict[str, Any]:
    """Force Caddy to mint the Let's Encrypt cert for ``hostname`` now.

    Without this, the FIRST real HTTPS request from a customer's
    browser triggers on-demand cert issuance and waits 5-30 s for the
    TLS-ALPN-01 dance to finish. On mobile Safari that wait frequently
    exceeds the default connect timeout, producing a "couldn't
    establish a secure connection" error that only clears after the
    user reloads.

    We call this Celery task right after a tenant sets / verifies a
    custom domain, so the cert is warm by the time a real visitor
    arrives. Never raises -- cert prewarming is best-effort; if it
    fails here, the first real request still triggers issuance, just
    with the usual first-request latency. No customer-facing error.

    Opens a TLS socket with SNI = hostname, sends a minimal HEAD
    request, reads the response line, and closes. That's enough to
    make Caddy's ``on_demand_tls`` issue the cert.
    """
    import socket
    import ssl

    canonical = (hostname or "").strip().lower().rstrip(".")
    if not canonical:
        return {"hostname": hostname, "status": "skipped_empty"}

    # Gate: only prewarm hostnames we'd actually serve. The edge's ask
    # endpoint would reject unknown hostnames anyway, but probing non-
    # customer domains with our workers is wasteful.
    if not canonical.endswith(".lintpdf.com") and not _cname_points_at_edge(
        _resolve_cname(canonical)
    ):
        logger.info(
            "Skipping cert prewarm for %s -- CNAME doesn't point at edge yet",
            canonical,
        )
        return {"hostname": canonical, "status": "cname_not_at_edge"}

    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((canonical, 443), timeout=45) as sock:
            with ctx.wrap_socket(sock, server_hostname=canonical) as ssock:
                ssock.sendall(
                    b"HEAD /__edge/health HTTP/1.1\r\nHost: "
                    + canonical.encode()
                    + b"\r\nConnection: close\r\nUser-Agent: lintpdf-cert-prewarm\r\n\r\n"
                )
                # Read the status line; body is discarded.
                status_line = ssock.recv(128)
        logger.info(
            "Edge cert prewarm OK for %s (%s)",
            canonical,
            status_line.decode("ascii", errors="replace").strip().splitlines()[0:1],
        )
        return {"hostname": canonical, "status": "warmed"}
    except ssl.SSLError as exc:
        # Retryable: cert still issuing, or order in-flight. One retry
        # after a 15 s delay gives Caddy time to finish the ACME dance.
        logger.warning("TLS error prewarming %s: %s (will retry)", canonical, exc)
        return {"hostname": canonical, "status": "tls_error", "error": str(exc)}
    except (OSError, socket.timeout) as exc:
        logger.warning("Network error prewarming %s: %s", canonical, exc)
        return {"hostname": canonical, "status": "network_error", "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected prewarm failure for %s", canonical)
        return {"hostname": canonical, "status": "error", "error": str(exc)}


def _activate_edge_domain(
    db: Any,
    row: Any,
    domain: str,
    verified_attr: str,
    scope_label: str,
    result: dict[str, Any],
) -> bool:
    """Flip ``verified=True`` if ``domain`` CNAMEs at our edge.

    Shared by the four probe branches (tenant reports, tenant app,
    profile reports, profile app) so there's exactly one place that
    owns the "is this domain live?" check.

    Returns True when the row was activated. On mismatch increments
    ``result['cname_mismatch']`` and returns False.
    """
    cname = _resolve_cname(domain)
    if not _cname_points_at_edge(cname):
        result["cname_mismatch"] += 1
        logger.info(
            "%s %s not yet CNAMEd at %s (CNAME=%s)",
            scope_label,
            domain,
            _EDGE_CNAME_TARGET,
            cname,
        )
        return False
    setattr(row, verified_attr, True)
    db.commit()
    result["activated"] += 1
    logger.info("Activated %s %s via edge", scope_label, domain)
    # Fire cert prewarm so the first real customer hit doesn't wait the
    # 5-30s LE issuance latency. Delayed 3 s to let the DB commit settle
    # + to stay off the probe-task's critical path.
    try:
        prewarm_edge_cert.apply_async(args=[domain], countdown=3)
    except Exception:
        logger.warning("Failed to schedule cert prewarm for %s", domain, exc_info=True)
    return True


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lintpdf.queue.tasks.probe_pending_custom_domains",
)
def probe_pending_custom_domains() -> dict[str, Any]:
    """Flip ``verified=True`` on unverified custom domains whose CNAMEs point at our edge.

    Runs on a 5-minute Celery beat schedule. Safe to run concurrently
    (commits per-row) and idempotent (verified rows are ignored).

    For each unverified domain -- tenant-level reports/app and
    brand-profile-level reports/app -- we resolve the customer's CNAME
    and flip ``verified=True`` if it points at ``edge.lintpdf.com``.
    Caddy handles cert issuance on first HTTPS request; no Railway
    round-trip or CF-Worker alias provisioning needed.
    """
    from lintpdf.api.database import get_db_session
    from lintpdf.api.models import BrandProfile, Tenant

    result: dict[str, Any] = {
        "checked": 0,
        "activated": 0,
        "cname_mismatch": 0,
    }

    # Cap how many unverified rows we pull per beat tick. The DNS probes
    # are cheap but a spam wave of signups can otherwise load tens of
    # thousands of rows into memory at once; we'll catch the leftovers on
    # the next 5-minute tick.
    _PROBE_BATCH_LIMIT = 500

    db = get_db_session()
    try:
        pending_tenants: list[Tenant] = (
            db.query(Tenant)
            .filter(
                Tenant.brand_custom_domain.isnot(None),
                Tenant.brand_custom_domain_verified.is_(False),
            )
            .limit(_PROBE_BATCH_LIMIT)
            .all()
        )
        for tenant in pending_tenants:
            result["checked"] += 1
            if not tenant.brand_custom_domain:
                continue
            _activate_edge_domain(
                db,
                tenant,
                tenant.brand_custom_domain,
                "brand_custom_domain_verified",
                f"tenant {tenant.id} reports domain",
                result,
            )

        pending_profiles: list[BrandProfile] = (
            db.query(BrandProfile)
            .filter(
                BrandProfile.custom_domain.isnot(None),
                BrandProfile.custom_domain_verified.is_(False),
            )
            .limit(_PROBE_BATCH_LIMIT)
            .all()
        )
        for profile in pending_profiles:
            result["checked"] += 1
            if not profile.custom_domain:
                continue
            _activate_edge_domain(
                db,
                profile,
                profile.custom_domain,
                "custom_domain_verified",
                f"profile {profile.id} reports domain",
                result,
            )

        pending_app_tenants: list[Tenant] = (
            db.query(Tenant)
            .filter(
                Tenant.app_custom_domain.isnot(None),
                Tenant.app_custom_domain_verified.is_(False),
            )
            .limit(_PROBE_BATCH_LIMIT)
            .all()
        )
        for tenant in pending_app_tenants:
            result["checked"] += 1
            if not tenant.app_custom_domain:
                continue
            _activate_edge_domain(
                db,
                tenant,
                tenant.app_custom_domain,
                "app_custom_domain_verified",
                f"tenant {tenant.id} app domain",
                result,
            )

        pending_app_profiles: list[BrandProfile] = (
            db.query(BrandProfile)
            .filter(
                BrandProfile.app_custom_domain.isnot(None),
                BrandProfile.app_custom_domain_verified.is_(False),
            )
            .limit(_PROBE_BATCH_LIMIT)
            .all()
        )
        for profile in pending_app_profiles:
            result["checked"] += 1
            if not profile.app_custom_domain:
                continue
            _activate_edge_domain(
                db,
                profile,
                profile.app_custom_domain,
                "app_custom_domain_verified",
                f"profile {profile.id} app domain",
                result,
            )

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
    """Deprecated: delegates to :func:`warm_viewer_tiles`.

    Kept as a stable Celery name so any pre-existing broker-queued
    messages still route somewhere sensible after the upgrade. New
    callers should use :func:`enqueue_tile_warming` instead, which
    pulls ``tenant_id`` and ``file_key`` from the job row and tracks
    progress in Redis.
    """
    _ = (tenant_id, file_key)  # intentionally unused — resolved from DB now
    logger.info("prerender_viewer_tiles: forwarding to warm_viewer_tiles for %s", job_id)
    return warm_viewer_tiles.apply(args=[job_id]).get()  # type: ignore[no-any-return]


def _dispatch_tenant_webhooks(
    db: Any,
    tenant_id: Any,
    event: str,
    payload: dict[str, Any],
) -> None:
    """Dispatch webhooks for a tenant asynchronously.

    Funnels through ``lintpdf.webhooks.events.emit_event`` so every
    dispatch lands in the ``webhook_deliveries`` audit table -- both
    pre-existing callers (job.completed, approval.* from approvals
    service) and the new event helpers share one emit path.
    """
    from lintpdf.webhooks.events import emit_event

    emit_event(db, tenant_id, event, payload)


_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_BASE_DELAY_S = 5
_DEFAULT_RETRY_MAX_DELAY_S = 300
_RETRY_CEILING = 10  # Hard ceiling irrespective of per-endpoint config


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lintpdf.webhook.dispatch",
    bind=True,
    max_retries=_RETRY_CEILING,
    default_retry_delay=_DEFAULT_RETRY_BASE_DELAY_S,
)
def dispatch_webhook(
    self: Any,
    webhook_url: str,
    webhook_secret: str,
    event: str,
    payload: dict[str, Any],
    delivery_id: str | None = None,
) -> dict[str, Any]:
    """Dispatch a webhook notification with per-endpoint retry config.

    Args:
        webhook_url: URL to deliver the webhook to.
        webhook_secret: HMAC secret for signing.
        event: Event type (e.g. "job.completed").
        payload: Event payload dict.
        delivery_id: Optional ``WebhookDelivery`` row UUID. When set, this
            task updates the row with attempt count, final status, and
            ``delivered_at`` so operators have a replayable audit trail.

    Returns:
        Delivery status dict (terminal outcome only — intermediate
        retries raise ``Retry`` instead of returning).
    """
    import datetime as _dt
    import hashlib
    import hmac
    import uuid as uuid_mod

    import httpx
    from celery.exceptions import MaxRetriesExceededError

    from lintpdf.api.database import SessionLocal
    from lintpdf.api.models import WebhookDelivery, WebhookEndpoint

    # Sign the payload
    body = json.dumps(payload, sort_keys=True, default=str)
    signature = hmac.new(
        webhook_secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    last_error: str | None = None
    final_status: int = 0
    success: bool = False

    # ``self.request.retries`` starts at 0 on the first delivery and
    # increments on every ``self.retry()``. Translate to 1-indexed for
    # the audit row so "attempt_count=3" reads naturally as "we tried
    # three times."
    attempt = int(getattr(self.request, "retries", 0) or 0) + 1

    try:
        response = httpx.post(
            webhook_url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-LintPDF-Event": event,
                "X-LintPDF-Signature": f"sha256={signature}",
                "User-Agent": "LintPDF-Webhook/0.1.0",
            },
            timeout=10.0,
        )
        final_status = response.status_code
        if response.status_code < 400:
            success = True
        else:
            last_error = f"HTTP {response.status_code}"
    except Exception as exc:
        last_error = str(exc)

    # Update audit row before deciding whether to retry so even
    # intermediate attempts are visible in /webhooks/deliveries.
    if delivery_id:
        session = SessionLocal()
        try:
            row = (
                session.query(WebhookDelivery)
                .filter(WebhookDelivery.id == uuid_mod.UUID(delivery_id))
                .first()
            )
            if row is not None:
                row.attempt_count = attempt
                row.final_status_code = final_status
                row.success = success
                row.last_error = (last_error or "")[:1024] if last_error else None
                row.delivered_at = _dt.datetime.now(_dt.timezone.utc)
                session.commit()
        except Exception:
            logger.exception(
                "Webhook audit: failed to update WebhookDelivery %s", delivery_id
            )
            session.rollback()
        finally:
            session.close()

    # Retry only on 5xx / network errors. 4xx means the caller's
    # endpoint rejected the payload; retrying the same body won't
    # make it better.
    retryable = (not success) and (final_status == 0 or final_status >= 500)

    if not success and retryable:
        # Load the per-endpoint retry config on every attempt so a
        # live ``PATCH /webhooks/{id}`` takes effect mid-backoff.
        session = SessionLocal()
        try:
            max_retries = _DEFAULT_MAX_RETRIES
            base_delay = _DEFAULT_RETRY_BASE_DELAY_S
            max_delay = _DEFAULT_RETRY_MAX_DELAY_S
            if delivery_id:
                delivery = (
                    session.query(WebhookDelivery)
                    .filter(WebhookDelivery.id == uuid_mod.UUID(delivery_id))
                    .first()
                )
                if delivery is not None:
                    endpoint = (
                        session.query(WebhookEndpoint)
                        .filter(WebhookEndpoint.id == delivery.webhook_id)
                        .first()
                    )
                    if endpoint is not None:
                        if endpoint.max_retries is not None:
                            max_retries = min(endpoint.max_retries, _RETRY_CEILING)
                        if endpoint.retry_base_delay_seconds is not None:
                            base_delay = endpoint.retry_base_delay_seconds
                        if endpoint.retry_max_delay_seconds is not None:
                            max_delay = endpoint.retry_max_delay_seconds
        finally:
            session.close()

        if attempt <= max_retries:
            # Exponential backoff, capped. attempt is 1-indexed; first
            # retry sleeps ``base_delay`` (not ``base_delay * 2``).
            countdown = min(base_delay * (2 ** (attempt - 1)), max_delay)
            try:
                raise self.retry(
                    countdown=countdown,
                    max_retries=max_retries,
                    exc=Exception(last_error or f"HTTP {final_status}"),
                )
            except MaxRetriesExceededError:
                pass  # Fall through to the failed-return below.

    if success:
        return {
            "status": "delivered",
            "url": webhook_url,
            "event": event,
            "status_code": final_status,
            "attempt_count": attempt,
        }

    # Retries exhausted (or the failure was non-retryable): mark the
    # audit row as dead so the admin /webhooks/deliveries?dead=true view
    # can surface it and an operator can trigger a replay later.
    if delivery_id:
        session = SessionLocal()
        try:
            row = (
                session.query(WebhookDelivery)
                .filter(WebhookDelivery.id == uuid_mod.UUID(delivery_id))
                .first()
            )
            if row is not None and not row.is_dead:
                row.is_dead = True
                session.commit()
        except Exception:
            logger.exception(
                "Webhook dead-letter: failed to flag delivery %s", delivery_id
            )
            session.rollback()
        finally:
            session.close()

    logger.error(
        "Webhook delivery to %s dead after %d attempts: %s",
        webhook_url,
        attempt,
        last_error,
    )
    return {
        "status": "failed",
        "url": webhook_url,
        "event": event,
        "error": last_error,
        "is_dead": True,
    }


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lintpdf.queue.tasks.sweep_webhook_deliveries",
)
def sweep_webhook_deliveries() -> dict[str, Any]:
    """Delete old ``WebhookDelivery`` rows per-endpoint retention policy.

    Runs daily via Celery Beat. For every endpoint with a non-null
    ``delivery_retention_days``, deletes rows whose ``created_at`` is
    older than that retention window. ``retention_overrides`` entries
    take precedence for matching event names (fnmatch glob, longest
    match wins), so a tenant can keep billing events for a year while
    annotation events expire in a week.

    Endpoints with ``delivery_retention_days IS NULL`` and no matching
    override are left alone -- operators can opt out of the sweep by
    leaving both fields unset.
    """
    import datetime as _dt
    import fnmatch

    from lintpdf.api.database import get_db_session
    from lintpdf.api.models import WebhookDelivery, WebhookEndpoint

    db = get_db_session()
    now = _dt.datetime.now(_dt.timezone.utc)
    total_deleted = 0
    per_endpoint: dict[str, int] = {}
    try:
        endpoints = db.query(WebhookEndpoint).all()
        for endpoint in endpoints:
            default_days = endpoint.delivery_retention_days
            overrides: dict[str, int] = endpoint.retention_overrides or {}
            if default_days is None and not overrides:
                continue

            rows = (
                db.query(WebhookDelivery)
                .filter(WebhookDelivery.webhook_id == endpoint.id)
                .all()
            )
            deleted_here = 0
            for row in rows:
                # Longest-glob wins so ``billing.file_quota.low`` is
                # bound by ``billing.file_quota.*`` rather than the
                # broader ``billing.*`` when both are present.
                matched_days: int | None = default_days
                best_match_len = -1
                for glob, days in overrides.items():
                    if fnmatch.fnmatchcase(row.event, glob) and len(glob) > best_match_len:
                        matched_days = days
                        best_match_len = len(glob)
                if matched_days is None:
                    continue
                cutoff = now - _dt.timedelta(days=matched_days)
                # SQLite stores naive datetimes; Postgres stores tz-aware.
                # Normalise to tz-aware UTC for the comparison.
                row_created = row.created_at
                if row_created.tzinfo is None:
                    row_created = row_created.replace(tzinfo=_dt.timezone.utc)
                if row_created < cutoff:
                    db.delete(row)
                    deleted_here += 1

            if deleted_here:
                per_endpoint[str(endpoint.id)] = deleted_here
                total_deleted += deleted_here

        if total_deleted:
            db.commit()
            logger.info(
                "sweep_webhook_deliveries: deleted %d rows across %d endpoint(s)",
                total_deleted,
                len(per_endpoint),
            )
        return {"deleted": total_deleted, "per_endpoint": per_endpoint}
    finally:
        db.close()


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

    # Same warming path as the engine completion branch — keeps the
    # viewer behaviour uniform across external-import / minimal runs.
    enqueue_tile_warming(job_id)

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
        "findings": [
            {
                "inspection_id": f.inspection_id,
                "severity": (
                    f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                ),
                "message": f.message,
                "page_num": f.page_num,
                "bbox": list(f.bbox) if f.bbox else None,
                "details": f.details,
                "source": f.source or "external",
                "category": f.category,
                "object_id": f.object_id,
                "object_type": f.object_type,
            }
            for f in imported.findings
        ],
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


# ---------------------------------------------------------------------------
# Viewer tile warming (background pre-render)
# ---------------------------------------------------------------------------

# DPI variants the viewer actively requests. Page tiles open at 150; the
# thumbnail strip reuses 72. Keep in lockstep with
# ``packages/app/components/viewer/types.ts::DEFAULT_DPI`` /
# ``THUMBNAIL_DPI``.
_WARM_MAIN_DPI = 150
_WARM_THUMBNAIL_DPI = 72

# TTL for the warming-status Redis key: long enough that a reviewer
# who opens the viewer hours after the job finished still sees
# ``status=complete``, short enough that stale keys don't accumulate
# indefinitely.
_WARM_STATUS_TTL_S = 24 * 60 * 60
_WARM_LOCK_TTL_S = 600  # matches soft_time_limit

# Per-tenant concurrency cap for tile warming. Prevents a bulk-upload
# tenant (100 jobs submitted in 10 seconds) from spawning 100
# simultaneous ``warm_tiles`` workers and starving the Celery pool.
# Overrides per-tenant via the ``LINTPDF_TILE_WARMING_PER_TENANT_MAX``
# env var. A value of 0 disables the cap entirely.
_WARM_TENANT_SEMAPHORE_TTL_S = 900  # conservative: 15 min, > hard time_limit
# How long a blocked enqueue should wait (via countdown) before retry.
# Short enough that a brief burst clears quickly; long enough that we
# don't busy-loop against the semaphore.
_WARM_TENANT_RETRY_DELAY_S = 20


def _tile_warm_status_key(job_id: str) -> str:
    """Redis hash tracking warming progress for a job."""
    return f"lintpdf:tile-warm:{job_id}"


def _tile_warm_lock_key(job_id: str) -> str:
    """Redis string holding the active warming lock for a job."""
    return f"lintpdf:tile-warm-lock:{job_id}"


def _tile_warm_tenant_semaphore_key(tenant_id: str) -> str:
    """Redis counter of currently-running warming jobs for a tenant."""
    return f"lintpdf:tile-warm-sem:{tenant_id}"


def _tile_warm_events_key(tenant_id: str) -> str:
    """Per-tenant capped list of recent warming events (for admin dashboard)."""
    return f"lintpdf:tile-warm-events:{tenant_id}"


def _tile_warm_events_all_key() -> str:
    """Global capped list of recent warming events across every tenant."""
    return "lintpdf:tile-warm-events:_all"


# Keep the last 500 events per list; expire the list after 7 days of silence.
_TILE_WARM_EVENTS_CAP = 500
_TILE_WARM_EVENTS_TTL_S = 7 * 24 * 3600


def _record_tile_warm_event(
    redis: Any,
    tenant_id: str | None,
    payload: dict[str, Any],
) -> None:
    """LPUSH + LTRIM + EXPIRE an event into the tenant list and the global list.

    Swallows every Redis error — observability must never affect warming.
    The recorder is called inside ``warm_viewer_tiles`` after the existing
    Redis-availability check, so ``redis`` here is guaranteed non-None at
    call time; we still defend against ``None`` so future callers can't
    surprise us.
    """
    import contextlib as _contextlib
    import json as _json

    if redis is None:
        return
    try:
        serialized = _json.dumps(payload, default=str)
    except Exception:
        logger.warning("tile_warm event serialize failed", exc_info=True)
        return

    def _push(key: str) -> None:
        with _contextlib.suppress(Exception):
            redis.lpush(key, serialized)
            redis.ltrim(key, 0, _TILE_WARM_EVENTS_CAP - 1)
            redis.expire(key, _TILE_WARM_EVENTS_TTL_S)

    if tenant_id:
        _push(_tile_warm_events_key(tenant_id))
    _push(_tile_warm_events_all_key())


def _tile_warm_tenant_cap() -> int:
    """Configured per-tenant concurrency cap. 0 means no cap."""
    import os as _os

    raw = _os.getenv("LINTPDF_TILE_WARMING_PER_TENANT_MAX", "3")
    try:
        return max(0, int(raw))
    except ValueError:
        return 3


def _tile_s3_key(tenant_id: str, job_id: str, page_num: int, dpi: int) -> str:
    """S3 key for a rendered page tile (mirrors ``viewer.py::_tile_cache_key``)."""
    return f"{tenant_id}/{job_id}/tiles/p{page_num}_d{dpi}.png"


def _warm_status_payload(
    *,
    status: str,
    total: int,
    rendered: int,
    dpi: int,
    started_at: str,
    updated_at: str | None = None,
    completed_at: str | None = None,
    error: str | None = None,
) -> dict[str, str]:
    """Shape of the warming-status Redis hash. All values stored as str.

    Kept as a flat string→string mapping so ``HSET`` / ``HGETALL`` round
    trips cleanly and the frontend can parse without a JSON unmarshal.
    """
    payload = {
        "status": status,
        "total": str(total),
        "rendered": str(rendered),
        "dpi": str(dpi),
        "started_at": started_at,
        "updated_at": updated_at or started_at,
    }
    if completed_at:
        payload["completed_at"] = completed_at
    if error:
        payload["error"] = error
    return payload


def enqueue_tile_warming(job_id: str, *, dpi: int = _WARM_MAIN_DPI) -> bool:
    """Fire-and-forget wrapper around :func:`warm_viewer_tiles`.

    Called from the preflight completion paths so cold-path job
    submission doesn't have to know the task name. Returns False when
    the warming feature is disabled or Celery isn't available — caller
    should not treat this as an error.
    """
    import os as _os

    if _os.getenv("LINTPDF_TILE_WARMING_ENABLED", "true").lower() == "false":
        return False
    try:
        warm_viewer_tiles.apply_async(args=[job_id, dpi], queue="default")
        return True
    except Exception:
        logger.warning("Failed to enqueue tile warming for %s", job_id, exc_info=True)
        return False


@celery_app.task(  # type: ignore[untyped-decorator]
    name="lintpdf.viewer.warm_tiles",
    max_retries=1,
    default_retry_delay=10,
    time_limit=600,  # 10 min hard cap — large PDFs can't take longer
    soft_time_limit=540,
)
def warm_viewer_tiles(
    job_id: str,
    dpi: int = _WARM_MAIN_DPI,
    *,
    include_thumbnails: bool = True,
) -> dict[str, Any]:
    """Pre-render every page tile for a completed job into S3.

    Writes progress to Redis under
    ``lintpdf:tile-warm:{job_id}`` as a hash
    ``{status, rendered, total, dpi, started_at, updated_at,
    completed_at, error}`` so the viewer can surface a readiness bar.

    Returns a status dict for observability. Never raises back to
    Celery on normal operational failures (Redis down, file already
    warmed, etc.) — only on unexpected exceptions after the in-progress
    state has been published, so retries don't wedge.
    """
    import contextlib
    import datetime as _dt
    import uuid as uuid_mod

    from lintpdf.ai.rendering import render_page_to_image
    from lintpdf.api.database import get_db_session
    from lintpdf.api.middleware import get_redis_client
    from lintpdf.api.models import Job, JobStatus
    from lintpdf.api.storage import get_storage

    redis = get_redis_client()
    if redis is None:
        # Warming without Redis coordination would risk double-renders
        # when Celery retries. The viewer silently skips the progress
        # indicator in this mode.
        logger.info("warm_viewer_tiles: Redis not configured, skipping %s", job_id)
        return {"status": "no_redis", "job_id": job_id}

    lock_key = _tile_warm_lock_key(job_id)
    acquired = False
    try:
        acquired = bool(redis.set(lock_key, "1", nx=True, ex=_WARM_LOCK_TTL_S))
    except Exception:
        logger.warning("warm_viewer_tiles: lock acquire failed for %s", job_id, exc_info=True)
        return {"status": "lock_error", "job_id": job_id}
    if not acquired:
        logger.info("warm_viewer_tiles: another worker already warming %s", job_id)
        return {"status": "locked", "job_id": job_id}

    status_key = _tile_warm_status_key(job_id)
    started_at = _dt.datetime.now(_dt.UTC).isoformat()
    semaphore_held = False
    tenant_id_for_semaphore: str | None = None

    db = get_db_session()
    try:
        try:
            job_uuid = uuid_mod.UUID(job_id)
        except ValueError:
            return {"status": "bad_job_id", "job_id": job_id}

        job = db.query(Job).filter(Job.id == job_uuid).first()
        if job is None:
            return {"status": "not_found", "job_id": job_id}
        if job.status != JobStatus.COMPLETE:
            logger.info(
                "warm_viewer_tiles: job %s is %s; skipping (only COMPLETE warms)",
                job_id,
                job.status,
            )
            return {"status": "not_complete", "job_id": job_id}

        page_count = int(job.page_count or 0)
        if page_count <= 0:
            return {"status": "no_pages", "job_id": job_id}

        tenant_id = str(job.tenant_id)
        storage = get_storage()

        # Per-tenant concurrency gate. We've already claimed the
        # per-job lock above, so release it if the semaphore is full —
        # the retry re-acquires both locks cleanly. ``cap = 0`` means
        # the cap is disabled (useful for integration tests).
        cap = _tile_warm_tenant_cap()
        if cap > 0:
            sem_key = _tile_warm_tenant_semaphore_key(tenant_id)
            try:
                current = redis.incr(sem_key)
                # First incrementer sets the TTL so orphaned counters
                # can't lock a tenant out forever if a worker crashes
                # before the decrement.
                if current == 1:
                    redis.expire(sem_key, _WARM_TENANT_SEMAPHORE_TTL_S)
                if current > cap:
                    # Over cap — roll back and retry.
                    redis.decr(sem_key)
                    with contextlib.suppress(Exception):
                        redis.delete(lock_key)
                    logger.info(
                        "warm_viewer_tiles: tenant %s over cap (%d/%d); retrying job %s in %ds",
                        tenant_id,
                        current - 1,
                        cap,
                        job_id,
                        _WARM_TENANT_RETRY_DELAY_S,
                    )
                    # Re-enqueue ourselves with a countdown so Celery
                    # defers the work instead of busy-retrying.
                    warm_viewer_tiles.apply_async(
                        args=[job_id, dpi],
                        kwargs={"include_thumbnails": include_thumbnails},
                        countdown=_WARM_TENANT_RETRY_DELAY_S,
                        queue="default",
                    )
                    return {
                        "status": "deferred",
                        "job_id": job_id,
                        "tenant_id": tenant_id,
                        "cap": cap,
                    }
            except Exception:
                logger.warning(
                    "warm_viewer_tiles: tenant semaphore failed for %s — proceeding without cap",
                    tenant_id,
                    exc_info=True,
                )
            else:
                semaphore_held = True
                tenant_id_for_semaphore = tenant_id

        # Publish initial in-progress state so pollers see a non-zero
        # total immediately.
        try:
            redis.hset(
                status_key,
                mapping=_warm_status_payload(
                    status="in_progress",
                    total=page_count,
                    rendered=0,
                    dpi=dpi,
                    started_at=started_at,
                ),
            )
            redis.expire(status_key, _WARM_STATUS_TTL_S)
        except Exception:
            logger.warning("warm_viewer_tiles: status publish failed", exc_info=True)

        # Pull the PDF once — we render all pages from the same bytes.
        pdf_bytes = _download_pdf_with_fallback(storage, job.file_key, job_id)

        def _warm_one(page_num: int, render_dpi: int) -> None:
            """Render one page to S3 unless already cached."""
            key = _tile_s3_key(tenant_id, job_id, page_num, render_dpi)
            try:
                if storage.download_raw(key) is not None:
                    return  # Already warmed — idempotent.
            except Exception:
                pass  # Probe failure — re-render and upload.
            try:
                tile_bytes = render_page_to_image(pdf_bytes, page_num, dpi=render_dpi)
                storage.upload_raw(
                    key,
                    tile_bytes,
                    content_type="image/png",
                    cache_control="public, max-age=86400",
                )
            except Exception:
                logger.warning(
                    "warm_viewer_tiles: render p%d @ %dpi failed for %s",
                    page_num,
                    render_dpi,
                    job_id,
                    exc_info=True,
                )
                # Don't re-raise — one page's failure shouldn't block the rest.

        # Pre-warm CMYK + spot channel rasters too, so the first click
        # on the Separations panel / Densitometer doesn't pay the
        # ~2s Ghostscript cost. get_cmyk_channels owns the cache
        # keys and the render; calling it with the storage context
        # populates the S3 cache as a side effect. Spot channels are
        # enumerated via list_separations so tenants printing with
        # Pantone / metallic inks benefit too.
        def _warm_separations() -> None:
            try:
                from lintpdf.reports.separation_renderer import (
                    channel_cache_key,
                    get_cmyk_channels,
                    list_separations,
                    render_separation_channel,
                )
            except Exception:
                logger.warning(
                    "warm_viewer_tiles: separation renderer unavailable — skipping spot warm",
                    exc_info=True,
                )
                return

            try:
                spots = [
                    ch["name"] for ch in list_separations(pdf_bytes) if ch.get("type") == "spot"
                ]
            except Exception:
                spots = []

            for page_num in range(1, page_count + 1):
                try:
                    # CMYK: get_cmyk_channels writes all four PNGs to
                    # S3 when the caching context is supplied.
                    get_cmyk_channels(
                        pdf_bytes,
                        page_num,
                        dpi,
                        tenant_id=tenant_id,
                        job_id=job_id,
                        storage=storage,
                    )
                except Exception:
                    logger.warning(
                        "warm_viewer_tiles: CMYK warm failed p%d for %s",
                        page_num,
                        job_id,
                        exc_info=True,
                    )
                for spot in spots:
                    key = channel_cache_key(tenant_id, job_id, page_num, dpi, spot)
                    try:
                        if storage.download_raw(key) is not None:
                            continue  # already cached
                    except Exception:
                        pass
                    try:
                        render_separation_channel(
                            pdf_bytes,
                            page_num,
                            spot,
                            dpi=dpi,
                            tenant_id=tenant_id,
                            job_id=job_id,
                            storage=storage,
                        )
                    except Exception:
                        logger.warning(
                            "warm_viewer_tiles: spot %s warm failed p%d for %s",
                            spot,
                            page_num,
                            job_id,
                            exc_info=True,
                        )

        for page_num in range(1, page_count + 1):
            _warm_one(page_num, dpi)
            if include_thumbnails and dpi != _WARM_THUMBNAIL_DPI:
                _warm_one(page_num, _WARM_THUMBNAIL_DPI)
            # Progress publish failures are cosmetic; keep rendering.
            with contextlib.suppress(Exception):
                redis.hset(
                    status_key,
                    mapping={
                        "rendered": str(page_num),
                        "updated_at": _dt.datetime.now(_dt.UTC).isoformat(),
                    },
                )

        # Separation warming runs after page tiles so a reviewer who
        # opens the viewer mid-warm always sees composite tiles first.
        # Gated behind an env var so tenants without Ghostscript
        # workloads can opt out of the extra minutes per large job.
        import os as _os_sep

        if _os_sep.getenv("LINTPDF_TILE_WARMING_INCLUDE_SEPARATIONS", "true").lower() != "false":
            _warm_separations()

        completed_at = _dt.datetime.now(_dt.UTC).isoformat()
        try:
            redis.hset(
                status_key,
                mapping=_warm_status_payload(
                    status="complete",
                    total=page_count,
                    rendered=page_count,
                    dpi=dpi,
                    started_at=started_at,
                    completed_at=completed_at,
                ),
            )
            redis.expire(status_key, _WARM_STATUS_TTL_S)
        except Exception:
            logger.warning("warm_viewer_tiles: final status publish failed", exc_info=True)

        # Structured completion log so ops/alerting can parse by key.
        # Duration is the wallclock between the initial publish and
        # now — a proxy for "time from job-complete to viewer-ready".
        try:
            started_dt = _dt.datetime.fromisoformat(started_at)
            duration_s = (_dt.datetime.now(_dt.UTC) - started_dt).total_seconds()
        except Exception:
            duration_s = -1.0
        logger.info(
            "tile_warm.complete",
            extra={
                "event": "tile_warm.complete",
                "job_id": job_id,
                "tenant_id": tenant_id,
                "page_count": page_count,
                "dpi": dpi,
                "thumbnails": include_thumbnails,
                "duration_s": round(duration_s, 2),
            },
        )
        _record_tile_warm_event(
            redis,
            tenant_id,
            {
                "event": "tile_warm.complete",
                "job_id": job_id,
                "tenant_id": tenant_id,
                "page_count": page_count,
                "dpi": dpi,
                "thumbnails": include_thumbnails,
                "duration_s": round(duration_s, 2),
                "error": None,
                "recorded_at": _dt.datetime.now(_dt.UTC).isoformat(),
            },
        )
        return {
            "status": "complete",
            "job_id": job_id,
            "rendered": page_count,
            "total": page_count,
            "duration_s": round(duration_s, 2),
        }

    except Exception as exc:
        logger.exception(
            "tile_warm.failure",
            extra={
                "event": "tile_warm.failure",
                "job_id": job_id,
                "tenant_id": tenant_id_for_semaphore,
                "error": str(exc)[:500],
            },
        )
        _record_tile_warm_event(
            redis,
            tenant_id_for_semaphore,
            {
                "event": "tile_warm.failure",
                "job_id": job_id,
                "tenant_id": tenant_id_for_semaphore,
                "page_count": None,
                "dpi": dpi,
                "thumbnails": include_thumbnails,
                "duration_s": None,
                "error": str(exc)[:500],
                "recorded_at": _dt.datetime.now(_dt.UTC).isoformat(),
            },
        )
        # Publish the failure state (best-effort) before re-raising so
        # the viewer's progress badge can render the error chip.
        with contextlib.suppress(Exception):
            redis.hset(
                status_key,
                mapping={
                    "status": "failed",
                    "updated_at": _dt.datetime.now(_dt.UTC).isoformat(),
                    "error": str(exc)[:500],
                },
            )
        raise
    finally:
        if semaphore_held and tenant_id_for_semaphore:
            with contextlib.suppress(Exception):
                redis.decr(_tile_warm_tenant_semaphore_key(tenant_id_for_semaphore))
        with contextlib.suppress(Exception):
            redis.delete(lock_key)
        db.close()
