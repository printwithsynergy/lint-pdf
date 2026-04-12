"""Approval chain orchestration: step advance, webhook fire, email send."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from lintpdf.api.models import (
    ApprovalChain,
    ApprovalChainTemplate,
    ApprovalStep,
    BrandProfile,
    Job,
    Tenant,
)

logger = logging.getLogger(__name__)


def _generate_token() -> str:
    """Generate a secure URL-safe access token for approvers."""
    return secrets.token_urlsafe(48)  # 64 chars


def _resolve_viewer_url_for_chain(
    tenant: Tenant,
    brand_profile: BrandProfile | None,
    token: str,
) -> str:
    """Build approve URL using tenant's app custom domain if configured."""
    from lintpdf.api.config import get_settings

    settings = get_settings()
    base = settings.app_base_url.rstrip("/")
    if (
        brand_profile
        and getattr(brand_profile, "app_custom_domain", None)
        and brand_profile.app_custom_domain_verified
    ):
        base = f"https://{brand_profile.app_custom_domain}"
    elif getattr(tenant, "app_custom_domain", None) and tenant.app_custom_domain_verified:
        base = f"https://{tenant.app_custom_domain}"
    return f"{base}/approve/{token}"


def _resolve_viewer_base(tenant: Tenant, brand_profile: BrandProfile | None) -> str:
    from lintpdf.api.config import get_settings

    settings = get_settings()
    if (
        brand_profile
        and getattr(brand_profile, "app_custom_domain", None)
        and brand_profile.app_custom_domain_verified
    ):
        return f"https://{brand_profile.app_custom_domain}"
    if getattr(tenant, "app_custom_domain", None) and tenant.app_custom_domain_verified:
        return f"https://{tenant.app_custom_domain}"
    return settings.app_base_url.rstrip("/")


def create_chain(
    db: Session,
    job: Job,
    tenant: Tenant,
    steps: list[dict[str, Any]],
    template_id: UUID | None = None,
) -> ApprovalChain:
    """Create a new approval chain for a job and kick off step 0."""
    chain = ApprovalChain(
        id=uuid4(),
        job_id=job.id,
        tenant_id=tenant.id,
        template_id=template_id,
        status="pending",
        current_step=0,
        steps=steps,
    )
    db.add(chain)
    db.flush()

    _start_step(db, chain, 0, tenant)

    db.commit()

    _fire_webhook(db, tenant, chain, "approval.chain.started", step_index=0)
    _fire_webhook(db, tenant, chain, "approval.step.started", step_index=0)

    return chain


