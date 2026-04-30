"""Centralised webhook event emission helpers.

Every mutation that should notify subscribers funnels through one of the
`fire_*` helpers here. Each helper:

1. Loads the tenant's ``WebhookEndpoint`` rows subscribed to the event.
2. Persists a ``WebhookDelivery`` row per endpoint (so the operator-facing
   replay endpoint has the exact payload we signed, regardless of whether
   the caller acks).
3. Hands the dispatch off to Celery (``dispatch_webhook`` task) so the
   calling request thread never blocks on a slow webhook.

The dispatcher's Celery task (``queue/tasks.dispatch_webhook``) re-signs
the stored payload on each attempt and updates the ``WebhookDelivery``
row with the final status. See ``webhooks/dispatcher.py`` for the
HMAC-SHA256 signing implementation shared between the sync and async
paths.
"""

from __future__ import annotations

import json
import logging
import uuid as uuid_mod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event catalogue
# ---------------------------------------------------------------------------


KNOWN_EVENTS: tuple[str, ...] = (
    # Preflight lifecycle (pre-existing)
    "job.completed",
    "job.failed",
    # Approval chain (pre-existing)
    "approval.chain.started",
    "approval.step.started",
    "approval.step.decided",
    "approval.chain.completed",
    "approval.chain.rejected",
    "approval.chain.cancelled",
    "approval.chain.timeout",
    # NEW umbrella: fires whenever GET /jobs/{id}/state would differ.
    "job.state_changed",
    # NEW per-mutation events (granular subscribers can cherry-pick)
    "annotation.created",
    "annotation.deleted",
    "comment.created",
    "verdict.changed",
    "report.minted",
    "report.expired",
    "share_link.visited",
    # NEW billing threshold events
    "billing.file_quota.low",
    "billing.file_quota.exhausted",
    "billing.ai_credits.low",
    "billing.ai_credits.exhausted",
    # NEW tenant admin
    "tenant.plan.changed",
)


# ---------------------------------------------------------------------------
# Core dispatch
# ---------------------------------------------------------------------------


def emit_event(
    db: Session,
    tenant_id: uuid_mod.UUID,
    event: str,
    payload: dict[str, Any],
) -> None:
    """Persist a ``WebhookDelivery`` row per subscribed endpoint + queue async dispatch.

    This is the single funnel every event passes through. Callers should
    use the higher-level ``fire_*`` helpers below instead of invoking
    this directly; the helpers construct the payload in the shape each
    event advertises in the docs.

    Failure to queue a dispatch never raises — we log the exception and
    move on so an errant webhook subscriber cannot block the primary
    mutation (e.g. a customer's ``/webhooks/test`` pointing at a 500ing
    endpoint shouldn't cascade into "cannot save this annotation").
    """
    from lintpdf.api.models import WebhookDelivery, WebhookEndpoint

    try:
        endpoints = (
            db.query(WebhookEndpoint)
            .filter(
                WebhookEndpoint.tenant_id == tenant_id,
                WebhookEndpoint.is_active.is_(True),
            )
            .all()
        )
    except Exception:
        logger.exception(
            "Webhook emit: failed to load endpoints for tenant %s event %s",
            tenant_id,
            event,
        )
        return

    # Import Celery task lazily so this module stays importable in tests
    # that don't boot the queue.
    try:
        from lintpdf.queue.tasks import dispatch_webhook
    except Exception:
        logger.exception("Webhook emit: failed to import dispatch_webhook")
        return

    # Wave V V-06 (Q-D3): resolve the tenant default once so every
    # endpoint share the same fallback. Per-webhook ``endpoint.secret``
    # wins; tenant default fills in when unset.
    tenant_default_secret = _load_tenant_default_secret(db, tenant_id)

    for endpoint in endpoints:
        # Explicit subscription list: empty means "all events".
        if endpoint.events and event not in endpoint.events:
            continue

        signing_secret = resolve_signing_secret(
            endpoint_secret=endpoint.secret,
            tenant_default_secret=tenant_default_secret,
        )
        if signing_secret is None:
            logger.error(
                "Webhook emit: tenant %s has neither per-webhook nor"
                " tenant-default signing secret for endpoint %s; skipping"
                " dispatch (event=%s)",
                tenant_id,
                endpoint.id,
                event,
            )
            continue

        # Persist the delivery row BEFORE the async dispatch so the
        # replay endpoint has something to refer to even if the Celery
        # worker is down. The dispatcher task updates `success`,
        # `final_status_code`, `last_error`, `attempt_count`, and
        # `delivered_at` when it finishes.
        try:
            delivery = WebhookDelivery(
                id=uuid_mod.uuid4(),
                webhook_id=endpoint.id,
                tenant_id=tenant_id,
                event=event,
                payload=payload,
                url=endpoint.url,
                attempt_count=0,
                final_status_code=0,
                success=False,
            )
            db.add(delivery)
            db.flush()  # get the PK so we can pass it to Celery
            delivery_id_str = str(delivery.id)
        except Exception:
            logger.exception(
                "Webhook emit: failed to persist WebhookDelivery for %s/%s",
                tenant_id,
                event,
            )
            continue

        try:
            dispatch_webhook.delay(  # type: ignore[attr-defined]
                webhook_url=endpoint.url,
                webhook_secret=signing_secret,
                event=event,
                payload=payload,
                delivery_id=delivery_id_str,
            )
        except Exception:
            logger.exception(
                "Webhook emit: failed to queue dispatch for delivery %s",
                delivery_id_str,
            )
            # Don't rollback the delivery row -- it still serves as an
            # audit of "we tried to notify" even if the queue is broken.


