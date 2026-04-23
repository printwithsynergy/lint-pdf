"""Async audit tasks — retried with exponential back-off on Claude failure.

The preflight completion hook enqueues :func:`audit_findings_async`
instead of running the audit inline, so a flaky Anthropic response
never stalls the preflight critical path. Each attempt runs the
full :func:`lintpdf.queue.tasks.run_customer_audit` pass; on
exception we re-queue with a hand-rolled back-off schedule capped
at 24 h wall clock.

Schedule: 30 s → 2 m → 5 m → 15 m → 30 m → 30 m → … for 24 h.
After 24 h every finding still without a verdict gets
``audit_status='pending_retry'`` so the viewer can render a retry
chip and the admin dashboard can surface the stuck job.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from lintpdf.queue.app import celery_app

logger = logging.getLogger(__name__)

# Back-off schedule in seconds. Beyond the last entry we re-use the
# last value (30 min) until the 24h wall-clock ceiling fires.
_BACKOFF_S: tuple[int, ...] = (30, 120, 300, 900, 1800)
_MAX_WALL_CLOCK_S = 24 * 3600


@celery_app.task(
    bind=True,
    name="lintpdf.queue.audit_tasks.audit_findings_async",
    max_retries=None,  # Capped by wall clock, not retry count.
)
def audit_findings_async(self: Any, job_id: str, *, first_attempt_at_iso: str | None = None) -> int:
    """Run the customer audit and retry on failure up to 24h wall clock.

    Returns the number of verdicts written. Retries silently on
    any Claude / Anthropic failure via ``self.retry(countdown=...)``.
    After 24h the finding rows for this job get
    ``audit_status='pending_retry'`` so operators can see they're
    stuck without the task itself logging an unbounded tail of
    retry exceptions.
    """
    from lintpdf.api.database import get_db_session
    from lintpdf.api.models import Job
    from lintpdf.audit.outage import record_outcome
    from lintpdf.queue.tasks import run_customer_audit

    first_attempt = _parse_iso(first_attempt_at_iso) or datetime.now(UTC)

    db = get_db_session()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job is None:
            logger.info("audit-async: job %s not found; dropping", job_id)
            return 0
        try:
            written = run_customer_audit(db, job, str(job_id), force=False)
            record_outcome(True)
            return written
        except Exception as exc:
            record_outcome(False)
            age_s = (datetime.now(UTC) - first_attempt).total_seconds()
            if age_s >= _MAX_WALL_CLOCK_S:
                # Out of budget — mark the findings so the viewer can
                # render a retry chip and stop trying.
                _mark_pending_retry(db, job_id)
                logger.warning(
                    "audit-async: giving up on job %s after %.0fs (24h ceiling)",
                    job_id,
                    age_s,
                )
                return 0
            countdown = _next_countdown(self.request.retries)
            logger.info(
                "audit-async: retry %d for job %s in %ds (%s)",
                (self.request.retries or 0) + 1,
                job_id,
                countdown,
                exc,
            )
            raise self.retry(
                countdown=countdown,
                kwargs={
                    "job_id": str(job_id),
                    "first_attempt_at_iso": first_attempt.isoformat(),
                },
                exc=exc,
            ) from exc
    finally:
        db.close()


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _next_countdown(retries: int | None) -> int:
    idx = retries or 0
    if idx >= len(_BACKOFF_S):
        idx = len(_BACKOFF_S) - 1
    return _BACKOFF_S[idx]


def _mark_pending_retry(db: Any, job_id: str) -> None:
    from lintpdf.api.models import JobFinding

    stale = (
        db.query(JobFinding)
        .filter(JobFinding.job_id == job_id, JobFinding.audit_status.is_(None))
        .all()
    )
    for f in stale:
        f.audit_status = "pending_retry"
        f.audit_at = datetime.now(UTC)
    if stale:
        db.commit()