def _start_step(
    db: Session,
    chain: ApprovalChain,
    step_index: int,
    tenant: Tenant,
) -> list[ApprovalStep]:
    """Create ApprovalStep rows for the given step and send approver emails."""
    if step_index >= len(chain.steps):
        return []

    step_config = chain.steps[step_index]
    approvers = step_config.get("approvers", [])
    timeout_hours = step_config.get("timeout_hours")
    expires_at = None
    if timeout_hours is not None and timeout_hours > 0:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=timeout_hours)

    # Resolve branding for email
    brand_profile = None
    if tenant.default_brand_profile_id:
        brand_profile = (
            db.query(BrandProfile)
            .filter(BrandProfile.id == tenant.default_brand_profile_id)
            .first()
        )

    created_steps: list[ApprovalStep] = []
    for approver in approvers:
        email = approver.get("email", "").strip().lower()
        if not email:
            continue
        token = _generate_token()
        row = ApprovalStep(
            id=uuid4(),
            chain_id=chain.id,
            step_index=step_index,
            step_name=step_config.get("name", ""),
            approver_email=email,
            decision="pending",
            access_token=token,
            expires_at=expires_at,
        )
        db.add(row)
        created_steps.append(row)

        # Send email (non-blocking best-effort)
        approve_url = _resolve_viewer_url_for_chain(tenant, brand_profile, token)
        viewer_base = _resolve_viewer_base(tenant, brand_profile)
        viewer_url = _resolve_viewer_url_for_chain(tenant, brand_profile, token).replace(
            f"/approve/{token}", f"/view/{token}"  # fallback; approver page links to viewer separately
        )
        try:
            from lintpdf.email.service import send_approval_request

            brand_name = (
                (brand_profile.brand_name if brand_profile else None)
                or tenant.brand_name
                or "LintPDF"
            )
            brand_color = (
                (brand_profile.primary_color if brand_profile else None)
                or tenant.brand_primary_color
                or "#1e3a8a"
            )
            send_approval_request(
                to=email,
                approver_name=approver.get("name"),
                step_name=step_config.get("name", "Review"),
                step_number=step_index + 1,
                total_steps=len(chain.steps),
                approve_url=approve_url,
                viewer_url=viewer_base,
                brand_name=brand_name,
                brand_primary_color=brand_color,
                chain_id=str(chain.id),
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to send approval request email to %s", email)

    return created_steps


def decide_step(
    db: Session,
    access_token: str,
    decision: str,
    notes: str | None,
) -> dict[str, Any]:
    """Record an approver's decision and advance/terminate the chain as needed."""
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be 'approved' or 'rejected'")

    step = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.access_token == access_token)
        .first()
    )
    if step is None:
        return {"error": "not_found", "status": 404}
    if step.decision != "pending":
        return {"error": "already_decided", "status": 410, "decision": step.decision}
    if step.expires_at and datetime.now(timezone.utc) > step.expires_at:
        return {"error": "expired", "status": 410}

    chain = db.query(ApprovalChain).filter(ApprovalChain.id == step.chain_id).first()
    if chain is None or chain.status != "pending":
        return {"error": "chain_inactive", "status": 410, "chain_status": chain.status if chain else None}

    tenant = db.query(Tenant).filter(Tenant.id == chain.tenant_id).first()
    if not tenant:
        return {"error": "tenant_missing", "status": 404}

    now = datetime.now(timezone.utc)
    step.decision = decision
    step.notes = notes
    step.decided_at = now
    db.flush()

    _fire_webhook(db, tenant, chain, "approval.step.decided", step_index=step.step_index, step=step)

    if decision == "rejected":
        chain.status = "rejected"
        chain.completed_at = now
        _update_job_verdict(db, chain, "fail")
        db.commit()
        _fire_webhook(db, tenant, chain, "approval.chain.rejected", step_index=step.step_index, step=step)
        return {"ok": True, "chain_status": "rejected", "step_index": step.step_index}

    # Approved — check if step is complete
    step_config = chain.steps[step.step_index]
    require_all = step_config.get("require_all", False)

    pending = (
        db.query(ApprovalStep)
        .filter(
            ApprovalStep.chain_id == chain.id,
            ApprovalStep.step_index == step.step_index,
            ApprovalStep.decision == "pending",
        )
        .count()
    )

    if require_all and pending > 0:
        db.commit()
        return {"ok": True, "chain_status": "pending", "awaiting": pending, "step_index": step.step_index}

    # Advance to next step
    next_index = step.step_index + 1
    if next_index >= len(chain.steps):
        # Chain complete
        chain.status = "approved"
        chain.completed_at = now
        chain.current_step = next_index
        _update_job_verdict(db, chain, "pass")
        db.commit()
        _fire_webhook(db, tenant, chain, "approval.chain.completed", step_index=step.step_index, step=step)
        return {"ok": True, "chain_status": "approved", "step_index": step.step_index}

    chain.current_step = next_index
    _start_step(db, chain, next_index, tenant)
    db.commit()
    _fire_webhook(db, tenant, chain, "approval.step.started", step_index=next_index)

    return {"ok": True, "chain_status": "pending", "advanced_to_step": next_index}


def cancel_chain(db: Session, chain: ApprovalChain, tenant: Tenant) -> None:
    """Cancel an active chain and invalidate all pending tokens."""
    if chain.status != "pending":
        return

    now = datetime.now(timezone.utc)
    chain.status = "cancelled"
    chain.completed_at = now

    # Invalidate pending access tokens
    db.query(ApprovalStep).filter(
        ApprovalStep.chain_id == chain.id,
        ApprovalStep.decision == "pending",
    ).update({"expires_at": now}, synchronize_session=False)

    db.commit()
    _fire_webhook(db, tenant, chain, "approval.chain.cancelled", step_index=chain.current_step)


def process_timeouts(db: Session) -> dict[str, int]:
    """Celery Beat: handle steps whose expires_at has passed."""
    now = datetime.now(timezone.utc)
    expired_steps = (
        db.query(ApprovalStep)
        .filter(
            ApprovalStep.decision == "pending",
            ApprovalStep.expires_at.isnot(None),
            ApprovalStep.expires_at < now,
        )
        .all()
    )

    rejected = 0
    advanced = 0
    notified = 0

    processed_chains: set[UUID] = set()

    for step in expired_steps:
        if step.chain_id in processed_chains:
            continue

        chain = db.query(ApprovalChain).filter(ApprovalChain.id == step.chain_id).first()
        if chain is None or chain.status != "pending":
            continue
        if chain.current_step != step.step_index:
            continue

        processed_chains.add(chain.id)

        step_config = chain.steps[step.step_index]
        on_timeout = step_config.get("on_timeout", "notify")
        tenant = db.query(Tenant).filter(Tenant.id == chain.tenant_id).first()
        if not tenant:
            continue

        if on_timeout == "reject":
            step.decision = "rejected"
            step.decided_at = now
            step.notes = "Automatic rejection due to step timeout."
            chain.status = "rejected"
            chain.completed_at = now
            _update_job_verdict(db, chain, "fail")
            db.commit()
            _fire_webhook(db, tenant, chain, "approval.chain.timeout", step_index=step.step_index, step=step)
            _fire_webhook(db, tenant, chain, "approval.chain.rejected", step_index=step.step_index, step=step)
            rejected += 1
        elif on_timeout == "advance":
            step.decision = "approved"
            step.decided_at = now
            step.notes = "Automatic approval due to step timeout."
            next_index = step.step_index + 1
            if next_index >= len(chain.steps):
                chain.status = "approved"
                chain.completed_at = now
                chain.current_step = next_index
                _update_job_verdict(db, chain, "pass")
                db.commit()
                _fire_webhook(db, tenant, chain, "approval.chain.timeout", step_index=step.step_index, step=step)
                _fire_webhook(db, tenant, chain, "approval.chain.completed", step_index=step.step_index, step=step)
            else:
                chain.current_step = next_index
                _start_step(db, chain, next_index, tenant)
                db.commit()
                _fire_webhook(db, tenant, chain, "approval.chain.timeout", step_index=step.step_index, step=step)
                _fire_webhook(db, tenant, chain, "approval.step.started", step_index=next_index)
            advanced += 1
        else:  # notify — re-send emails, keep pending, reset expires_at
            timeout_hours = step_config.get("timeout_hours")
            if timeout_hours:
                step.expires_at = now + timedelta(hours=timeout_hours)
            db.commit()
            _fire_webhook(db, tenant, chain, "approval.chain.timeout", step_index=step.step_index, step=step)
            notified += 1

    return {"rejected": rejected, "advanced": advanced, "notified": notified}