def resolve_signing_secret(
    *,
    endpoint_secret: str | None,
    tenant_default_secret: str | None,
) -> str | None:
    """Wave V V-06 (Q-D3) — resolve the HMAC secret for one delivery.

    Returns the per-webhook override if set, otherwise the tenant
    default, otherwise ``None`` (caller's signal to skip the dispatch
    and log an error). Empty strings are treated as unset to avoid
    silently signing with a zero-length key.
    """
    if endpoint_secret:
        return endpoint_secret
    if tenant_default_secret:
        return tenant_default_secret
    return None


def _load_tenant_default_secret(db: Session, tenant_id: uuid_mod.UUID) -> str | None:
    """Read ``Tenant.webhook_signing_secret`` once per emission."""
    from lintpdf.api.models import Tenant

    try:
        row = db.get(Tenant, tenant_id)
    except Exception:
        logger.exception(
            "Webhook emit: failed to load tenant %s for default secret",
            tenant_id,
        )
        return None
    return getattr(row, "webhook_signing_secret", None) if row else None


def _ensure_json_safe(value: Any) -> Any:
    """Coerce UUIDs + datetimes so the payload round-trips through JSON.

    The dispatcher calls ``json.dumps(payload, default=str)`` already,
    but pre-serialising here keeps the stored ``WebhookDelivery.payload``
    column byte-identical to the signed body so replay verifies.
    """
    return json.loads(json.dumps(value, default=str))


# ---------------------------------------------------------------------------
# High-level event emitters
# ---------------------------------------------------------------------------


