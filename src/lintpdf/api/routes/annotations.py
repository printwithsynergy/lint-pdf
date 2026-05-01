"""Viewer annotations — authenticated + public share-link CRUD.

Backs the Mark Up toolbar group in the interactive viewer. Anonymous
share-link visitors can read annotations without gating, but creating
or modifying requires both ``allow_annotations=true`` on the token
record and an ``X-Visitor-Email`` header identifying the writer.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import (
    Job,
    ReportToken,
    ShareLinkVisitor,
    Tenant,
    ViewerAnnotation,
    ViewerAnnotationComment,
)
from lintpdf.services.email import EmailService, get_email_service

logger = logging.getLogger(__name__)

router = APIRouter()

_ALLOWED_KINDS = {"rect", "circle", "arrow", "freehand", "note"}


class AnnotationCreateRequest(BaseModel):
    page_num: int = Field(..., ge=1, description="1-indexed page number")
    kind: str = Field(..., description='"rect" | "circle" | "arrow" | "freehand" | "note"')
    geometry: dict[str, Any] = Field(..., description="Primitive geometry in PDF points")
    color: str = Field(default="#dc2626", max_length=16)
    text: str | None = Field(default=None, max_length=2000)


class AnnotationUpdateRequest(BaseModel):
    geometry: dict[str, Any] | None = None
    color: str | None = Field(default=None, max_length=16)
    text: str | None = Field(default=None, max_length=2000)


class AnnotationResponse(BaseModel):
    id: str
    job_id: str
    page_num: int
    kind: str
    geometry: dict[str, Any]
    color: str
    text: str | None
    author_email: str
    created_at: str
    updated_at: str


class CommentCreateRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000, description="Comment body")


class CommentUpdateRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)


class CommentResponse(BaseModel):
    id: str
    annotation_id: str
    author_email: str
    body: str
    created_at: str
    updated_at: str


class AnnotationWithCommentsResponse(AnnotationResponse):
    """Annotation with its comment thread embedded inline.

    Returned from ``GET .../annotations?include=comments`` instead of the
    bare :class:`AnnotationResponse`. The extra ``comments`` field is an
    ordered list (oldest first) of every comment on the annotation —
    matches the shape used by ``GET /jobs/{id}/state`` so clients can
    parse both surfaces with one model.
    """

    comments: list[CommentResponse] = Field(
        default_factory=list,
        description="Ordered (oldest first) comments on this annotation.",
    )


def _comment_to_response(row: ViewerAnnotationComment) -> CommentResponse:
    return CommentResponse(
        id=str(row.id),
        annotation_id=str(row.annotation_id),
        author_email=row.author_email,
        body=row.body,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


class _AnnotationSnapshot:
    """Lightweight struct to carry annotation fields past a delete-commit.

    The ORM row becomes unusable the moment SQLAlchemy expires it on
    commit, so the deletion-event helpers need a plain container to
    quote ``id`` / ``job_id`` / ``page_num`` / ``tenant_id`` from after
    the delete has landed.
    """

    __slots__ = ("id", "job_id", "page_num", "tenant_id")

    def __init__(
        self,
        *,
        id: uuid_mod.UUID,
        tenant_id: uuid_mod.UUID,
        job_id: uuid_mod.UUID,
        page_num: int,
    ) -> None:
        self.id = id
        self.tenant_id = tenant_id
        self.job_id = job_id
        self.page_num = page_num


def _to_response(row: ViewerAnnotation) -> AnnotationResponse:
    return AnnotationResponse(
        id=str(row.id),
        job_id=str(row.job_id),
        page_num=row.page_num,
        kind=row.kind,
        geometry=row.geometry_json,
        color=row.color,
        text=row.text,
        author_email=row.author_email,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


def _dashboard_author_email(request: Request, tenant: Tenant) -> str:
    """Resolve the author email for a dashboard-side annotation/comment.

    The Next.js plugin proxy forwards the authenticated user's email as
    ``X-Visitor-Email`` (same header name the public share-link surface
    uses, so the engine handlers share one code path). Falls back to
    the tenant's contact email for direct API-key callers, and finally
    to a sentinel so the column is never NULL.
    """
    header = (request.headers.get("x-visitor-email") or "").strip().lower()
    if header and "@" in header and len(header) <= 255:
        return header
    if tenant.contact_email:
        return tenant.contact_email
    return "dashboard@lintpdf"


def _validate_kind(kind: str) -> None:
    if kind not in _ALLOWED_KINDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"kind must be one of: {', '.join(sorted(_ALLOWED_KINDS))}",
        )


def _require_annotations_entitlement(tenant: Tenant) -> None:
    """Raise a plan_upgrade_required 403 if the tenant's plan forbids annotations."""
    from lintpdf.api.gates import plan_upgrade_required
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)
    if not entitlements.annotations_enabled:
        raise plan_upgrade_required(
            gate="annotations",
            current_plan=str(tenant.plan),
            required_plan="starter",
            message=(
                f"Your plan ({tenant.plan}) does not include viewer "
                f"annotations. Upgrade to Starter to unlock annotation "
                f"tools."
            ),
        )