def _update_job_verdict(db: Session, chain: ApprovalChain, verdict: str) -> None:
    """Sync chain outcome to the job's verdict fields."""
    job = db.query(Job).filter(Job.id == chain.job_id).first()
    if not job:
        return

    template_name = "Ad-hoc Approval Chain"
    if chain.template_id:
        template = (
            db.query(ApprovalChainTemplate)
            .filter(ApprovalChainTemplate.id == chain.template_id)
            .first()
        )
        if template:
            template_name = template.name

    all_steps = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.chain_id == chain.id)
        .order_by(ApprovalStep.step_index, ApprovalStep.created_at)
        .all()
    )
    notes_parts = []
    for s in all_steps:
        if s.decision != "pending":
            line = f"[{s.step_name}] {s.approver_email}: {s.decision}"
            if s.notes:
                line += f" — {s.notes}"
            notes_parts.append(line)

    job.verdict = verdict
    job.verdict_by = template_name
    job.verdict_at = datetime.now(timezone.utc)
    job.verdict_notes = "\n".join(notes_parts) if notes_parts else None


def _fire_webhook(
    db: Session,
    tenant: Tenant,
    chain: ApprovalChain,
    event: str,
    step_index: int,
    step: ApprovalStep | None = None,
) -> None:
    """Dispatch an approval webhook event to tenant endpoints + any step-level webhook_url."""
    from lintpdf.queue.tasks import dispatch_webhook
    from lintpdf.api.models import WebhookEndpoint

    step_config = chain.steps[step_index] if step_index < len(chain.steps) else {}

    viewer_url = ""
    try:
        brand_profile = None
        if tenant.default_brand_profile_id:
            brand_profile = (
                db.query(BrandProfile)
                .filter(BrandProfile.id == tenant.default_brand_profile_id)
                .first()
            )
        viewer_base = _resolve_viewer_base(tenant, brand_profile)
        # Best-effort: try to find a ReportToken for the job
        from lintpdf.api.models import ReportToken

        token_row = (
            db.query(ReportToken)
            .filter(ReportToken.job_id == chain.job_id, ReportToken.format == "html")
            .order_by(ReportToken.id.desc())
            .first()
        )
        if token_row:
            viewer_url = f"{viewer_base}/view/{token_row.token}"
    except Exception:  # noqa: BLE001
        viewer_url = ""

    payload = {
        "event": event,
        "job_id": str(chain.job_id),
        "chain_id": str(chain.id),
        "template_id": str(chain.template_id) if chain.template_id else None,
        "step_index": step_index,
        "step_name": step_config.get("name") if isinstance(step_config, dict) else None,
        "status": chain.status,
        "decision": step.decision if step else None,
        "approver_email": step.approver_email if step else None,
        "notes": step.notes if step else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "viewer_url": viewer_url,
    }

    # Fire to step-level webhook_url (if set)
    step_webhook = step_config.get("webhook_url") if isinstance(step_config, dict) else None
    if step_webhook:
        try:
            dispatch_webhook.delay(
                webhook_url=step_webhook,
                webhook_secret="",  # Step-level webhooks can be unsigned or use HMAC with empty secret
                event=event,
                payload=payload,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to queue step-level webhook for %s", step_webhook)

    # Fire to tenant-level webhook endpoints subscribing to this event
    endpoints = (
        db.query(WebhookEndpoint)
        .filter(
            WebhookEndpoint.tenant_id == tenant.id,
            WebhookEndpoint.is_active.is_(True),
        )
        .all()
    )
    for ep in endpoints:
        if ep.events and event not in ep.events:
            continue
        try:
            dispatch_webhook.delay(
                webhook_url=ep.url,
                webhook_secret=ep.secret,
                event=event,
                payload=payload,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to queue webhook for %s", ep.url)