def build_job_state_payload(db: Session, job: Any, tenant_id: uuid_mod.UUID) -> dict[str, Any]:
    """Return the ``/jobs/{id}/state`` digest as a plain dict.

    Mirrors the handler in ``api/routes/jobs.get_job_state`` so
    ``job.state_changed`` webhooks carry exactly what a subscriber would
    get by calling ``GET /api/v1/jobs/{id}/state`` themselves -- no
    follow-up request required.
    """
    from lintpdf.api.config import get_settings
    from lintpdf.api.models import (
        ApprovalChain,
        ApprovalStep,
        ReportToken,
        ViewerAnnotation,
        ViewerAnnotationComment,
    )

    settings = get_settings()
    base_url = settings.report_base_url.rstrip("/")

    reports = []
    for t in (
        db.query(ReportToken)
        .filter(ReportToken.job_id == job.id, ReportToken.tenant_id == tenant_id)
        .order_by(ReportToken.created_at.asc())
        .all()
    ):
        if t.format in ("pdf", "annotated_pdf", "annotated_pdf_markup"):
            url = f"{base_url}/r/{t.token}.pdf"
        elif t.format == "json":
            url = f"{base_url}/r/{t.token}.json"
        elif t.format == "xml":
            url = f"{base_url}/r/{t.token}.xml"
        else:
            url = f"{base_url}/r/{t.token}"
        reports.append(
            {
                "format": t.format,
                "url": url,
                "token": t.token,
                "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                "allow_annotations": bool(t.allow_annotations),
                "require_visitor_email": t.require_visitor_email,
            }
        )

    chain_payload: dict[str, Any] | None = None
    chain = (
        db.query(ApprovalChain)
        .filter(ApprovalChain.job_id == job.id, ApprovalChain.tenant_id == tenant_id)
        .first()
    )
    if chain is not None:
        steps = (
            db.query(ApprovalStep)
            .filter(ApprovalStep.chain_id == chain.id)
            .order_by(ApprovalStep.step_index, ApprovalStep.created_at)
            .all()
        )
        chain_payload = {
            "id": str(chain.id),
            "template_id": str(chain.template_id) if chain.template_id else None,
            "status": chain.status,
            "current_step": chain.current_step,
            "step_history": [
                {
                    "step_index": s.step_index,
                    "step_name": s.step_name,
                    "approver_email": s.approver_email,
                    "decision": s.decision,
                    "notes": s.notes,
                    "decided_at": s.decided_at.isoformat() if s.decided_at else None,
                }
                for s in steps
            ],
            "created_at": chain.created_at.isoformat() if chain.created_at else None,
            "completed_at": chain.completed_at.isoformat() if chain.completed_at else None,
        }

    auto_passed: bool | None = None
    if job.result_json:
        auto_passed = (job.result_json.get("summary") or {}).get("passed")
    verdict_payload = {
        "verdict": job.verdict,
        "auto_passed": auto_passed,
        "verdict_by": job.verdict_by,
        "verdict_at": job.verdict_at.isoformat() if job.verdict_at else None,
        "notes": job.verdict_notes,
    }

    ann_rows = (
        db.query(ViewerAnnotation)
        .filter(ViewerAnnotation.job_id == job.id)
        .order_by(ViewerAnnotation.created_at.asc())
        .all()
    )
    comments_by_ann: dict[str, list[dict[str, Any]]] = {}
    if ann_rows:
        comment_rows = (
            db.query(ViewerAnnotationComment)
            .filter(ViewerAnnotationComment.annotation_id.in_([r.id for r in ann_rows]))
            .order_by(ViewerAnnotationComment.created_at.asc())
            .all()
        )
        for c in comment_rows:
            comments_by_ann.setdefault(str(c.annotation_id), []).append(
                {
                    "id": str(c.id),
                    "annotation_id": str(c.annotation_id),
                    "author_email": c.author_email,
                    "body": c.body,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                }
            )
    by_page: dict[str, int] = {}
    items: list[dict[str, Any]] = []
    for r in ann_rows:
        by_page[str(r.page_num)] = by_page.get(str(r.page_num), 0) + 1
        items.append(
            {
                "id": str(r.id),
                "job_id": str(r.job_id),
                "page_num": r.page_num,
                "kind": r.kind,
                "geometry": r.geometry_json,
                "color": r.color,
                "text": r.text,
                "author_email": r.author_email,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "comments": comments_by_ann.get(str(r.id), []),
            }
        )

    summary = (job.result_json or {}).get("summary") if job.result_json else None

    return {
        "job": {
            "job_id": str(job.id),
            "status": job.status.value if hasattr(job.status, "value") else str(job.status),
            "profile_id": job.profile_id,
            "file_name": job.file_name,
            "page_count": job.page_count,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        },
        "summary": summary,
        "reports": reports,
        "approval_chain": chain_payload,
        "verdict": verdict_payload,
        "annotations": {"total": len(ann_rows), "by_page": by_page, "items": items},
    }


def fire_job_state_changed(
    db: Session,
    job: Any,
    tenant_id: uuid_mod.UUID,
    *,
    reason: str,
) -> None:
    """Emit ``job.state_changed`` with the full /state digest inline.

    ``reason`` is a short machine-readable tag for why the state changed
    (e.g. ``"approval.step.decided"``, ``"annotation.created"``). Lets
    subscribers de-dupe or route without having to diff the payload.
    """
    payload = build_job_state_payload(db, job, tenant_id)
    payload["reason"] = reason
    emit_event(db, tenant_id, "job.state_changed", _ensure_json_safe(payload))