# ---------------------------------------------------------------------------
# Authenticated (dashboard) endpoints
# ---------------------------------------------------------------------------


def _parse_include_comments(raw: str | None) -> bool:
    """Normalise the optional ``?include=comments`` query param.

    Accepts ``comments`` (singular, case-insensitive). Any other non-empty
    value 422s so typos like ``?include=comment`` surface loudly instead
    of silently returning the bare shape. ``None`` / empty returns False,
    preserving back-compat for every existing caller.
    """
    if raw is None or not raw.strip():
        return False
    wanted = {part.strip().lower() for part in raw.split(",") if part.strip()}
    unknown = wanted - {"comments"}
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unknown include key(s): {', '.join(sorted(unknown))}. "
                "Only `comments` is supported on this endpoint."
            ),
        )
    return "comments" in wanted


def _embed_comments(
    db: Session, rows: list[ViewerAnnotation]
) -> list[AnnotationWithCommentsResponse]:
    """Stitch a single `comments` thread onto each annotation.

    One SELECT pulls every comment for the given annotation IDs, then we
    group in Python. Net O(1) round trips instead of N+1 -- same strategy
    the /jobs/{id}/state aggregator uses for its annotations section.
    """
    if not rows:
        return []
    ann_ids = [r.id for r in rows]
    comment_rows = (
        db.query(ViewerAnnotationComment)
        .filter(ViewerAnnotationComment.annotation_id.in_(ann_ids))
        .order_by(ViewerAnnotationComment.created_at.asc())
        .all()
    )
    by_ann: dict[str, list[CommentResponse]] = {}
    for c in comment_rows:
        by_ann.setdefault(str(c.annotation_id), []).append(_comment_to_response(c))
    out: list[AnnotationWithCommentsResponse] = []
    for r in rows:
        base = _to_response(r)
        out.append(
            AnnotationWithCommentsResponse(
                **base.model_dump(),
                comments=by_ann.get(str(r.id), []),
            )
        )
    return out


