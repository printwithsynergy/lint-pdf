"""Celery tasks for async job processing."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from lintpdf.queue.app import celery_app

logger = logging.getLogger(__name__)


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
                from lintpdf.profiles.schema import PreflightProfile, ThresholdConfig

                profile = profile.model_copy(
                    update={"thresholds": ThresholdConfig(**threshold_data)}
                )
                if "conformance" in jdf_overrides:
                    profile = profile.model_copy(
                        update={"conformance": jdf_overrides["conformance"]}
                    )

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