def fire_annotation_created(db: Session, annotation: Any) -> None:
    emit_event(
        db,
        annotation.tenant_id,
        "annotation.created",
        _ensure_json_safe(
            {
                "job_id": str(annotation.job_id),
                "annotation": {
                    "id": str(annotation.id),
                    "page_num": annotation.page_num,
                    "kind": annotation.kind,
                    "geometry": annotation.geometry_json,
                    "color": annotation.color,
                    "text": annotation.text,
                    "author_email": annotation.author_email,
                    "created_at": annotation.created_at.isoformat()
                    if annotation.created_at
                    else None,
                },
            }
        ),
    )


def fire_annotation_deleted(db: Session, annotation: Any) -> None:
    emit_event(
        db,
        annotation.tenant_id,
        "annotation.deleted",
        _ensure_json_safe(
            {
                "job_id": str(annotation.job_id),
                "annotation_id": str(annotation.id),
                "page_num": annotation.page_num,
            }
        ),
    )


def fire_comment_created(db: Session, comment: Any) -> None:
    emit_event(
        db,
        comment.tenant_id,
        "comment.created",
        _ensure_json_safe(
            {
                "annotation_id": str(comment.annotation_id),
                "comment": {
                    "id": str(comment.id),
                    "author_email": comment.author_email,
                    "body": comment.body,
                    "created_at": comment.created_at.isoformat() if comment.created_at else None,
                },
            }
        ),
    )


def fire_verdict_changed(
    db: Session,
    job: Any,
    tenant_id: uuid_mod.UUID,
    *,
    previous_verdict: str | None,
) -> None:
    emit_event(
        db,
        tenant_id,
        "verdict.changed",
        _ensure_json_safe(
            {
                "job_id": str(job.id),
                "previous": previous_verdict,
                "current": job.verdict,
                "verdict_by": job.verdict_by,
                "verdict_at": job.verdict_at.isoformat() if job.verdict_at else None,
                "notes": job.verdict_notes,
            }
        ),
    )


def fire_report_minted(
    db: Session,
    tenant_id: uuid_mod.UUID,
    *,
    job_id: uuid_mod.UUID,
    reports: list[dict[str, Any]],
) -> None:
    emit_event(
        db,
        tenant_id,
        "report.minted",
        _ensure_json_safe({"job_id": str(job_id), "reports": reports}),
    )


def fire_report_expired(
    db: Session,
    tenant_id: uuid_mod.UUID,
    *,
    job_id: uuid_mod.UUID,
    token: str,
    format: str,
) -> None:
    emit_event(
        db,
        tenant_id,
        "report.expired",
        _ensure_json_safe({"job_id": str(job_id), "token": token, "format": format}),
    )


def fire_share_link_visited(
    db: Session,
    tenant_id: uuid_mod.UUID,
    *,
    token: str,
    visitor_email: str,
    job_id: uuid_mod.UUID,
    first_visit: bool,
) -> None:
    emit_event(
        db,
        tenant_id,
        "share_link.visited",
        _ensure_json_safe(
            {
                "token": token,
                "visitor_email": visitor_email,
                "job_id": str(job_id),
                "first_visit": first_visit,
            }
        ),
    )


def fire_billing_threshold(
    db: Session,
    tenant_id: uuid_mod.UUID,
    *,
    resource: str,
    severity: str,
    remaining: int | float,
    allotment: int | float | None = None,
) -> None:
    """Emit ``billing.{resource}.{severity}``.

    resource -> "file_quota" | "ai_credits"
    severity -> "low" | "exhausted"
    """
    if severity not in ("low", "exhausted"):
        raise ValueError(f"Invalid severity {severity!r}")
    if resource not in ("file_quota", "ai_credits"):
        raise ValueError(f"Invalid resource {resource!r}")
    event = f"billing.{resource}.{severity}"
    emit_event(
        db,
        tenant_id,
        event,
        _ensure_json_safe(
            {
                "resource": resource,
                "severity": severity,
                "remaining": remaining,
                "allotment": allotment,
            }
        ),
    )


def fire_tenant_plan_changed(
    db: Session,
    tenant_id: uuid_mod.UUID,
    *,
    previous_plan: str | None,
    new_plan: str,
) -> None:
    emit_event(
        db,
        tenant_id,
        "tenant.plan.changed",
        _ensure_json_safe(
            {
                "previous_plan": previous_plan,
                "new_plan": new_plan,
            }
        ),
    )