@router.get(
    "/jobs/{job_id}/annotations",
    response_model=list[AnnotationResponse] | list[AnnotationWithCommentsResponse],
)
async def list_annotations_auth(
    job_id: str,
    include: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> list[AnnotationResponse] | list[AnnotationWithCommentsResponse]:
    """List all annotations for a job (tenant-scoped).

    Pass ``?include=comments`` to embed each annotation's full comment
    thread inline, eliminating the N+1 fan-out that previously required
    a ``GET .../annotations/{id}/comments`` round trip per annotation.
    Default shape is unchanged for back-compat.
    """
    try:
        jid = uuid_mod.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found.") from None

    job = db.query(Job).filter(Job.id == jid, Job.tenant_id == tenant.id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    rows = (
        db.query(ViewerAnnotation)
        .filter(ViewerAnnotation.job_id == jid)
        .order_by(ViewerAnnotation.created_at.asc())
        .all()
    )
    if _parse_include_comments(include):
        return _embed_comments(db, rows)
    return [_to_response(r) for r in rows]


@router.post(
    "/jobs/{job_id}/annotations",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_annotation_auth(
    job_id: str,
    body: AnnotationCreateRequest,
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> AnnotationResponse:
    """Create an annotation on a job page (authenticated dashboard writer).

    Attribution precedence:
      1. ``X-Visitor-Email`` header (forwarded by the Next.js plugin,
         carries the authenticated user's email so per-user audit works
         on tenants with multiple dashboard reviewers).
      2. ``tenant.contact_email`` — fallback for direct API-key callers.
      3. ``"dashboard@lintpdf"`` sentinel so the column is never NULL.
    """
    _require_annotations_entitlement(tenant)
    _validate_kind(body.kind)
    try:
        jid = uuid_mod.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found.") from None

    job = db.query(Job).filter(Job.id == jid, Job.tenant_id == tenant.id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    row = ViewerAnnotation(
        id=uuid_mod.uuid4(),
        job_id=jid,
        tenant_id=tenant.id,
        share_token=None,
        page_num=body.page_num,
        kind=body.kind,
        geometry_json=body.geometry,
        color=body.color,
        text=body.text,
        author_email=_dashboard_author_email(request, tenant),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    # Notify subscribers: granular (annotation.created) + umbrella
    # (job.state_changed with the full /state digest inline).
    from lintpdf.webhooks.events import fire_annotation_created, fire_job_state_changed

    fire_annotation_created(db, row)
    fire_job_state_changed(db, job, tenant.id, reason="annotation.created")
    db.commit()

    return _to_response(row)


@router.patch("/jobs/{job_id}/annotations/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation_auth(
    job_id: str,
    annotation_id: str,
    body: AnnotationUpdateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> AnnotationResponse:
    _require_annotations_entitlement(tenant)
    try:
        aid = uuid_mod.UUID(annotation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Annotation not found.") from None

    row = (
        db.query(ViewerAnnotation)
        .filter(
            ViewerAnnotation.id == aid,
            ViewerAnnotation.tenant_id == tenant.id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")

    if body.geometry is not None:
        row.geometry_json = body.geometry
    if body.color is not None:
        row.color = body.color
    if body.text is not None:
        row.text = body.text
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.delete(
    "/jobs/{job_id}/annotations/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_annotation_auth(
    job_id: str,
    annotation_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> None:
    _require_annotations_entitlement(tenant)
    try:
        aid = uuid_mod.UUID(annotation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Annotation not found.") from None

    row = (
        db.query(ViewerAnnotation)
        .filter(
            ViewerAnnotation.id == aid,
            ViewerAnnotation.tenant_id == tenant.id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")

    # Capture a plain-dict snapshot BEFORE deletion so the event helper
    # still has the fields it needs after the ORM row is gone.
    snapshot = _AnnotationSnapshot(
        id=row.id,
        tenant_id=row.tenant_id,
        job_id=row.job_id,
        page_num=row.page_num,
    )
    deleted_job_id = row.job_id
    db.delete(row)
    db.commit()

    job = db.query(Job).filter(Job.id == deleted_job_id, Job.tenant_id == tenant.id).first()
    from lintpdf.webhooks.events import fire_annotation_deleted, fire_job_state_changed

    fire_annotation_deleted(db, snapshot)
    if job is not None:
        fire_job_state_changed(db, job, tenant.id, reason="annotation.deleted")
    db.commit()


# ---------------------------------------------------------------------------
# Public share-link endpoints
# ---------------------------------------------------------------------------


def _resolve_token(token: str, db: Session) -> ReportToken:
    rec = db.query(ReportToken).filter(ReportToken.token == token).first()
    if rec is None:
        raise HTTPException(status_code=404, detail="Token not found.")
    if rec.expires_at is not None and datetime.now(timezone.utc) > rec.expires_at:
        raise HTTPException(status_code=410, detail="Token has expired.")
    return rec


def _capture_visitor(token: str, email: str, request: Request, db: Session) -> None:
    """Upsert a share-link visitor row so we have an audit trail.

    Hashes the client IP (do not store raw). A missing client address
    (e.g. behind a proxy with no X-Forwarded-For handled upstream) is
    fine — we still record the email.
    """
    ip = (request.client.host if request.client else "") or ""
    ip_hash = hashlib.sha256(ip.encode()).hexdigest() if ip else None
    ua = request.headers.get("user-agent", "")[:512] or None

    existing = (
        db.query(ShareLinkVisitor)
        .filter(
            ShareLinkVisitor.share_token == token,
            ShareLinkVisitor.visitor_email == email.lower(),
        )
        .first()
    )
    first_visit = existing is None
    if existing is None:
        db.add(
            ShareLinkVisitor(
                id=uuid_mod.uuid4(),
                share_token=token,
                visitor_email=email.lower(),
                ip_hash=ip_hash,
                user_agent=ua,
            )
        )
    else:
        existing.last_seen_at = datetime.now(timezone.utc)
        if ip_hash:
            existing.ip_hash = ip_hash
        if ua:
            existing.user_agent = ua

    # Fire share_link.visited only on first touch per (token, email) pair.
    # Subsequent visits update last_seen_at but don't spam webhooks.
    if first_visit:
        try:
            rec = db.query(ReportToken).filter(ReportToken.token == token).first()
            if rec is not None:
                from lintpdf.webhooks.events import fire_share_link_visited

                fire_share_link_visited(
                    db,
                    rec.tenant_id,
                    token=token,
                    visitor_email=email.lower(),
                    job_id=rec.job_id,
                    first_visit=True,
                )
        except Exception:
            logger.exception("share_link.visited webhook emit failed")


def _require_visitor_email(request: Request) -> str:
    email = (request.headers.get("x-visitor-email") or "").strip().lower()
    if not email or "@" not in email or len(email) > 255:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Annotation requires a visitor email. Provide 'X-Visitor-Email: you@example.com'."
            ),
        )
    return email


@router.get(
    "/public/{token}/annotations",
    response_model=list[AnnotationResponse] | list[AnnotationWithCommentsResponse],
)
async def list_annotations_public(
    token: str,
    include: str | None = None,
    db: Session = Depends(get_db),
) -> list[AnnotationResponse] | list[AnnotationWithCommentsResponse]:
    """List annotations for a share-link job (unauthenticated read).

    Pass ``?include=comments`` to embed each annotation's comment thread
    inline. The share-link surface is always read-only for comments; the
    ``allow_annotations`` flag on the token only gates *creation* of new
    annotations, not retrieval of the thread on existing ones.
    """
    rec = _resolve_token(token, db)
    rows = (
        db.query(ViewerAnnotation)
        .filter(ViewerAnnotation.job_id == rec.job_id)
        .order_by(ViewerAnnotation.created_at.asc())
        .all()
    )
    if _parse_include_comments(include):
        return _embed_comments(db, rows)
    return [_to_response(r) for r in rows]


@router.post(
    "/public/{token}/annotations",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_annotation_public(
    token: str,
    body: AnnotationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AnnotationResponse:
    """Create an annotation via a share-link token.

    Requires the token's ``allow_annotations`` flag to be set (minted by
    the issuing tenant) and an ``X-Visitor-Email`` header identifying
    the writer. The email is recorded once per token+email pair in
    ``share_link_visitors`` for audit.
    """
    _validate_kind(body.kind)
    rec = _resolve_token(token, db)
    if not rec.allow_annotations:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This share link is read-only.",
        )
    email = _require_visitor_email(request)
    _capture_visitor(token, email, request, db)

    row = ViewerAnnotation(
        id=uuid_mod.uuid4(),
        job_id=rec.job_id,
        tenant_id=rec.tenant_id,
        share_token=token,
        page_num=body.page_num,
        kind=body.kind,
        geometry_json=body.geometry,
        color=body.color,
        text=body.text,
        author_email=email,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    # Share-link annotation creates still fire tenant-scoped webhooks so
    # the issuing tenant's dashboard gets the same signal whether the
    # reviewer typed in the dashboard or a share-link page.
    from lintpdf.webhooks.events import fire_annotation_created, fire_job_state_changed

    fire_annotation_created(db, row)
    job = db.query(Job).filter(Job.id == rec.job_id).first()
    if job is not None:
        fire_job_state_changed(db, job, rec.tenant_id, reason="annotation.created")
    db.commit()

    return _to_response(row)


@router.patch(
    "/public/{token}/annotations/{annotation_id}",
    response_model=AnnotationResponse,
)
async def update_annotation_public(
    token: str,
    annotation_id: str,
    body: AnnotationUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AnnotationResponse:
    rec = _resolve_token(token, db)
    if not rec.allow_annotations:
        raise HTTPException(status_code=403, detail="This share link is read-only.")
    email = _require_visitor_email(request)
    _capture_visitor(token, email, request, db)

    try:
        aid = uuid_mod.UUID(annotation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Annotation not found.") from None

    row = (
        db.query(ViewerAnnotation)
        .filter(
            ViewerAnnotation.id == aid,
            ViewerAnnotation.share_token == token,
            ViewerAnnotation.author_email == email,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")

    if body.geometry is not None:
        row.geometry_json = body.geometry
    if body.color is not None:
        row.color = body.color
    if body.text is not None:
        row.text = body.text
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.delete(
    "/public/{token}/annotations/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_annotation_public(
    token: str,
    annotation_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    rec = _resolve_token(token, db)
    if not rec.allow_annotations:
        raise HTTPException(status_code=403, detail="This share link is read-only.")
    email = _require_visitor_email(request)
    _capture_visitor(token, email, request, db)

    try:
        aid = uuid_mod.UUID(annotation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Annotation not found.") from None

    row = (
        db.query(ViewerAnnotation)
        .filter(
            ViewerAnnotation.id == aid,
            ViewerAnnotation.share_token == token,
            ViewerAnnotation.author_email == email,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    snapshot = _AnnotationSnapshot(
        id=row.id,
        tenant_id=row.tenant_id,
        job_id=row.job_id,
        page_num=row.page_num,
    )
    deleted_job_id = row.job_id
    deleted_tenant_id = row.tenant_id
    db.delete(row)
    db.commit()

    from lintpdf.webhooks.events import fire_annotation_deleted, fire_job_state_changed

    fire_annotation_deleted(db, snapshot)
    job = db.query(Job).filter(Job.id == deleted_job_id).first()
    if job is not None:
        fire_job_state_changed(db, job, deleted_tenant_id, reason="annotation.deleted")
    db.commit()


# ---------------------------------------------------------------------------
# Comment threads — Wave B collaboration
# ---------------------------------------------------------------------------


def _parse_annotation_id(annotation_id: str) -> uuid_mod.UUID:
    try:
        return uuid_mod.UUID(annotation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Annotation not found.") from None


def _parse_comment_id(comment_id: str) -> uuid_mod.UUID:
    try:
        return uuid_mod.UUID(comment_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Comment not found.") from None


# Production defaults for annotation deep-link URLs. These match the
# current Railway prod deployment (app.lintpdf.com dashboard,
# reports.lintpdf.com share surface). Overridable via env so a staging
# or customer-branded tenant can point elsewhere without a code change.
_DEFAULT_APP_URL = "https://app.lintpdf.com"
_DEFAULT_REPORT_BASE_URL = "https://reports.lintpdf.com"


def _deep_link_for_annotation(*, annotation: ViewerAnnotation, share_token: str | None) -> str:
    """Build a viewer URL that opens the referenced annotation.

    Share-link writers get the public ``/v/{token}`` surface; dashboard
    writers get the authenticated dashboard viewer. The ``#ann={id}``
    fragment is read by ``PdfViewer.tsx`` to scroll the reader to the
    markup and auto-open its popover.

    Resolution order:
    1. Env-provided override (``LINTPDF_APP_URL`` / ``LINTPDF_REPORT_BASE_URL``
       / ``NEXT_PUBLIC_APP_URL``) — honoured when non-empty so staging
       and custom-domain tenants can redirect.
    2. Production defaults (``app.lintpdf.com`` /
       ``reports.lintpdf.com``) — always produce an absolute URL so
       recipients in external inboxes can click through.
    """
    app_base = os.getenv("LINTPDF_APP_URL") or os.getenv("NEXT_PUBLIC_APP_URL") or _DEFAULT_APP_URL
    share_base = os.getenv("LINTPDF_REPORT_BASE_URL") or _DEFAULT_REPORT_BASE_URL
    if share_token:
        return f"{share_base.rstrip('/')}/v/{share_token}#ann={annotation.id}"
    return f"{app_base.rstrip('/')}/dashboard/jobs/{annotation.job_id}/viewer#ann={annotation.id}"


def _fan_out_comment_email(
    *,
    db: Session,
    annotation: ViewerAnnotation,
    new_comment: ViewerAnnotationComment,
    job: Job | None,
    email: EmailService,
) -> None:
    """Email the annotation author + earlier commenters about a new reply.

    The current commenter is excluded so nobody gets their own echo.
    Fan-out is synchronous: the reviewer is already waiting on the POST
    and the email provider latency is comparable to the DB commit.

    Email service is injected (Phase 5 W2): SaaS hosts wire a real
    Resend impl via ``app.dependency_overrides[get_email_service]``,
    OSS hosts get a NoOp that skips the send.
    """
    participants: set[str] = set()
    if annotation.author_email:
        participants.add(annotation.author_email.lower())
    earlier = (
        db.query(ViewerAnnotationComment.author_email)
        .filter(
            ViewerAnnotationComment.annotation_id == annotation.id,
            ViewerAnnotationComment.id != new_comment.id,
        )
        .all()
    )
    for (addr,) in earlier:
        if addr:
            participants.add(addr.lower())

    # Don't notify the sender.
    participants.discard(new_comment.author_email.lower())
    if not participants:
        return

    file_name = getattr(job, "filename", None) or "your PDF"
    deep_link = _deep_link_for_annotation(annotation=annotation, share_token=annotation.share_token)
    excerpt = new_comment.body.strip()
    if len(excerpt) > 500:
        excerpt = excerpt[:497] + "..."

    for recipient in sorted(participants):
        try:
            email.send_annotation_comment(
                to=recipient,
                commenter_email=new_comment.author_email,
                file_name=file_name,
                body_excerpt=excerpt,
                deep_link_url=deep_link,
            )
        except Exception:
            logger.exception("Annotation comment notification failed for %s", recipient)


# ---- Authenticated dashboard CRUD ----


def _get_annotation_for_tenant(
    *, annotation_id: str, tenant: Tenant, db: Session
) -> ViewerAnnotation:
    aid = _parse_annotation_id(annotation_id)
    row = (
        db.query(ViewerAnnotation)
        .filter(ViewerAnnotation.id == aid, ViewerAnnotation.tenant_id == tenant.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    return row


@router.get(
    "/jobs/{job_id}/annotations/{annotation_id}/comments",
    response_model=list[CommentResponse],
)
async def list_comments_auth(
    job_id: str,
    annotation_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> list[CommentResponse]:
    annotation = _get_annotation_for_tenant(annotation_id=annotation_id, tenant=tenant, db=db)
    rows = (
        db.query(ViewerAnnotationComment)
        .filter(ViewerAnnotationComment.annotation_id == annotation.id)
        .order_by(ViewerAnnotationComment.created_at.asc())
        .all()
    )
    return [_comment_to_response(r) for r in rows]


@router.post(
    "/jobs/{job_id}/annotations/{annotation_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment_auth(
    job_id: str,
    annotation_id: str,
    body: CommentCreateRequest,
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
    email: EmailService = Depends(get_email_service),
) -> CommentResponse:
    annotation = _get_annotation_for_tenant(annotation_id=annotation_id, tenant=tenant, db=db)
    row = ViewerAnnotationComment(
        id=uuid_mod.uuid4(),
        annotation_id=annotation.id,
        tenant_id=tenant.id,
        share_token=annotation.share_token,
        # Author precedence: X-Visitor-Email (forwarded by the plugin
        # proxy) > tenant.contact_email > sentinel. See
        # :func:`_dashboard_author_email`.
        author_email=_dashboard_author_email(request, tenant),
        body=body.body.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    job = db.query(Job).filter(Job.id == annotation.job_id).first()
    _fan_out_comment_email(db=db, annotation=annotation, new_comment=row, job=job, email=email)

    from lintpdf.webhooks.events import fire_comment_created, fire_job_state_changed

    fire_comment_created(db, row)
    if job is not None:
        fire_job_state_changed(db, job, tenant.id, reason="comment.created")
    db.commit()

    return _comment_to_response(row)


@router.patch(
    "/jobs/{job_id}/annotations/{annotation_id}/comments/{comment_id}",
    response_model=CommentResponse,
)
async def update_comment_auth(
    job_id: str,
    annotation_id: str,
    comment_id: str,
    body: CommentUpdateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> CommentResponse:
    # Tenant scope inherits from annotation; we only need the comment id
    # plus the tenant filter to guarantee isolation.
    cid = _parse_comment_id(comment_id)
    row = (
        db.query(ViewerAnnotationComment)
        .filter(
            ViewerAnnotationComment.id == cid,
            ViewerAnnotationComment.tenant_id == tenant.id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Comment not found.")
    row.body = body.body.strip()
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _comment_to_response(row)


@router.delete(
    "/jobs/{job_id}/annotations/{annotation_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment_auth(
    job_id: str,
    annotation_id: str,
    comment_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> None:
    cid = _parse_comment_id(comment_id)
    row = (
        db.query(ViewerAnnotationComment)
        .filter(
            ViewerAnnotationComment.id == cid,
            ViewerAnnotationComment.tenant_id == tenant.id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Comment not found.")
    db.delete(row)
    db.commit()


# ---- Public share-link CRUD ----


def _get_annotation_for_token(
    *, annotation_id: str, token: str, rec: ReportToken, db: Session
) -> ViewerAnnotation:
    aid = _parse_annotation_id(annotation_id)
    row = (
        db.query(ViewerAnnotation)
        .filter(
            ViewerAnnotation.id == aid,
            ViewerAnnotation.job_id == rec.job_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    return row


@router.get(
    "/public/{token}/annotations/{annotation_id}/comments",
    response_model=list[CommentResponse],
)
async def list_comments_public(
    token: str,
    annotation_id: str,
    db: Session = Depends(get_db),
) -> list[CommentResponse]:
    rec = _resolve_token(token, db)
    annotation = _get_annotation_for_token(annotation_id=annotation_id, token=token, rec=rec, db=db)
    rows = (
        db.query(ViewerAnnotationComment)
        .filter(ViewerAnnotationComment.annotation_id == annotation.id)
        .order_by(ViewerAnnotationComment.created_at.asc())
        .all()
    )
    return [_comment_to_response(r) for r in rows]


@router.post(
    "/public/{token}/annotations/{annotation_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment_public(
    token: str,
    annotation_id: str,
    body: CommentCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    email: EmailService = Depends(get_email_service),
) -> CommentResponse:
    rec = _resolve_token(token, db)
    if not rec.allow_annotations:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This share link is read-only.",
        )
    visitor_email = _require_visitor_email(request)
    _capture_visitor(token, visitor_email, request, db)

    annotation = _get_annotation_for_token(annotation_id=annotation_id, token=token, rec=rec, db=db)
    row = ViewerAnnotationComment(
        id=uuid_mod.uuid4(),
        annotation_id=annotation.id,
        tenant_id=rec.tenant_id,
        share_token=token,
        author_email=visitor_email,
        body=body.body.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    job = db.query(Job).filter(Job.id == annotation.job_id).first()
    _fan_out_comment_email(db=db, annotation=annotation, new_comment=row, job=job, email=email)

    from lintpdf.webhooks.events import fire_comment_created, fire_job_state_changed

    fire_comment_created(db, row)
    if job is not None:
        fire_job_state_changed(db, job, rec.tenant_id, reason="comment.created")
    db.commit()

    return _comment_to_response(row)


@router.patch(
    "/public/{token}/annotations/{annotation_id}/comments/{comment_id}",
    response_model=CommentResponse,
)
async def update_comment_public(
    token: str,
    annotation_id: str,
    comment_id: str,
    body: CommentUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> CommentResponse:
    rec = _resolve_token(token, db)
    if not rec.allow_annotations:
        raise HTTPException(status_code=403, detail="This share link is read-only.")
    email = _require_visitor_email(request)
    _capture_visitor(token, email, request, db)

    cid = _parse_comment_id(comment_id)
    row = (
        db.query(ViewerAnnotationComment)
        .filter(
            ViewerAnnotationComment.id == cid,
            ViewerAnnotationComment.share_token == token,
            ViewerAnnotationComment.author_email == email,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Comment not found.")
    row.body = body.body.strip()
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _comment_to_response(row)


@router.delete(
    "/public/{token}/annotations/{annotation_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment_public(
    token: str,
    annotation_id: str,
    comment_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    rec = _resolve_token(token, db)
    if not rec.allow_annotations:
        raise HTTPException(status_code=403, detail="This share link is read-only.")
    email = _require_visitor_email(request)
    _capture_visitor(token, email, request, db)

    cid = _parse_comment_id(comment_id)
    row = (
        db.query(ViewerAnnotationComment)
        .filter(
            ViewerAnnotationComment.id == cid,
            ViewerAnnotationComment.share_token == token,
            ViewerAnnotationComment.author_email == email,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Comment not found.")
    db.delete(row)
    db.commit()
